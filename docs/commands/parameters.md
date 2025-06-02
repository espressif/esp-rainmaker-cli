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