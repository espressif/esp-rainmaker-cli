# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import json
import re
import os
import sys
import time
import datetime
import requests
import base64
import re
from pathlib import Path
from rmaker_lib import session, configmanager
from rmaker_lib.logger import log
from rmaker_lib import node
from rmaker_lib.exceptions import HttpErrorResponse, NetworkError, InvalidJSONError, SSLError,\
    RequestTimeoutError
from rmaker_lib.profile_utils import get_session_with_profile

try:
    from rmaker_lib import session, node, device, service,\
        serverconfig, configmanager
    from rmaker_lib.exceptions import HttpErrorResponse, NetworkError, InvalidJSONError, SSLError,\
        RequestTimeoutError
    from rmaker_lib.logger import log
except ImportError as err:
    print("Failed to import ESP Rainmaker library. " + str(err))
    raise err

MAX_HTTP_CONNECTION_RETRIES = 5

def _format_schedule(schedule):
    """
    Helper function to format schedule information in a readable way

    :param schedule: Schedule object from node params
    :type schedule: dict

    :return: Formatted schedule string
    :rtype: str
    """
    schedule_str = []

    # Add name and ID
    name = schedule.get('name', 'Unnamed')
    schedule_id = schedule.get('id', 'Unknown ID')
    enabled = schedule.get('enabled', False)
    status = "Enabled" if enabled else "Disabled"

    schedule_str.append(f"Name: {name} (ID: {schedule_id}, {status})")

    # Add info and flags if present
    if 'info' in schedule:
        schedule_str.append(f"Info: {schedule.get('info')}")

    if 'flags' in schedule:
        schedule_str.append(f"Flags: {schedule.get('flags')}")

    # Format triggers
    if 'triggers' in schedule:
        for trigger_idx, trigger in enumerate(schedule.get('triggers', [])):
            trigger_str = []

            # Handle minutes since midnight (convert to time)
            if 'm' in trigger:
                minutes = trigger.get('m', 0)
                hours = minutes // 60
                mins = minutes % 60
                time_str = f"{hours:02d}:{mins:02d}"
                trigger_str.append(f"Time: {time_str}")

            # Handle day bitmap
            if 'd' in trigger:
                d_value = trigger.get('d', 0)

                # Check if it's one-time schedule
                if d_value == 0:
                    trigger_str.append("Once only")
                else:
                    # Parse bitmap for days
                    days = []
                    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

                    for day_idx in range(7):
                        if (d_value & (1 << day_idx)) != 0:
                            days.append(day_names[day_idx])

                    # Check if it's all weekdays
                    if d_value == 31:  # 0b00011111
                        trigger_str.append("All weekdays")
                    # Check if it's weekends
                    elif d_value == 96:  # 0b01100000
                        trigger_str.append("Weekends")
                    # Check if it's all days
                    elif d_value == 127:  # 0b01111111
                        trigger_str.append("Every day")
                    else:
                        trigger_str.append(f"On: {', '.join(days)}")

            # Handle specific date
            if 'dd' in trigger:
                dd_value = trigger.get('dd', 1)
                trigger_str.append(f"Date: {dd_value}")

                # Handle month bitmap if present
                if 'mm' in trigger:
                    mm_value = trigger.get('mm', 0)
                    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    months = []

                    for month_idx in range(12):
                        if (mm_value & (1 << month_idx)) != 0:
                            months.append(month_names[month_idx])

                    trigger_str.append(f"Months: {', '.join(months)}")

                # Handle year
                if 'yy' in trigger:
                    yy_value = trigger.get('yy', 0)
                    trigger_str.append(f"Year: {yy_value}")

                # Handle yearly repeat
                if trigger.get('r', False):
                    trigger_str.append("Repeats yearly")

            # Handle timestamp and relative seconds fields
            if 'ts' in trigger and 'rsec' in trigger:
                ts_value = trigger.get('ts', 0)
                rsec_value = trigger.get('rsec', 0)

                # Always show rsec value
                trigger_str.append(f"After {rsec_value} seconds")

                # Only show timestamp if it's valid
                if ts_value > 1000000000:  # Valid timestamp (after year 2001)
                    ts_datetime = datetime.datetime.fromtimestamp(ts_value)
                    formatted_ts = ts_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    trigger_str.append(f"Triggers at: {formatted_ts} (local time)")
                # Don't print anything about invalid timestamps

            # Handle timestamp alone (no rsec)
            elif 'ts' in trigger:
                ts_value = trigger.get('ts', 0)
                # Only show if ts is valid
                if ts_value > 1000000000:  # Valid timestamp (after year 2001)
                    ts_datetime = datetime.datetime.fromtimestamp(ts_value)
                    formatted_ts = ts_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    trigger_str.append(f"Triggers at: {formatted_ts} (local time)")

            # Handle relative seconds alone (no ts)
            elif 'rsec' in trigger:
                rsec_value = trigger.get('rsec', 0)
                trigger_str.append(f"After {rsec_value} seconds")

            schedule_str.append(f"  Trigger {trigger_idx+1}: {', '.join(trigger_str)}")

    # Format actions
    if 'action' in schedule:
        actions = []
        action_obj = schedule.get('action', {})

        for device_name, device_action in action_obj.items():
            action_details = []
            for param, value in device_action.items():
                action_details.append(f"{param}: {value}")

            actions.append(f"{device_name}: {', '.join(action_details)}")

        schedule_str.append(f"  Action: {'; '.join(actions)}")

    return "\n".join(schedule_str)

