# Parameter Management Documentation

ESP RainMaker allows you to get and set parameters for your nodes. Parameters represent the state and settings of devices connected to the node.

## Overview

Parameters in ESP RainMaker are organized hierarchically:
- Each node can have multiple devices and services
- Each device/service has parameters (e.g., power, brightness, temperature)
- Parameters have types (e.g., boolean, integer, string) and values

## Commands

### Getting Parameters

To retrieve the current parameters of a node:

```bash
esp-rainmaker-cli getparams <nodeid>
```

Example:
```bash
esp-rainmaker-cli getparams abcd1234
```

This returns a JSON object containing all parameters for all devices and services on the node.

#### Local Control Mode

For faster parameter retrieval, you can get parameters directly from the device on your local network:

```bash
esp-rainmaker-cli getparams <nodeid> --local --pop <pop_value>
```

Local control options:
- `--local`: Enable local control mode (5-10x faster than cloud)
- `--pop <value>`: Proof of Possession for device authentication
- `--transport <type>`: Transport protocol (http/https/ble, default: http)
- `--port <number>`: Port number (default: 8080)
- `--sec_ver <version>`: Security version (0/1/2, default: 1)

Example:
```bash
esp-rainmaker-cli getparams N7FXSyMjeYFhWcRyDig7t3 --local --pop 2c4d470d
```

**Performance comparison:**
- Cloud API: 500-2000ms response time
- Local Control: 50-200ms response time (5-10x faster)

### Setting Parameters

There are two ways to set parameters:

#### Using JSON Data Directly

```bash
esp-rainmaker-cli setparams <nodeid> --data '<json_data>'
```

Example:
```bash
esp-rainmaker-cli setparams abcd1234 --data '{"Light": {"Power": true, "Brightness": 75}}'
```

**Important**: The JSON data must be enclosed in single quotes to prevent shell interpretation.

#### Using a JSON File

```bash
esp-rainmaker-cli setparams <nodeid> --filepath <path_to_json_file>
```

Example:
```bash
esp-rainmaker-cli setparams abcd1234 --filepath ./light_params.json
```

Where `light_params.json` might contain:
```json
{
    "Light": {
        "Power": true,
        "Brightness": 75
    }
}
```

#### Local Control Mode for Setting Parameters

For faster parameter setting, you can set parameters directly on the device via local network:

```bash
esp-rainmaker-cli setparams <nodeid> --data '<json_data>' --local --pop <pop_value>
```

Example:
```bash
esp-rainmaker-cli setparams N7FXSyMjeYFhWcRyDig7t3 --data '{"Light": {"Power": true, "Brightness": 75}}' --local --pop 2c4d470d
```

Local control options for setparams:
- `--local`: Enable local control mode (8-10x faster than cloud)
- `--pop <value>`: Proof of Possession for device authentication
- `--transport <type>`: Transport protocol (http/https/ble, default: http)
- `--port <number>`: Port number (default: 8080)
- `--sec_ver <version>`: Security version (0/1/2, default: 1)

**Performance comparison for setparams:**
- Cloud API: 800-3000ms response time
- Local Control: 100-300ms response time (8-10x faster)

## Parameter Structure

The parameter JSON structure follows this format:

```json
{
    "DeviceName1": {
        "Parameter1": value1,
        "Parameter2": value2
    },
    "DeviceName2": {
        "Parameter1": value1
    },
    "ServiceName1": {
        "Parameter1": value1
    }
}
```

## Common Parameter Types and Examples

### Boolean Parameters

```json
{
    "Light": {
        "Power": true
    }
}
```

### Numeric Parameters

```json
{
    "Light": {
        "Brightness": 75,
        "Color Temperature": 5000
    }
}
```

### String Parameters

```json
{
    "Speaker": {
        "Name": "Living Room Speaker",
        "Mode": "Normal"
    }
}
```

### Multiple Devices

```json
{
    "Light": {
        "Power": true,
        "Brightness": 80
    },
    "Fan": {
        "Power": true,
        "Speed": 3
    }
}
```

## Getting Device and Parameter Information

