# Command Response Documentation

ESP RainMaker provides a Command Response feature (Beta) that allows you to send commands to your nodes and retrieve their responses. This is particularly useful for custom device operations that aren't covered by standard parameters.

## Overview

The Command Response feature involves:
1. Creating a command request with a specific command ID and data
2. Sending this request to one or more nodes
3. Retrieving the responses from those nodes

## Commands

### Creating a Command Request

```bash
esp-rainmaker-cli create_cmd_request <nodes> <cmd> <data> [--timeout <seconds>]
```

Where:
- `nodes` is a comma-separated list of node IDs (up to 25)
- `cmd` is a numeric command ID
- `data` is a JSON string containing the command data
- `--timeout` (optional) is the time in seconds until the command request expires (default: 30)

Example:
```bash
esp-rainmaker-cli create_cmd_request 686725E6AA20 4096 '{"brightness":50}' --timeout 60
```

The command will return:
- A request ID (used to retrieve responses)
- Initial responses indicating that the command is in progress

### Getting Command Responses

```bash
esp-rainmaker-cli get_cmd_requests <request_id> [options]
```

Where:
- `request_id` is the ID returned from the create_cmd_request command

Options:
- `--node_id` - Filter responses for a specific node
- `--start_id` - Start ID for pagination
- `--num_records` - Number of records to retrieve

Example:
```bash
esp-rainmaker-cli get_cmd_requests EQPf7Rj7HFiBhFhvNMjLaB
```

## Command Response Process in Detail

### Creating a Command Request

1. **Prepare your command data**:
   - Identify the target nodes
   - Determine the command ID (this is application-specific)
   - Format your command data as a JSON string

2. **Send the command request**:
   ```bash
   esp-rainmaker-cli create_cmd_request 686725E6AA20 4096 '{"brightness":50}' --timeout 60
   ```

3. **Note the request ID returned**:
   ```
   Request Id: EQPf7Rj7HFiBhFhvNMjLaB
   ```

4. **Check initial responses**:
   ```
   Responses: [{'node_ids': ['686725E6AA20'], 'response': {'status': 'success', 'description': 'in_progress'}}]
   ```

### Getting Command Responses

1. **Query for responses using the request ID**:
   ```bash
   esp-rainmaker-cli get_cmd_requests EQPf7Rj7HFiBhFhvNMjLaB
   ```

2. **Review the response data**:
   ```
   Requests: [{'node_id': '686725E6AA20', 'request_id': 'EQPf7Rj7HFiBhFhvNMjLaB', 'request_timestamp': 1748871366, 'response_timestamp': 1748871367, 'response_data': {'status': 'success'}, 'request_data': {'brightness': 50}, 'status': 'success', 'device_status': 0, 'expiration_timestamp': 1748871426, 'cmd': 4096}]
   ```

3. **Check status and response data**:
   - `status`: Overall status of the command
   - `response_data`: Specific response from the node
   - `device_status`: Numeric status code from the device

## Response Structure

The command response includes:

- `node_id`: ID of the node that responded
- `request_id`: ID of the original request
- `request_timestamp`: Time when the request was sent
- `response_timestamp`: Time when the response was received
- `request_data`: Original command data
- `response_data`: Response data from the node
- `status`: Status of the command (success, failure, etc.)
- `device_status`: Numeric status code from the device
- `expiration_timestamp`: Time when the request will expire
- `cmd`: Original command ID

## Examples of Common Use Cases

### Sending a Custom Command to a Light

```bash
# Set brightness to 75%
esp-rainmaker-cli create_cmd_request abcd1234 4096 '{"brightness":75}'

# Get the response
esp-rainmaker-cli get_cmd_requests <request_id_from_above>
```

### Sending Commands to Multiple Nodes

```bash
# Turn off multiple lights
esp-rainmaker-cli create_cmd_request abcd1234,efgh5678 2048 '{"power":false}'

# Get responses for a specific node
esp-rainmaker-cli get_cmd_requests <request_id_from_above> --node_id abcd1234
```

### Setting a Longer Timeout

```bash
# Command with 2-minute timeout for operations that take longer
esp-rainmaker-cli create_cmd_request abcd1234 8192 '{"update_config":true}' --timeout 120
```

## Best Practices

1. **Use appropriate timeouts**: Set timeouts based on expected operation time
2. **Check responses promptly**: Commands might complete before the timeout expires
3. **Handle errors gracefully**: Check status codes and response data for errors
4. **Unique command IDs**: Use unique command IDs for different operations
5. **Limit batch size**: Keep the number of nodes in a single request reasonable (max 25)

## Notes

- This feature is currently in Beta
- Command IDs and data formats are specific to your device implementation
- The maximum timeout value is application-dependent
- Response data may vary based on the device's implementation 