def get_nodes(vars=None):
    """
    List all nodes associated with the user.

    :param vars: Optional parameters including 'profile'
    :type vars: dict | None

    :raises Exception: If there is an HTTP issue while getting nodes

    :return: None on Success
    :rtype: None
    """
    try:
        s = get_session_with_profile(vars or {})
        nodes = s.get_nodes()
    except Exception as get_nodes_err:
        log.error(get_nodes_err)
    else:
        if len(nodes.keys()) == 0:
            print('User is not associated with any nodes.')
            return
        for idx, key in enumerate(nodes.keys(), 1):
            print(f"{idx}. {nodes[key].get_nodeid()}")
    return

def get_node_details(vars=None):
    """
    Get detailed information for all nodes including config, status, and params.

    :param vars: Optional parameters:
                 `raw` as key - If True, prints raw JSON output
                 `nodeid` as key - Single node ID to get details for
                 `profile` as key - Profile to use for the operation
    :type vars: dict | None

    :raises Exception: If there is an HTTP issue while getting node details

    :return: None on Success
    :rtype: None
    """
    try:
        s = get_session_with_profile(vars or {})
        raw_output = vars.get('raw', False) if vars else False
        node_id = vars.get('nodeid') if vars else None

        # Get node details with filters if provided
        if node_id:
            # Make targeted API call for a single node
            node_details = s.get_node_details_by_id(node_id)

            if not node_details or 'node_details' not in node_details or len(node_details['node_details']) == 0:
                print(f'No details available for node {node_id}.')
                return
        else:
            # Get all nodes
            node_details = s.get_node_details()

            if not node_details or 'node_details' not in node_details or len(node_details['node_details']) == 0:
                print('No node details available or user is not associated with any nodes.')
                return

        if raw_output:
            # Print raw JSON if requested
            print(json.dumps(node_details, indent=4))
            return

        # Print formatted node details
        for idx, node_info in enumerate(node_details['node_details'], 1):
            node_id = node_info.get('id', 'Unknown')
            _print_node_details(node_id, node_info, idx)
            print()  # Add empty line between nodes
    except Exception as e:
        log.error(e)
        print(f"Error retrieving node details: {str(e)}")

def _print_node_details(node_id, node_info, index=None):
    """
    Helper function to print formatted node details

    :param node_id: ID of the node
    :type node_id: str
    :param node_info: Node information dictionary
    :type node_info: dict
    :param index: Optional index number for the node
    :type index: int | None

    :return: None
    :rtype: None
    """
    print(f"{'=' * 50}")
    if index is not None:
        print(f"{index}. Node ID: {node_id}")
    else:
        print(f"Node ID: {node_id}")
    print(f"{'=' * 50}")

    # Print connectivity status
    status = node_info.get('status', {})
    connectivity = status.get('connectivity', {})
    connected = connectivity.get('connected', False)
    timestamp = connectivity.get('timestamp', 0)

    if connected:
        print(f"\nStatus: Online")
    else:
        if timestamp:
            timestamp_str = datetime.datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')
            print(f"\nStatus: Offline since {timestamp_str}")
        else:
            print(f"\nStatus: Offline")

    # Print config information
    config = node_info.get('config', {})
    print(f"\nConfig:")

    # Print node info
    info = config.get('info', {})
    if info:
        print(f"  Info:")
        print(f"    Name: {info.get('name', 'N/A')}")
        print(f"    Type: {info.get('type', 'N/A')}")
        print(f"    Model: {info.get('model', 'N/A')}")
        print(f"    Firmware Version: {info.get('fw_version', 'N/A')}")

    # Print node-level attributes if any
    attributes = config.get('attributes', [])
    if attributes:
        print(f"\n  Attributes:")
        for attr in attributes:
            print(f"    {attr.get('name', 'N/A')}: {attr.get('value', 'N/A')}")

    # Get params to use later
    params = node_info.get('params', {})

    # Print devices information with their params
    devices = config.get('devices', [])
    if devices:
        print(f"\n  Devices:")
        for i, device in enumerate(devices):
            device_name = device.get('name', 'N/A')
            print(f"    Device {i+1}:")
            print(f"      Name: {device_name}")
            print(f"      Type: {device.get('type', 'N/A')}")

            # Print device attributes if any
            attributes = device.get('attributes', [])
            if attributes:
                print(f"      Attributes:")
                for attr in attributes:
                    print(f"        {attr.get('name', 'N/A')}: {attr.get('data_type', 'N/A')}")

            # Print device parameters with their types
            if device_name in params:
                print(f"      Parameters:")
                device_params = params.get(device_name, {})
                # Find parameter types from the device config
                param_types = {}
                for param_config in device.get('params', []):
                    param_types[param_config.get('name')] = param_config.get('type', 'N/A')

                for param_name, param_value in device_params.items():
                    param_type = param_types.get(param_name, 'N/A')
                    print(f"        {param_name}: {param_value} ({param_type})")

    # Print services information with their params
    services = config.get('services', [])
    if services:
        print(f"\n  Services:")
        for i, service in enumerate(services):
            service_name = service.get('name', 'N/A')
            print(f"    Service {i+1}:")
            print(f"      Name: {service_name}")
            print(f"      Type: {service.get('type', 'N/A')}")

            # Print service parameters with their types
            if service_name in params:
                print(f"      Parameters:")
                service_params = params.get(service_name, {})
                # Find parameter types from the service config
                param_types = {}
                for param_config in service.get('params', []):
                    param_types[param_config.get('name')] = param_config.get('type', 'N/A')

                for param_name, param_value in service_params.items():
                    param_type = param_types.get(param_name, 'N/A')

                    # Format schedules if this is the Schedules parameter
                    if param_name == "Schedules" and param_type == "esp.param.schedules" and isinstance(param_value, list):
                        print(f"        {param_name}: ({param_type})")
                        if param_value:
                            for idx, schedule in enumerate(param_value):
                                print(f"          Schedule {idx+1}:")
                                formatted_schedule = _format_schedule(schedule)
                                for line in formatted_schedule.split('\n'):
                                    print(f"            {line}")
                        else:
                            print(f"          No schedules defined")
                    else:
                        print(f"        {param_name}: {param_value} ({param_type})")

    # Print additional metadata
    if node_info.get('metadata'):
        print(f"\nMetadata: {json.dumps(node_info.get('metadata'), indent=2)}")

    if node_info.get('tags'):
        print(f"\nTags: {', '.join(node_info.get('tags'))}")

    # Only show Node Type if it has a value
    node_type = node_info.get('node_type')
    if node_type and node_type != 'N/A':
        print(f"\nNode Type: {node_type}")

    print(f"User Role: {node_info.get('role', 'N/A')}")
    print(f"Is Primary: {node_info.get('primary', False)}")
    print(f"Is Matter: {node_info.get('is_matter', False)}")

    if node_info.get('mapping_timestamp'):
        mapping_time = datetime.datetime.fromtimestamp(node_info.get('mapping_timestamp')).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Mapping Timestamp: {mapping_time}")

    # Only print Admin Access if it exists and is not N/A
    admin_access = node_info.get('admin_access')
    if admin_access and admin_access != 'N/A':
        print(f"Admin Access: {admin_access}")

