# Node Management Documentation

ESP RainMaker allows you to manage your nodes through various commands. Nodes are the physical ESP32 devices connected to the RainMaker cloud.

## Overview

Node management commands allow you to:
- List all nodes associated with your account
- Get detailed information about nodes
- View node configuration and status
- Remove nodes from your account

## Commands

### Listing Nodes

To list all nodes associated with your account:

```bash
esp-rainmaker-cli getnodes
```

This command displays the Node IDs of all devices associated with your account.

### Getting Node Details

To get detailed information about all nodes:

```bash
esp-rainmaker-cli getnodedetails
```

To get detailed information about a specific node:

```bash
esp-rainmaker-cli getnodedetails --nodeid <nodeid>
```

Example:
```bash
esp-rainmaker-cli getnodedetails --nodeid abcd1234
```

If you want the raw JSON output:

```bash
esp-rainmaker-cli getnodedetails --nodeid <nodeid> --raw
```

The node details include:
- Node configuration (devices, services, parameters)
- Node status (online/offline)
- Current parameter values
- Node metadata and attributes

### Getting Node Configuration

To get just the configuration information of a node:

```bash
esp-rainmaker-cli getnodeconfig <nodeid>
```

Example:
```bash
esp-rainmaker-cli getnodeconfig abcd1234
```

This returns the node's configuration in JSON format, including:
- Devices and their attributes
- Services and their attributes
- Node information (name, type, firmware version)

### Getting Node Status

To check if a node is online or offline:

```bash
esp-rainmaker-cli getnodestatus <nodeid>
```

Example:
```bash
esp-rainmaker-cli getnodestatus abcd1234
```

This returns the node's connectivity status in JSON format.

### Removing a Node

To remove a node from your account:

```bash
esp-rainmaker-cli removenode <nodeid>
```

Example:
```bash
esp-rainmaker-cli removenode abcd1234
```

This removes the association between your user account and the node. The node will need to be claimed again before it can be used.

## Understanding Node Information

### Node Structure

A node typically contains:
- **Devices**: Physical or virtual components (e.g., light, switch, sensor)
- **Services**: System services (e.g., OTA, scheduling, time sync)
- **Parameters**: Settings and states for devices and services

### Node States

Nodes can be in one of these states:
- **Online**: The node is connected to the cloud
- **Offline**: The node is not connected to the cloud

For offline nodes, the CLI shows the last time the node was seen online.

## Example Workflows

### Basic Node Discovery and Inspection

1. List all your nodes:
   ```bash
   esp-rainmaker-cli getnodes
   ```

2. Get details for a specific node:
   ```bash
   esp-rainmaker-cli getnodedetails --nodeid abcd1234
   ```

3. Check if the node is online:
   ```bash
   esp-rainmaker-cli getnodestatus abcd1234
   ```

### Device Management

1. Get the node's configuration to understand its devices:
   ```bash
   esp-rainmaker-cli getnodeconfig abcd1234
   ```

2. Get current parameters to see device states:
   ```bash
   esp-rainmaker-cli getparams abcd1234
   ```

3. Set parameters to control devices:
   ```bash
   esp-rainmaker-cli setparams abcd1234 --data '{"Light": {"Power": true}}'
   ```

### Troubleshooting an Offline Node

1. Check node status:
   ```bash
   esp-rainmaker-cli getnodestatus abcd1234
   ```

2. If offline, get node details to see last connection time:
   ```bash
   esp-rainmaker-cli getnodedetails --nodeid abcd1234
   ```

3. Check network connectivity on the physical device
   
4. If needed, remove and reclaim the node:
   ```bash
   esp-rainmaker-cli removenode abcd1234
   # Then follow claiming process again
   ```

## Tips and Best Practices

1. **Regular Checks**: Periodically check node status to ensure devices are online
   
2. **Keep Track of Node IDs**: Store node IDs in a safe place for future reference
   
3. **Remove Unused Nodes**: Clean up your account by removing nodes you no longer use
   
4. **Review Node Details**: Check node details to understand device capabilities
   
5. **JSON Output**: Use the `--raw` flag with getnodedetails for programmatic processing

## Troubleshooting

### Node Not Listed

If a node doesn't appear in the `getnodes` command:
- Ensure the node has been claimed with your account
- Check if the node has been powered on and connected to Wi-Fi
- Verify the node's firmware is correctly configured for RainMaker

### Cannot Remove Node

If you cannot remove a node:
- Ensure you're logged in with the account that owns the node
- Check if the node is shared with other users (remove sharing first)
- Verify you have the correct Node ID 