To know what parameters a node supports, you can use the `getnodedetails` command:

```bash
esp-rainmaker-cli getnodedetails --nodeid <nodeid>
```

This will show the node's configuration, including all devices, services, and their parameters.

## Working with Special Parameter Types

### RGB Color Parameters

```json
{
    "Light": {
        "RGB": {
            "r": 255,
            "g": 0,
            "b": 0
        }
    }
}
```

### Time Parameters

```json
{
    "Timer": {
        "Time": "10:30"
    }
}
```

## Error Handling

If the parameter setting fails, the CLI will return an error message. Common errors include:
- Invalid JSON format
- Parameter not found
- Value type mismatch
- Node offline

## Best Practices

1. **Check Node Status**: Ensure the node is online before setting parameters
2. **Verify Configuration**: Use `getnodedetails` to verify parameter names and types
3. **Use Proper JSON Format**: Ensure your JSON is valid and properly formatted
4. **Handle Errors**: Check for error messages and handle them appropriately
5. **Test Changes**: Verify parameter changes took effect using `getparams`

## Examples of Common Use Cases

### Controlling a Light

```bash
# Turn on a light
esp-rainmaker-cli setparams abcd1234 --data '{"Light": {"Power": true}}'

# Set brightness to 50%
esp-rainmaker-cli setparams abcd1234 --data '{"Light": {"Brightness": 50}}'

# Turn on and set brightness in one command
esp-rainmaker-cli setparams abcd1234 --data '{"Light": {"Power": true, "Brightness": 50}}'
```

### Controlling a Thermostat

```bash
# Set temperature to 72°F
esp-rainmaker-cli setparams abcd1234 --data '{"Thermostat": {"Temperature": 72}}'

# Change mode to "Cooling"
esp-rainmaker-cli setparams abcd1234 --data '{"Thermostat": {"Mode": "Cooling"}}'
```

### Controlling Multiple Devices

```bash
# Control multiple devices at once
esp-rainmaker-cli setparams abcd1234 --data '{"Light": {"Power": true}, "Fan": {"Power": true, "Speed": 2}}'
```

## Local Control Examples

### Fast Device Control

```bash
# Quickly turn on a light (local control)
esp-rainmaker-cli setparams N7FXSyMjeYFhWcRyDig7t3 --data '{"Light": {"Power": true}}' --local --pop 2c4d470d

# Set multiple parameters with local control
esp-rainmaker-cli setparams N7FXSyMjeYFhWcRyDig7t3 --data '{"Light": {"Power": true, "Brightness": 80, "Hue": 120}}' --local --pop 2c4d470d

# Get current state quickly
esp-rainmaker-cli getparams N7FXSyMjeYFhWcRyDig7t3 --local --pop 2c4d470d
```

## Raw Local Control Mode (--local-raw)

The `--local-raw` mode provides an alternative local control mechanism that uses raw provisioning endpoints instead of ESP Local Control. This is particularly useful during provisioning when esp_local_ctrl may not be available.

### Key Differences from --local Mode

| Feature | --local (esp_local_ctrl) | --local-raw (provisioning endpoints) |
|---------|--------------------------|--------------------------------------|
| Protocol | ESP Local Control (property-based) | Raw protocomm endpoints |
| Transport | HTTP/HTTPS | HTTP/BLE |
| Availability | After provisioning | During and after provisioning |
| Endpoints | `config`, `params` properties | `get_params`, `set_params` endpoints |
| Signed Response | Not supported | Supported (with --timestamp) |

### Getting Parameters with --local-raw

```bash
# Basic usage over HTTP
esp-rainmaker-cli getparams <nodeid> --local-raw --pop <pop_value>

# Over BLE (requires device name)
esp-rainmaker-cli getparams <nodeid> --local-raw --transport ble --device_name PROV_aabbcc --pop <pop_value>

# With timestamp for signed response
esp-rainmaker-cli getparams <nodeid> --local-raw --pop <pop_value> --timestamp 1737100800
```