def get_schedules(vars=None):
    """
    Get schedule information for a specific node.

    :param vars: Parameters:
                 `nodeid` as key - Node ID to fetch schedules for
                 `profile` as key - Profile to use for the operation
    :type vars: dict | None

    :raises Exception: If there is an HTTP issue while getting node details

    :return: None on Success
    :rtype: None
    """
    if not vars or 'nodeid' not in vars:
        print("Error: Node ID is required.")
        return

    node_id = vars['nodeid']

    try:
        s = get_session_with_profile(vars)

        # Get node details for the specific node
        node_details = s.get_node_details_by_id(node_id)

        if not node_details or 'node_details' not in node_details:
            print(f'No details available for node {node_id}.')
            return

        # Find the node in the node_details array
        node_info = None
        for node in node_details['node_details']:
            if node.get('id') == node_id:
                node_info = node
                break

        if not node_info:
            print(f'Node {node_id} not found or not associated with current user.')
            return

        # Look for schedule service and parameters
        schedules_found = False

        # First check in config for schedule service
        if 'config' in node_info:
            config = node_info['config']

            if 'services' in config:
                for service in config['services']:
                    if service.get('type') == 'esp.service.schedule':
                        schedules_found = True
                        print(f"Node supports schedules.")
                        break

        if not schedules_found:
            print(f"Node {node_id} does not support schedules.")
            return

        # Check in params for actual schedule data
        schedule_data_found = False
        if 'params' in node_info:
            params = node_info['params']

            # Look through all devices and services for schedules
            for entity_name, entity_params in params.items():
                for param_name, param_value in entity_params.items():
                    # Check if this is a schedules parameter
                    if isinstance(param_value, list) and param_name == "Schedules":
                        schedule_data_found = True

                        if not param_value:
                            print("No schedules configured for this node.")
                            return

                        # Print each schedule
                        for idx, schedule in enumerate(param_value):
                            print(f"\nSchedule {idx+1}:")
                            print(_format_schedule(schedule))

        if not schedule_data_found:
            print("No schedules configured for this node.")

    except Exception as e:
        log.error(e)
        print(f"Error retrieving schedules: {str(e)}")

