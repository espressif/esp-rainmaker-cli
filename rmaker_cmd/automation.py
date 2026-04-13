# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

from rmaker_lib.profile_utils import get_session_with_profile
import json


def _handle_error(e, operation):
    """Helper function to handle errors and extract descriptions from API responses"""
    error_msg = str(e)
    try:
        if hasattr(e, 'response') and e.response is not None:
            resp = e.response.json()
            if 'description' in resp:
                error_msg = resp['description']
    except Exception:
        pass
    print(f"Failed to {operation}: {error_msg}")


def _parse_json(value, field_name):
    """Parse a JSON string, returning the parsed object or None on error."""
    try:
        return json.loads(value)
    except Exception as e:
        print(f"Invalid JSON for {field_name}: {e}")
        return None


def _parse_location(location_str):
    """Parse 'lat,long' string into location dict."""
    parts = location_str.split(',')
    if len(parts) != 2:
        print("Invalid location format. Use: lat,long (e.g., 18.521428,73.8544541)")
        return None
    return {"latitude": parts[0].strip(), "longitude": parts[1].strip()}


def automation_add(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        name = vars['name']
        event_type = vars['event_type']
        event_jsons = vars['event']
        action_json = vars['action']
        node_id = vars.get('node_id')
        location = vars.get('location')
        event_operator = vars.get('event_operator')
        retrigger = vars.get('retrigger', False)
        metadata_arg = vars.get('metadata')

        # Map 'params' to 'node_params' for the API
        api_event_type = 'node_params' if event_type == 'params' else event_type

        # Validate event_type-specific requirements
        if event_type == 'params' and not node_id:
            print("Error: --node-id is required when --event-type is 'params'")
            return
        if event_type in ('weather', 'daylight') and not location:
            print(f"Error: --location is required when --event-type is '{event_type}'")
            return

        # Parse events
        events = []
        for ev in event_jsons:
            parsed = _parse_json(ev, 'event')
            if parsed is None:
                return
            events.append(parsed)

        # Validate event_operator if multiple events
        if len(events) > 1 and not event_operator:
            print("Error: --event-operator (AND/OR) is required when multiple events are specified")
            return

        # Parse action
        action = _parse_json(action_json, 'action')
        if action is None:
            return
        if isinstance(action, dict):
            actions = [action]
        elif isinstance(action, list):
            actions = action
        else:
            print("Error: --action must be a JSON object or array of objects")
            return

        # Build payload
        payload = {
            'name': name,
            'event_type': api_event_type,
            'events': events,
            'actions': actions,
            'retrigger': retrigger,
        }
        if node_id:
            payload['node_id'] = node_id
        if location:
            loc = _parse_location(location)
            if loc is None:
                return
            payload['location'] = loc
        if event_operator:
            payload['event_operator'] = event_operator.lower()
        if metadata_arg:
            metadata = _parse_json(metadata_arg, 'metadata')
            if metadata is None:
                return
            payload['metadata'] = metadata

        resp = s.create_automation(payload)
        print("Automation created successfully:")
        print(json.dumps(resp, indent=2))
    except Exception as e:
        _handle_error(e, "create automation")


def automation_edit(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        automation_id = vars['id']

        payload = {}
        if vars.get('name'):
            payload['name'] = vars['name']
        if vars.get('node_id'):
            payload['node_id'] = vars['node_id']
        if vars.get('event'):
            events = []
            for ev in vars['event']:
                parsed = _parse_json(ev, 'event')
                if parsed is None:
                    return
                events.append(parsed)
            payload['events'] = events
        if vars.get('action'):
            action = _parse_json(vars['action'], 'action')
            if action is None:
                return
            if isinstance(action, dict):
                payload['actions'] = [action]
            elif isinstance(action, list):
                payload['actions'] = action
            else:
                print("Error: --action must be a JSON object or array of objects")
                return
        if vars.get('event_operator'):
            payload['event_operator'] = vars['event_operator'].lower()
        if vars.get('location'):
            loc = _parse_location(vars['location'])
            if loc is None:
                return
            payload['location'] = loc
        if vars.get('metadata'):
            metadata = _parse_json(vars['metadata'], 'metadata')
            if metadata is None:
                return
            payload['metadata'] = metadata

        # Handle retrigger/no-retrigger
        if vars.get('retrigger'):
            payload['retrigger'] = True
        elif vars.get('no_retrigger'):
            payload['retrigger'] = False

        # Handle enabled/disabled
        if vars.get('enabled'):
            payload['enabled'] = True
        elif vars.get('disabled'):
            payload['enabled'] = False

        if not payload:
            print("No fields to update. Provide at least one option to edit.")
            return

        resp = s.update_automation(automation_id, payload)
        print("Automation updated successfully:")
        print(json.dumps(resp, indent=2))
    except Exception as e:
        _handle_error(e, "update automation")


def automation_remove(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        automation_id = vars['id']
        resp = s.remove_automation(automation_id)
        print("Automation removed successfully:")
        print(json.dumps(resp, indent=2))
    except Exception as e:
        _handle_error(e, "remove automation")


def automation_get(vars=None):
    try:
        s = get_session_with_profile(vars or {})
        automation_id = vars.get('id')
        node_id = vars.get('node_id')
        resp = s.get_automations(automation_id=automation_id, node_id=node_id)

        if not resp:
            print("No automations found.")
            return

        automations = resp.get('automation_trigger_actions', [])
        if not automations:
            print("No automations found.")
            return

        if automation_id:
            print("Automation details:")
        else:
            print(f"Automations ({len(automations)}):")
        print(json.dumps(automations, indent=2))
    except Exception as e:
        _handle_error(e, "get automations")
