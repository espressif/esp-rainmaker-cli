# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

from rmaker_lib.profile_utils import get_session_with_profile
import datetime
import json
import sys
from rmaker_cmd.node import (
    _get_description,
    _get_request_expiration,
    _get_request_id,
    _get_status,
    _print_api_error,
    _print_node_details,
)


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


def _split_groups(groups_arg):
    return [g.strip() for g in groups_arg.split(',') if g.strip()]


def _print_group_sharing_request_details(resp, is_primary_user=False):
    requests_in_resp = resp.get('sharing_requests') or []
    if not requests_in_resp:
        print("No pending requests")
        return
    request_exists = False
    for request in requests_in_resp:
        if request.get('request_status', '').lower() == 'declined':
            continue
        request_exists = True
        print("\n{:<15}: {}".format('Request Id', request['request_id']))
        print("{:<15}: {}".format('Group Id(s)', ','.join(request.get('group_ids', []))))
        group_names = request.get('group_names') or []
        if group_names:
            print("{:<15}: {}".format('Group Name(s)', ','.join(group_names)))
        if is_primary_user:
            if 'user_name' in request and request['user_name']:
                print("{:<15}: {}".format('Shared with', request['user_name']))
        else:
            if 'primary_user_name' in request and request['primary_user_name']:
                print("{:<15}: {}".format('Shared by', request['primary_user_name']))
        if 'user_role' in request and request['user_role']:
            print("{:<15}: {}".format('Role', request['user_role']))
        print(_get_request_expiration(request))

    if not request_exists:
        print("No pending requests")


def _print_group_sharing_details(resp):
    try:
        groups_in_resp = resp.get('group_sharing') or []
        if not groups_in_resp:
            print("No shared groups")
            return
        for group in groups_in_resp:
            print("\nGroup Id: {}".format(group.get('group_id', '')))
            users = group.get('users') or {}
            primary_users = ','.join(users.get('primary') or [])
            secondary_users = ','.join(users.get('secondary') or [])
            print("{:<7}: {:<9}: {}".format('Users', 'Primary', primary_users), end='')
            if secondary_users:
                print("\n{:>18}: {}".format('Secondary', secondary_users), end='')
            print()
    except KeyError:
        print("Error in displaying details...Please check API Json...Exiting...")
        sys.exit(0)


def _emit(resp, raw, render):
    if raw:
        print(json.dumps(resp, indent=2))
        return
    if isinstance(resp, dict) and resp.get('status', '').lower() != 'success' and 'error_code' in resp:
        _print_api_error(resp)
        return
    render(resp)


def group_sharing_add(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        groups = _split_groups(vars['groups'])
        if not groups:
            print("At least one group id must be provided in --groups")
            return
        user = vars.get('user')
        primary = vars.get('primary') if vars.get('primary') else None
        sub_role = vars.get('sub_role')
        transfer = vars.get('transfer') if vars.get('transfer') else None
        new_role = vars.get('new_role')
        metadata = None
        metadata_arg = vars.get('metadata')
        if metadata_arg:
            try:
                metadata = json.loads(metadata_arg)
            except Exception as e:
                print("Invalid JSON for --metadata:", e)
                return
        print("Sharing group(s) with user")
        resp = s.add_user_group_sharing(
            groups=groups,
            user_name=user,
            primary=primary,
            sub_role=sub_role,
            metadata=metadata,
            transfer=transfer,
            new_role=new_role,
        )

        def render(r):
            if r.get('status', '').lower() == 'success':
                print("{:<11}: {}".format('Status', _get_status(r)))
                print("{:<11}: {}".format('Description', _get_description(r)))
                if 'request_id' in r:
                    print("{:<11}: {}".format('Request Id', _get_request_id(r)))

        _emit(resp, vars.get('raw', False), render)
    except Exception as e:
        _handle_error(e, "add group sharing")


def group_sharing_remove(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        groups = _split_groups(vars['groups'])
        if not groups:
            print("At least one group id must be provided in --groups")
            return
        print("Removing group sharing")
        resp = s.remove_user_group_sharing(
            groups=','.join(groups),
            user_name=vars['user'],
        )

        def render(r):
            if r.get('status', '').lower() == 'success':
                print("{}: {}".format(_get_status(r), _get_description(r)))

        _emit(resp, vars.get('raw', False), render)
    except Exception as e:
        _handle_error(e, "remove group sharing")


def group_sharing_list(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        resp = s.get_user_group_sharing(
            group_id=vars.get('group_id'),
            sub_groups=vars.get('sub_groups', False),
            parent_groups=vars.get('parent_groups', False),
            metadata=vars.get('metadata', False),
        )

        def render(r):
            print("Displaying group sharing details")
            _print_group_sharing_details(r)

        _emit(resp, vars.get('raw', False), render)
    except Exception as e:
        _handle_error(e, "list group sharing")


def group_sharing_list_requests(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        is_primary = vars.get('primary_user', False)
        resp = s.get_user_group_sharing_requests(
            request_id=vars.get('id'),
            primary_user=is_primary,
        )

        def render(r):
            print("Displaying pending group sharing requests")
            print("Current (logged-in) user is set as {} user".format(
                'Primary' if is_primary else 'Secondary'))
            _print_group_sharing_request_details(r, is_primary_user=is_primary)

        _emit(resp, vars.get('raw', False), render)
    except Exception as e:
        _handle_error(e, "list group sharing requests")


def _respond_group_sharing(vars, accept):
    action = 'accept' if accept else 'decline'
    try:
        s = get_session_with_profile(vars or {})
        resp = s.respond_user_group_sharing_request(
            request_id=vars['id'], accept=accept)

        def render(r):
            if r.get('status', '').lower() == 'success':
                print("{:<11}: {}".format('Status', _get_status(r)))
                print("{:<11}: {}".format('Description', _get_description(r)))

        _emit(resp, vars.get('raw', False), render)
    except Exception as e:
        _handle_error(e, "{} group sharing request".format(action))


def group_sharing_accept(vars=None):
    _respond_group_sharing(vars, accept=True)


def group_sharing_decline(vars=None):
    _respond_group_sharing(vars, accept=False)


def group_sharing_cancel(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        print("Cancelling request")
        resp = s.remove_user_group_sharing_request(request_id=vars['id'])

        def render(r):
            if r.get('status', '').lower() == 'success':
                print("{}: {}".format(_get_status(r), _get_description(r)))

        _emit(resp, vars.get('raw', False), render)
    except Exception as e:
        _handle_error(e, "cancel group sharing request")