def set_schedule(vars=None):
    """
    Set schedule for a specific node. This function supports adding, editing, removing, enabling, and disabling schedules.

    :param vars: Parameters:
                 `nodeid` as key - Node ID to set schedule for
                 `operation` as key - Operation to perform (add, edit, remove, enable, disable)
                 `id` as key - Schedule ID (required for edit, remove, enable, disable)
                 `name` as key - Schedule name (required for add, optional for edit)
                 `trigger` as key - JSON string of trigger configuration (required for add, optional for edit)
                 `action` as key - JSON string of action configuration (required for add, optional for edit)
                 `info` as key - Additional information (optional)
                 `flags` as key - General purpose flags (optional)
                 `profile` as key - Profile to use for this operation (optional)
    :type vars: dict | None

    :raises Exception: If there is an HTTP issue while setting schedule

    :return: None on Success
    :rtype: None
    """
    if not vars or 'nodeid' not in vars:
        print("Error: Node ID is required.")
        return

    if 'operation' not in vars:
        print("Error: Operation is required (add, edit, remove, enable, disable).")
        return

    node_id = vars['nodeid']
    operation = vars['operation'].lower()

    # Validate operation
    valid_operations = ['add', 'edit', 'remove', 'enable', 'disable']
    if operation not in valid_operations:
        print(f"Error: Invalid operation. Must be one of {', '.join(valid_operations)}.")
        return

    # For operations other than 'add', id is required
    if operation != 'add' and ('id' not in vars or vars['id'] is None):
        print("Error: Schedule ID is required for this operation.")
        return

    # For 'add' operation, name, trigger, and action are required
    if operation == 'add':
        if 'name' not in vars or vars['name'] is None:
            print("Error: Schedule name is required for add operation.")
            return
        if 'trigger' not in vars or vars['trigger'] is None:
            print("Error: Trigger configuration is required for add operation. Please provide it with --trigger option.")
            print("Example: --trigger '{\"m\": 1110, \"d\": 31}' for 6:30 PM on weekdays")
            return
        if 'action' not in vars or vars['action'] is None:
            print("Error: Action configuration is required for add operation. Please provide it with --action option.")
            print("Example: --action '{\"Light\": {\"Power\": true}}' to turn on a light")
            return

    # Create the schedule data structure
    schedule = {}

    # Set operation first
    schedule['operation'] = operation

    # Set ID field
    if operation != 'add' and 'id' in vars:
        schedule['id'] = vars['id']

    if operation == 'add':
        # Always generate a random 4-character hexadecimal ID for new schedules
        import random
        generated_id = ''.join(random.choice('0123456789ABCDEF') for _ in range(4))
        schedule['id'] = generated_id

    # For simple operations like enable/disable/remove, we only need id and operation
    if operation in ['enable', 'disable', 'remove']:
        # Create the full params object
        params = {
            "Schedule": {
                "Schedules": [schedule]
            }
        }

        try:
            # Set the parameters on the node using profile-aware session
            curr_session = get_session_with_profile(vars)
            n = node.Node(node_id, curr_session)
            response = n.set_node_params(params)

            # Determine if the operation was successful
            success = False
            if isinstance(response, dict) and response.get('status', '').lower() == 'success':
                success = True
            elif isinstance(response, bool) and response:
                success = True

            if success:
                op_str = {
                    'add': 'added',
                    'edit': 'updated',
                    'remove': 'removed',
                    'enable': 'enabled',
                    'disable': 'disabled'
                }.get(operation, operation)

                print(f"Schedule successfully {op_str}.")
            else:
                if isinstance(response, dict):
                    print(f"Error setting schedule: {response.get('description', 'Unknown error')}")
                else:
                    print(f"Error setting schedule: Unexpected response format")

        except Exception as e:
            log.error(e)
            print(f"Error setting schedule: {str(e)}")

        return

    # For add and edit operations, set additional fields
    if 'name' in vars:
        schedule['name'] = vars['name']

    # Set trigger if provided
    if 'trigger' in vars and vars['trigger'] is not None:
        try:
            trigger_data = json.loads(vars['trigger'])

            # If this is an add operation with rsec but no ts, add current timestamp
            if operation == 'add' and 'rsec' in trigger_data and 'ts' not in trigger_data:
                import time
                trigger_data['ts'] = int(time.time())

            schedule['triggers'] = [trigger_data]
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for trigger configuration.")
            return
    elif operation == 'add':
        # For add operation, trigger is required
        print("Error: Trigger configuration is required for add operation. Please provide it with --trigger option.")
        print("Example: --trigger '{\"m\": 1110, \"d\": 31}' for 6:30 PM on weekdays")
        return

    # Set action if provided
    if 'action' in vars and vars['action'] is not None:
        try:
            action_data = json.loads(vars['action'])
            schedule['action'] = action_data
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for action configuration.")
            return
    elif operation == 'add':
        # For add operation, action is required
        print("Error: Action configuration is required for add operation. Please provide it with --action option.")
        print("Example: --action '{\"Light\": {\"Power\": true}}' to turn on a light")
        return

    # Set additional fields if provided
    if 'info' in vars:
        schedule['info'] = vars['info']

    if 'flags' in vars and vars['flags'] is not None and vars['flags'].isdigit():
        schedule['flags'] = int(vars['flags'])

    # Create the full params object
    params = {
        "Schedule": {
            "Schedules": [schedule]
        }
    }

    try:
        # Set the parameters on the node using profile-aware session
        curr_session = get_session_with_profile(vars)
        n = node.Node(node_id, curr_session)
        response = n.set_node_params(params)

        # Determine if the operation was successful
        success = False
        if isinstance(response, dict) and response.get('status', '').lower() == 'success':
            success = True
        elif isinstance(response, bool) and response:
            success = True

        if success:
            op_str = {
                'add': 'added',
                'edit': 'updated',
                'remove': 'removed',
                'enable': 'enabled',
                'disable': 'disabled'
            }.get(operation, operation)

            if operation == 'add':
                print(f"Schedule successfully {op_str} with ID: {generated_id}")
            else:
                print(f"Schedule successfully {op_str}.")
        else:
            if isinstance(response, dict):
                print(f"Error setting schedule: {response.get('description', 'Unknown error')}")
            else:
                print(f"Error setting schedule: Unexpected response format")

    except Exception as e:
        log.error(e)
        print(f"Error setting schedule: {str(e)}")

