# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import json
import random
import time
from rmaker_lib.logger import log


def format_schedule_params(operation, schedule_id=None, name=None, trigger=None, action=None, 
                          info=None, flags=None, auto_generate_id=True):
    """
    Format schedule parameters for ESP RainMaker API.
    
    This utility function creates the proper parameter structure for schedule operations
    that can be used with node.set_node_params().
    
    :param operation: Operation to perform ('add', 'edit', 'remove', 'enable', 'disable')
    :type operation: str
    :param schedule_id: Schedule ID (required for edit, remove, enable, disable operations)
    :type schedule_id: str | None
    :param name: Schedule name (required for add operation, optional for edit)
    :type name: str | None
    :param trigger: Trigger configuration - can be dict or JSON string
    :type trigger: dict | str | None
    :param action: Action configuration - can be dict or JSON string  
    :type action: dict | str | None
    :param info: Additional information for the schedule
    :type info: str | None
    :param flags: General purpose flags for the schedule
    :type flags: str | int | None
    :param auto_generate_id: Whether to auto-generate ID for 'add' operations
    :type auto_generate_id: bool
    
    :raises ValueError: If required parameters are missing or invalid
    :raises json.JSONDecodeError: If trigger/action JSON strings are invalid
    
    :return: Formatted parameters dict ready for node.set_node_params()
    :rtype: dict
    """
    # Validate operation
    valid_operations = ['add', 'edit', 'remove', 'enable', 'disable']
    if operation not in valid_operations:
        raise ValueError(f"Invalid operation. Must be one of {', '.join(valid_operations)}.")
    
    # For operations other than 'add', schedule_id is required
    if operation != 'add' and not schedule_id:
        raise ValueError("Schedule ID is required for this operation.")
    
    # For 'add' operation, name, trigger, and action are required
    if operation == 'add':
        if not name:
            raise ValueError("Schedule name is required for add operation.")
        if trigger is None:
            raise ValueError("Trigger configuration is required for add operation.")
        if action is None:
            raise ValueError("Action configuration is required for add operation.")
    
    # Create the schedule data structure
    schedule = {'operation': operation}
    
    # Handle ID field
    if operation != 'add' and schedule_id:
        schedule['id'] = schedule_id
    elif operation == 'add':
        if auto_generate_id:
            # Generate a random 4-character hexadecimal ID for new schedules
            generated_id = ''.join(random.choice('0123456789ABCDEF') for _ in range(4))
            schedule['id'] = generated_id
        elif schedule_id:
            schedule['id'] = schedule_id
    
    # For simple operations like enable/disable/remove, we only need id and operation
    if operation in ['enable', 'disable', 'remove']:
        return {
            "Schedule": {
                "Schedules": [schedule]
            }
        }
    
    # For add and edit operations, set additional fields
    if name:
        schedule['name'] = name
    
    # Handle trigger configuration
    if trigger is not None:
        # Parse trigger if it's a JSON string
        if isinstance(trigger, str):
            try:
                trigger_data = json.loads(trigger)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format for trigger configuration.")
        else:
            trigger_data = trigger
        

        
        # CLI uses 'triggers' array, while MCP might use single 'trigger'
        # We'll standardize on 'triggers' array for consistency with CLI
        schedule['triggers'] = [trigger_data]
    elif operation == 'add':
        raise ValueError("Trigger configuration is required for add operation.")
    
    # Handle action configuration
    if action is not None:
        # Parse action if it's a JSON string
        if isinstance(action, str):
            try:
                action_data = json.loads(action)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format for action configuration.")
        else:
            action_data = action
        
        schedule['action'] = action_data
    elif operation == 'add':
        raise ValueError("Action configuration is required for add operation.")
    
    # Handle additional fields
    if info:
        schedule['info'] = info
    
    if flags is not None:
        if isinstance(flags, str) and flags.isdigit():
            schedule['flags'] = int(flags)
        elif isinstance(flags, int):
            schedule['flags'] = flags
        elif flags:  # Non-empty string that's not a digit
            raise ValueError("Flags must be a valid integer or integer string.")
    
    # Create the full params object
    return {
        "Schedule": {
            "Schedules": [schedule]
        }
    }


def extract_schedules_from_node_details(node_details, node_id):
    """
    Extract schedule information from node details response.
    
    :param node_details: Node details response from API
    :type node_details: dict
    :param node_id: Target node ID
    :type node_id: str
    
    :return: Dictionary with schedule information
    :rtype: dict
    """
    if not node_details or 'node_details' not in node_details:
        return {
            "node_id": node_id,
            "error": f"No details available for node {node_id}",
            "schedules_supported": False,
            "schedules": [],
            "schedule_count": 0
        }
    
    # Find the node in the node_details array
    node_info = None
    for node in node_details['node_details']:
        if node.get('id') == node_id:
            node_info = node
            break
    
    if not node_info:
        return {
            "node_id": node_id,
            "error": f"Node {node_id} not found or not associated with current user",
            "schedules_supported": False,
            "schedules": [],
            "schedule_count": 0
        }
    
    # Check for schedule service support
    schedules_supported = False
    if 'config' in node_info:
        config = node_info['config']
        if 'services' in config:
            for service in config['services']:
                if service.get('type') == 'esp.service.schedule':
                    schedules_supported = True
                    break
    
    if not schedules_supported:
        return {
            "node_id": node_id,
            "schedules_supported": False,
            "schedules": [],
            "schedule_count": 0,
            "message": f"Node {node_id} does not support schedules"
        }
    
    # Extract actual schedule data
    schedule_data = []
    if 'params' in node_info:
        params = node_info['params']
        
        # Look through all devices and services for schedules
        for entity_name, entity_params in params.items():
            for param_name, param_value in entity_params.items():
                # Check if this is a schedules parameter
                if isinstance(param_value, list) and param_name == "Schedules":
                    schedule_data = param_value
                    break
    
    return {
        "node_id": node_id,
        "schedules_supported": True,
        "schedules": schedule_data if schedule_data else [],
        "schedule_count": len(schedule_data) if schedule_data else 0
    } 