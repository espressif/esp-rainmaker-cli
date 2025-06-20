# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

from rmaker_lib.profile_utils import get_session_with_profile
import json
from rmaker_cmd.node import _print_node_details


def _handle_error(e, operation):
    """Helper function to handle errors and extract descriptions from API responses"""
    error_msg = str(e)
    try:
        # If response is available in the exception, try to get description
        if hasattr(e, 'response') and e.response is not None:
            resp = e.response.json()
            if 'description' in resp:
                error_msg = resp['description']
    except Exception:
        pass
    print(f"Failed to {operation}: {error_msg}")


def group_add(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        group_name = vars['name']  # CLI uses --name, API expects group_name
        description = vars.get('description')
        mutually_exclusive = vars.get('mutually_exclusive')
        custom_data_arg = vars.get('custom_data')
        nodes = vars.get('nodes')
        type_ = vars.get('type')
        parent_group_id = vars.get('parent_group_id')
        custom_data = None
        if custom_data_arg:
            try:
                custom_data = json.loads(custom_data_arg)
            except Exception as e:
                print("Invalid JSON for custom_data:", e)
                return
        if nodes:
            nodes = [n.strip() for n in nodes.split(',') if n.strip()]
        resp = s.create_group(
            group_name=group_name,
            description=description,
            mutually_exclusive=mutually_exclusive,
            custom_data=custom_data,
            nodes=nodes,
            type_=type_,
            parent_group_id=parent_group_id
        )
        print("Group created successfully:")
        print(json.dumps(resp, indent=2))
    except Exception as e:
        _handle_error(e, "create group")


def group_remove(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        group_id = vars['group_id']
        resp = s.remove_group(group_id)
        print("Group removed successfully:")
        print(json.dumps(resp, indent=2))
    except Exception as e:
        _handle_error(e, "remove group")


def group_edit(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        group_id = vars['group_id']
        group_name = vars.get('name')
        description = vars.get('description')
        mutually_exclusive_str = vars.get('mutually_exclusive')
        custom_data_arg = vars.get('custom_data')
        nodes = vars.get('nodes')
        type_ = vars.get('type')
        parent_group_id = vars.get('parent_group_id')
        custom_data = None

        # Convert string values to boolean for mutually_exclusive
        mutually_exclusive = None
        if mutually_exclusive_str is not None:
            mutually_exclusive = mutually_exclusive_str.lower() in ('true', '1')

        if custom_data_arg:
            try:
                custom_data = json.loads(custom_data_arg)
            except Exception as e:
                print("Invalid JSON for custom_data:", e)
                return
        if nodes:
            nodes = [n.strip() for n in nodes.split(',') if n.strip()]
        resp = s.edit_group(
            group_id=group_id,
            group_name=group_name,
            description=description,
            mutually_exclusive=mutually_exclusive,
            custom_data=custom_data,
            nodes=nodes,
            type_=type_,
            parent_group_id=parent_group_id
        )
        print("Group edited successfully:")
        print(json.dumps(resp, indent=2))
    except Exception as e:
        _handle_error(e, "edit group")


def group_list(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        sub_groups = vars.get('sub_groups', False)
        all_groups = []
        next_id = None
        while True:
            resp = s.list_groups(start_id=next_id, sub_groups=sub_groups)
            if isinstance(resp, list):
                all_groups.extend(resp)
                # Try to get next_id from the last response if available
                if hasattr(s, 'last_group_list_response') and s.last_group_list_response:
                    next_id = s.last_group_list_response.get('next_id')
                else:
                    next_id = None
            elif isinstance(resp, dict):
                all_groups.extend(resp.get('groups', []))
                next_id = resp.get('next_id')
            else:
                break
            if not next_id:
                break

        # Helper function to print groups with hierarchy
        def print_group_hierarchy(groups, level=0):
            indent = "  " * level
            for idx, group in enumerate(groups, 1):
                group_name = group.get('group_name', 'Unnamed')
                group_id = group.get('group_id', '-')
                print(f"{indent}{idx}. {group_name} (ID: {group_id})")

                # Print sub-groups if they exist
                if sub_groups and 'sub_groups' in group and group['sub_groups']:
                    print_group_hierarchy(group['sub_groups'], level + 1)

        print("Groups:")
        print_group_hierarchy(all_groups)
        print(f"Total groups: {len(all_groups)}")
    except Exception as e:
        _handle_error(e, "list groups")


def group_show(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        group_id = vars['group_id']
        sub_groups = vars.get('sub_groups', False)
        resp = s.show_group(group_id, sub_groups=sub_groups)
        print("Group details:")
        print(json.dumps(resp, indent=2))

        # If sub_groups is enabled, also show sub-group information in a readable format
        if sub_groups and 'groups' in resp and resp['groups']:
            for group in resp['groups']:
                if 'sub_groups' in group and group['sub_groups']:
                    print("\nSub-groups:")
                    for idx, sg in enumerate(group['sub_groups'], 1):
                        name = sg.get('group_name', 'Unnamed')
                        sg_id = sg.get('group_id', '-')
                        description = sg.get('description', '')
                        if description:
                            print(f"{idx}. {name} (ID: {sg_id}) - {description}")
                        else:
                            print(f"{idx}. {name} (ID: {sg_id})")
    except Exception as e:
        _handle_error(e, "get group details")


def group_add_nodes(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        group_id = vars['group_id']
        nodes = vars['nodes']
        node_list = [n.strip() for n in nodes.split(',') if n.strip()]
        resp = s.add_nodes_to_group(group_id, node_list)
        print("Nodes added to group successfully:")
        print(json.dumps(resp, indent=2))
    except Exception as e:
        _handle_error(e, "add nodes to group")


def group_remove_nodes(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        group_id = vars['group_id']
        nodes = vars['nodes']
        node_list = [n.strip() for n in nodes.split(',') if n.strip()]
        resp = s.remove_nodes_from_group(group_id, node_list)
        print("Nodes removed from group successfully:")
        print(json.dumps(resp, indent=2))
    except Exception as e:
        _handle_error(e, "remove nodes from group")


def group_list_nodes(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        group_id = vars['group_id']
        node_details = vars.get('node_details', False)
        sub_groups = vars.get('sub_groups', False)
        raw_output = vars.get('raw', False)
        node_list = not node_details  # If not node_details, use node_list
        resp = s.list_nodes_in_group(group_id, node_details=node_details, node_list=node_list, sub_groups=sub_groups)
        # Handle node_list response
        if node_list:
            nodes = resp.get('groups', [{}])[0].get('nodes', [])
        else:
            nodes = resp.get('groups', [{}])[0].get('node_details', [])
        if node_details:
            if raw_output:
                print(json.dumps(resp, indent=4))
            else:
                if not nodes:
                    print("No nodes found in group.")
                else:
                    for idx, node_info in enumerate(nodes, 1):
                        node_id = node_info.get('id', 'Unknown')
                        _print_node_details(node_id, node_info, idx)
                        print()  # Add empty line between nodes
        else:
            if not nodes:
                print("No nodes found in group.")
            else:
                print("Nodes in group:")
                for idx, node in enumerate(nodes, 1):
                    print(f"{idx}. {node}")
                print(f"Total nodes: {len(nodes)}")
        # Print sub-groups if requested and present
        if sub_groups:
            sub_groups_data = resp.get('groups', [{}])[0].get('sub_groups')
            if sub_groups_data:
                print("\nSub-groups:")
                for idx, sg in enumerate(sub_groups_data, 1):
                    name = sg.get('group_name', 'Unnamed')
                    group_id = sg.get('group_id', '-')
                    description = sg.get('description', '')
                    if description:
                        print(f"{idx}. {name} (ID: {group_id}) - {description}")
                    else:
                        print(f"{idx}. {name} (ID: {group_id})")
    except Exception as e:
        _handle_error(e, "list nodes in group")