def _check_user_input(node_ids_str):
    log.debug("Check user input....")
    # Check user input format
    input_pattern = re.compile("^[0-9A-Za-z]+(,[0-9A-Za-z]+)*$")
    result = input_pattern.match(node_ids_str)
    log.debug("User input result: {}".format(result))
    if result is None:
        sys.exit("Invalid format. Expected: <nodeid>,<nodeid>,... (no spaces)")
    return True

def _print_api_error(node_json_resp):
    print("{:<7} ({}):  {}".format(
        node_json_resp['status'].capitalize(),
        node_json_resp['error_code'],
        node_json_resp['description'])
        )

def _set_node_ids_list(node_ids):
    # Create list from node ids string
    node_id_list = node_ids.split(',')
    node_id_list = [ item.strip() for item in node_id_list ]
    log.debug("Node ids list: {}".format(node_id_list))
    return node_id_list

def sharing_request_op(accept_request=False, request_id=None, profile_override=None):
    """
    Accept or Decline the sharing request.

    :param accept_request: Request to accept or decline the request
    :type accept_request: bool

    :param request_id: Request ID for accept/decline
    :type request_id: str
    
    :param profile_override: Optional profile to use for this operation
    :type profile_override: str

    :raises Exception: If there is an issue
                       while accept/decline request

    :return: API response
    :rtype: dict
    """
    # Create API data dictionary
    api_data = {}
    api_data['accept'] = accept_request
    api_data['request_id'] = request_id

    # Use profile-aware session
    vars_dict = {'profile': profile_override} if profile_override else {}
    curr_session = get_session_with_profile(vars_dict)
    node_obj = node.Node(None, curr_session)
    log.debug("API data set: {}".format(api_data))

    # API to accept or decline node sharing request
    node_json_resp = node_obj.request_op(api_data)
    log.debug("Sharing request API response: {}".format(node_json_resp))

    return node_json_resp

def list_sharing_details(node_id=None, primary_user=False, request_id=None, list_requests=False, profile_override=None):
    """
    List sharing details of all nodes associated with user
    or List pending requests

    :param node_id: Node Id of the node(s)
                 (if not provided, is set to all nodes associated with user)
    :type node_id: str

    :param primary_user: User is primary or secondary
                 (if provided, user is primary user)
    :type primary_user: bool

    :param request_id: Id of sharing request
    :type request_id: str

    :param list_requests:
                 If True, list pending requests
                 If False, list sharing details of nodes
    :type list_requests: bool
    
    :param profile_override: Optional profile to use for this operation
    :type profile_override: str

    :raises Exception: If there is an issue
                       while listing details

    :return: API response
    :rtype: dict
    """
    # Use profile-aware session
    vars_dict = {'profile': profile_override} if profile_override else {}
    curr_session = get_session_with_profile(vars_dict)
    node_obj = node.Node(node_id, curr_session)
    log.debug("Node id received from user: {}".format(node_id))

    # Set data for listing pending requests
    if list_requests:
        # Create API query params
        api_params = {}
        if request_id:
            api_params['id'] = request_id
        api_params['primary_user'] = "{}".format(primary_user)

        node_json_resp = node_obj.get_shared_nodes_request(api_params)
        log.debug("List sharing request response: {}".format(node_json_resp))
    else:
        # Get sharing details of all nodes associated with user
        # API
        node_json_resp = node_obj.get_sharing_details_of_nodes()
        log.debug("Get shared nodes response: {}".format(node_json_resp))

    return node_json_resp

def add_user_to_share_nodes(nodes=None, user=None, profile_override=None):
    """
    Add user to share nodes

    :param nodes: Node Id of the node(s)
    :type nodes: str

    :param user: User name
    :type user: str
    
    :param profile_override: Optional profile to use for this operation
    :type profile_override: str

    :raises Exception: If there is an issue
                       while adding user to share nodes

    :return: API response
    :rtype: dict
    """
    log.debug("Adding user to share nodes")

    # Remove any spaces if exist
    nodes = nodes.strip()
    # Check user input format
    ret_status = _check_user_input(nodes)
    # Create list from node ids string
    node_id_list = _set_node_ids_list(nodes)
    log.debug("Node ids list: {}".format(node_id_list))

    log.debug("User name is set: {}".format(user))

    # Create API input info
    api_input = {}
    api_input['nodes'] = node_id_list
    api_input['user_name'] = user
    log.debug("API data set: {}".format(api_input))

    # API with profile-aware session
    vars_dict = {'profile': profile_override} if profile_override else {}
    curr_session = get_session_with_profile(vars_dict)
    node_obj = node.Node(None, curr_session)
    node_json_resp = node_obj.add_user_for_sharing(api_input)
    log.debug("Set shared nodes response: {}".format(node_json_resp))

    return node_json_resp