**Options for --local-raw:**
- `--local-raw`: Enable raw local control mode
- `--pop <value>`: Proof of Possession for device authentication
- `--transport <type>`: Transport protocol (http/ble, default: http)
- `--device_name <name>`: BLE device name (required for BLE transport, e.g., PROV_aabbcc)
- `--timestamp <value>`: Unix timestamp for signed response
- `--sec_ver <version>`: Security version (0/1/2, default: 1)

### Setting Parameters with --local-raw

```bash
# Basic usage over HTTP
esp-rainmaker-cli setparams <nodeid> --data '{"Light": {"Power": true}}' --local-raw --pop <pop_value>

# Over BLE during provisioning
esp-rainmaker-cli setparams <nodeid> --data '{"Light": {"Power": true}}' --local-raw --transport ble --device_name PROV_aabbcc --pop <pop_value>
```

### BLE Transport Examples

When using BLE transport, the `--device_name` parameter is required:

```bash
# Get parameters over BLE
esp-rainmaker-cli getparams N7FXSyMjeYFhWcRyDig7t3 --local-raw --transport ble --device_name PROV_aaf824 --pop 2c4d470d

# Set parameters over BLE
esp-rainmaker-cli setparams N7FXSyMjeYFhWcRyDig7t3 --data '{"Light": {"Power": true}}' --local-raw --transport ble --device_name PROV_aaf824 --pop 2c4d470d
```

The device name is typically in the format `PROV_XXXXXX` where XXXXXX are the last 6 characters of the device's MAC address.

## Proxy Reporting Mode (--proxy-report)

The `--proxy-report` mode automatically retrieves signed parameters from the device and reports them to the RainMaker cloud proxy API. This is useful for scenarios where the cloud needs to receive device state updates directly from local communication.

### How It Works

1. Automatically uses the current Unix timestamp
2. Retrieves parameters from the device with signed response
3. POSTs the signed payload to the RainMaker cloud proxy API
4. The cloud verifies the signature and processes the parameters

### Usage

```bash
# Report current params to cloud via proxy API
esp-rainmaker-cli getparams <nodeid> --local-raw --pop <pop_value> --proxy-report

# Report initial params to cloud (uses initparams API)
esp-rainmaker-cli getparams <nodeid> --local-raw --pop <pop_value> --proxy-report --init
```

**Options for --proxy-report:**
- `--proxy-report`: Enable proxy reporting mode
- `--init`: Use `initparams` API endpoint instead of `params` (for initial parameter reporting)

### Proxy API Endpoints

| Command | Default API Path | With --init |
|---------|------------------|-------------|
| `getparams --proxy-report` | `/user/nodes/{node_id}/proxy/params` | `/user/nodes/{node_id}/proxy/initparams` |

### Example Workflow

```bash
# During provisioning, report initial device state to cloud
esp-rainmaker-cli getparams N7FXSyMjeYFhWcRyDig7t3 --local-raw --transport ble --device_name PROV_aaf824 --pop 2c4d470d --proxy-report --init

# After provisioning, report current state to cloud
esp-rainmaker-cli getparams N7FXSyMjeYFhWcRyDig7t3 --local-raw --pop 2c4d470d --proxy-report
```

### Response Format

When using `--proxy-report`, the signed response from the device looks like:

```json
{
    "node_payload": {
        "data": {
            "Light": {
                "Power": true,
                "Brightness": 75
            }
        },
        "timestamp": 1737100800
    },
    "signature": "base64_encoded_signature..."
}
```

The cloud proxy API response:

```json
{
    "status": "success",
    "description": "Node params request queued successfully"
}
```

### Finding Device PoP Value

To use local control, you need the device's Proof of Possession (PoP) value:

```bash
# Get PoP from cloud (one-time lookup)
esp-rainmaker-cli getparams <nodeid>
# Look for "Local Control" service with "POP" parameter
```

Or check the device's physical label/QR code for the PoP value.

### Local Control Benefits

- **Speed**: 5-10x faster response times
- **Reliability**: Works even when internet is down
- **Privacy**: No data sent to cloud servers
- **Responsiveness**: Real-time device control for better user experience

For more details on ESP Local Control, see the [Local Control Guide](local_control.md).