def remove_sharing(nodes=None, user=None, request_id=None, profile_override=None):
    """
    Remove user from shared nodes or
    Remove sharing request

    :param nodes: Node Id for the node
    :type nodes: str

    :param user: User name
    :type user: str

    :param request_id: Id of sharing request
    :type request_id: str
    
    :param profile_override: Optional profile to use for this operation
    :type profile_override: str

    :raises Exception: If there is an issue
                       while remove operation

    :return: API response
    :rtype: dict
    """
    print('\nPlease make sure current (logged-in) user is Primary user\n')

    node_json_resp = None
    # Use profile-aware session
    vars_dict = {'profile': profile_override} if profile_override else {}
    curr_session = get_session_with_profile(vars_dict)
    node_obj = node.Node(None, curr_session)
    
    if request_id:
        # API call to remove the shared nodes request
        node_json_resp = node_obj.remove_shared_nodes_request(request_id)
        log.debug("Remove sharing request response: {}".format(node_json_resp))
    else:
        # Remove any spaces if exist
        node_ids = nodes.strip()

        # Check user input format
        ret_status = _check_user_input(node_ids)

        # Create API query params dictionary
        api_params = {}
        api_params['nodes'] = node_ids
        api_params['user_name'] = user
        log.debug("API data set to: {}".format(api_params))

        # API call to remove the shared nodes
        node_json_resp = node_obj.remove_user_from_shared_nodes(api_params)
        log.debug("Remove user from shared nodes response: {}".format(node_json_resp))

    return node_json_resp

def _get_status(resp):
    return(resp['status'].capitalize())

def _get_description(resp):
    return(resp['description'])

def _get_request_id(resp):
    return(resp['request_id'])

def _get_request_expiration(request):
    total_expiry_days = 7
    expiration_str = ""

    curr_time = datetime.datetime.now()
    log.debug("Current time is set to: {}".format(curr_time))

    creation_time = datetime.datetime.fromtimestamp(request['request_timestamp'])
    log.debug("Creation timestamp received : {}".format(creation_time))

    timedelta = curr_time - creation_time
    log.debug("Timedelta is : {}".format(timedelta))
    days_left = total_expiry_days - timedelta.days
    log.debug("Days left for request to expire: {}".format(days_left))
    if days_left <= 0:
        expiration_str = "** Request expired **"
    elif days_left == 1:
        expiration_str = "** Request will expire today **"
    else:
        expiration_str = "** Request will expire in {} day(s) **".format(days_left)
    log.debug("Expiration is: {}".format(expiration_str))
    return expiration_str

def _print_request_details(resp, is_primary_user=False):
    try:
        log.debug("Printing request details")
        requests_in_resp = resp['sharing_requests']
        request_exists = False
        if not requests_in_resp:
            print("No pending requests")
            return
        for request in requests_in_resp:
            nodes_str = ""
            if request['request_status'].lower() == 'declined':
                continue
            request_exists = True
            print("\n{:<12}: {}".format('Request Id',request['request_id']))
            for n_id in request['node_ids']:
                nodes_str += "{},".format(n_id)
            nodes_str = nodes_str.rstrip(',')
            print("{:<12}: {}".format('Node Id(s)', nodes_str))
            if is_primary_user:
                print("{:<12}: {}".format('Shared with', request['user_name']))
            else:
                print("{:<12}: {}".format('Shared by', request['primary_user_name']))
            expiration_msg = _get_request_expiration(request)
            print(expiration_msg)

        if not request_exists:
            print("No pending requests")

    except KeyError as err:
        print(err)
        log.debug("Key Error while printing request details: {}".format(err))
        print("Error in displaying details...Please check API Json...Exiting...")
        sys.exit(0)
    log.debug("Done printing request details")

def _print_sharing_details(resp):
    try:
        log.debug("Printing sharing details of nodes")
        nodes_in_resp = resp['node_sharing']
        for nodes in nodes_in_resp:
            primary_users = ""
            secondary_users = ""
            print("\nNode Id: {}".format(nodes['node_id']))

            for user in nodes['users']['primary']:
                primary_users += "{},".format(user)
            primary_users = primary_users.rstrip(',')
            print("{:<7}: {:<9}: {}".format('Users', 'Primary', primary_users), end='')

            if 'secondary' in nodes['users'].keys():
                for user in nodes['users']['secondary']:
                    secondary_users += "{},".format(user)
                secondary_users = secondary_users.rstrip(',')
                print("\n{:>18}: {}".format('Secondary', secondary_users), end='')
            print()

    except KeyError as err:
        log.debug("Key Error while printing sharing details of nodes: {}".format(err))
        print("Error in displaying details...Please check API Json...Exiting...")
        sys.exit(0)
    log.debug("Done printing sharing details of nodes")

'''
Node Sharing operations based on user input
'''
def node_sharing_ops(vars=None):
    try:
        op = ""

        log.debug("Performing Node Sharing operations")

        # Set action if given
        try:
            action = vars['sharing_ops'].lower()
        except AttributeError:
            print(vars['parser'].format_help())
            sys.exit(0)

        # Set operation to base action
        op = action
        
        # Get profile override if specified
        profile_override = vars.get('profile')

        if action == 'add_user':
            # Share nodes with user
            print("Adding user to share node(s)")
            node_json_resp = add_user_to_share_nodes(nodes=vars['nodes'], user=vars['user'], profile_override=profile_override)

            # Print success response
            if 'status' in node_json_resp and node_json_resp['status'].lower() == 'success':
                print("{:<11}: {}\n{:<11}: {}".format(
                    _get_status(node_json_resp),
                    _get_description(node_json_resp),
                    'Request Id',
                    _get_request_id(node_json_resp))
                    )
        elif action == "accept":
            # Accept sharing request
            node_json_resp = sharing_request_op(accept_request=True, request_id=vars['id'], profile_override=profile_override)

            # Print success response
            if 'status' in node_json_resp and node_json_resp['status'].lower() == 'success':
                print("{:<11}: {}".format(
                    _get_status(node_json_resp),
                    _get_description(node_json_resp))
                    )
        elif action == "decline":
            # Decline sharing request
            node_json_resp = sharing_request_op(accept_request=False, request_id=vars['id'], profile_override=profile_override)

            # Print success response
            if 'status' in node_json_resp and node_json_resp['status'].lower() == 'success':
                print("{:<11}: {}".format(
                    _get_status(node_json_resp),
                    _get_description(node_json_resp))
                    )
        elif action == "cancel":
            log.debug("Performing action: {}".format(action))
            # Cancel sharing request
            print("Cancelling request")
            node_json_resp = remove_sharing(request_id=vars['id'], profile_override=profile_override)

            # Print success response
            if 'status' in node_json_resp and node_json_resp['status'].lower() == 'success':
                print("{}: {}".format(
                    _get_status(node_json_resp),
                    _get_description(node_json_resp))
                    )
        elif action == "remove_user":
            log.debug("Performing action: {}".format(action))
            # Remove nodes shared with user
            print("Removing user from shared nodes")
            node_json_resp = remove_sharing(nodes=vars['nodes'], user=vars['user'], profile_override=profile_override)

            # Print success response
            if 'status' in node_json_resp and node_json_resp['status'].lower() == 'success':
                print("{}: {}".format(
                    _get_status(node_json_resp),
                    _get_description(node_json_resp))
                    )
        elif action == "list_nodes":
            log.debug("Performing action: {}".format(action))

            log.debug("List sharing details of nodes associated with user")
            print("Displaying sharing details")
            # List sharing details of all nodes associated with user
            node_json_resp = list_sharing_details(node_id=vars['node'], profile_override=profile_override)

            # Print success response
            if 'node_sharing' in node_json_resp:
                _print_sharing_details(node_json_resp)
        elif action == "list_requests":
            log.debug("Performing action: {}".format(action))

            log.debug("List pending requests")
            print("Displaying pending requests")
            if vars['primary_user']:
                print("Current (logged-in) user is set as Primary user")
            else:
                print("Current (logged-in) user is set as Secondary user")
            # List pending sharing requests
            node_json_resp = list_sharing_details(primary_user=vars['primary_user'],
                                                    request_id=vars['id'],
                                                    list_requests=True,
                                                    profile_override=profile_override
                                                    )
            # Print success response
            if 'sharing_requests' in node_json_resp:
                _print_request_details(node_json_resp, is_primary_user=vars['primary_user'])

    except Exception as get_node_status_err:
        log.error(get_node_status_err)
        return
    else:
        if 'status' in node_json_resp and node_json_resp['status'].lower() != 'success':
            log.debug("Operation {} failed\nresp: {}".format(op, node_json_resp))
            _print_api_error(node_json_resp)
            return
    log.debug("Operation `{}` was successful".format(op))

def get_node_config(vars=None):
    """
    Shows the configuration of the node.

    :param vars: `nodeid` as key - Node ID for the node
                 `profile` as key - Profile to use for the operation
    :type vars: dict | None

    :raises Exception: If there is an HTTP issue while getting node config

    :return: None on Success
    :rtype: None
    """
    try:
        node_config = None
        s = get_session_with_profile(vars or {})
        n = node.Node(vars['nodeid'], s)
        node_config = n.get_node_config()
    except Exception as get_nodes_err:
        log.error(get_nodes_err)
    else:
        print(json.dumps(node_config, indent=4))
    return node_config


def get_node_status(vars=None):
    """
    Shows the online/offline status of the node.

    :param vars: `nodeid` as key - Node ID for the node
                 `profile` as key - Profile to use for the operation
    :type vars: dict | None

    :raises Exception: If there is an HTTP issue while getting node status

    :return: None on Success
    :rtype: None
    """
    try:
        s = get_session_with_profile(vars or {})
        n = node.Node(vars['nodeid'], s)
        node_status = n.get_node_status()
    except Exception as get_node_status_err:
        log.error(get_node_status_err)
    else:
        print(json.dumps(node_status, indent=4))
    return


def set_params(vars=None):
    """
    Set parameters of the node.

    :param vars: `nodeid` as key - Node ID for the node
                 `data` as key - JSON data containing parameters to be set
                 `filepath` as key - Path of the JSON file containing parameters
                 `profile` as key - Profile to use for the operation
    :type vars: dict | None

    :raises NetworkError: If there is a network connection issue during
                          HTTP request for setting node params
    :raises Exception: If there is an HTTP issue while setting params or
                       JSON format issue in HTTP response

    :return: None on Success
    :rtype: None
    """

    data = None
    if vars['data']:
        data = json.loads(vars['data'])
    else:
        with open(vars['filepath'], 'r') as data_file:
            data = json.load(data_file)

    try:
        s = get_session_with_profile(vars or {})
        n = node.Node(vars['nodeid'], s)
        status = n.set_node_params(data)
    except SSLError:
        log.error(SSLError())
    except NetworkError as conn_err:
        print(conn_err)
        log.warn(conn_err)
    except Exception as set_params_err:
        log.error(set_params_err)
    else:
        print('Node state updated successfully.')
    return


def get_params(vars=None):
    """
    Get parameters of the node.

    :param vars: `nodeid` as key - Node ID for the node
                 `profile` as key - Profile to use for the operation
    :type vars: dict | None

    :raises Exception: If there is an HTTP issue while getting params or
                       JSON format issue in HTTP response

    :return: None on Success
    :rtype: None
    """
    try:
        params = None
        s = get_session_with_profile(vars or {})
        n = node.Node(vars['nodeid'], s)
        params = n.get_node_params()
    except SSLError:
        log.error(SSLError())
    except NetworkError as conn_err:
        print(conn_err)
        log.warn(conn_err)
    except Exception as get_params_err:
        log.error(get_params_err)
    else:
        if params is None:
            log.error('Node status not updated.')
            return
        else:
            print(json.dumps(params, indent=4))
    return params


def remove_node(vars=None):
    """
    Removes the user node mapping.

    :param vars: `nodeid` as key - Node ID for the node
                 `profile` as key - Profile to use for the operation
    :type vars: dict | None

    :raises NetworkError: If there is a network connection issue during
                          HTTP request for removing node
    :raises Exception: If there is an HTTP issue while removing node or
                       JSON format issue in HTTP response

    :return: None on Success
    :rtype: None
    """
    log.info('Removing user node mapping for node ' + vars['nodeid'])
    try:
        s = get_session_with_profile(vars or {})
        n = node.Node(vars['nodeid'], s)
        params = n.remove_user_node_mapping()
    except Exception as remove_node_err:
        log.error(remove_node_err)
    else:
        log.debug('Removed the user node mapping successfully.')
        print('Removed node ' + vars['nodeid'] + ' successfully.')
    return


def get_mqtt_host(vars=None):
    """
    Shows the MQTT Host endpoint.

    :param vars: Optional parameters including 'profile'
    :type vars: dict | None

    :raises Exception: If there is an HTTP issue while getting MQTT Host

    :return: None on Success
    :rtype: None
    """
    try:
        s = get_session_with_profile(vars or {})
        mqtt_host = s.get_mqtt_host()
        if mqtt_host is not None:
            print(mqtt_host)
    except Exception as e:
        log.error(e)
    return


def claim_node(vars=None):
    """
    Claim the node connected to the given serial port
    (Get cloud credentials)

    :param vars: `port` as key - Serial Port, defaults to `None`
    :type vars: str | None

    :raises Exception: If there is an HTTP issue while claiming

    :return: None on Success
    :rtype: None
    """
    try:
        if not vars['port'] and not vars['mac'] and not vars['addr'] and not vars['platform'] and not vars['outdir']:
            sys.exit(vars['parser'].print_help())
        if vars['addr'] and not vars['port'] and not vars['platform']:
            sys.exit('Invalid. <port> or --platform argument is needed.')
        if vars['mac']:
            if not re.match(r'([0-9A-F]:?){12}', vars['mac']):
                sys.exit('Invalid MAC address.')

        from rmaker_tools.rmaker_claim.claim import claim
        claim(port=vars['port'], node_platform=vars['platform'], mac_addr=vars['mac'], flash_address=vars['addr'], matter=vars['matter'], out_dir=vars['outdir'])
    except Exception as claim_err:
        log.error(claim_err)
        return

def ota_upgrade(vars=None):
    """
    Upload OTA Firmware image and start OTA Upgrade

    :param vars: `nodeid` as key - Node ID for the node
                 `otaimagepath` as key - OTA Firmware image path
                 `profile` as key - Profile to use for the operation
    :type vars: dict | None

    :raises Exception: If there is an HTTP issue while uploading OTA Firmware image

    :return: None on Success
    :rtype: None
    """
    try:
        node_id = vars['nodeid']
        ota_image_path = vars['otaimagepath']
        
        s = get_session_with_profile(vars or {})
        n = node.Node(node_id, s)
        response = n.upload_ota_image(ota_image_path)
        if response is not None:
            print(json.dumps(response, indent=4))
    except Exception as e:
        log.error(e)
    return