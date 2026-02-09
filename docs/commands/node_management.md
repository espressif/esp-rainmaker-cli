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

#### Local Control Mode

For faster response times, you can get node configuration directly from the device on your local network:

```bash
esp-rainmaker-cli getnodeconfig <nodeid> --local --pop <pop_value>
```

Local control options:
- `--local`: Enable local control mode (5-10x faster than cloud)
- `--pop <value>`: Proof of Possession for device authentication
- `--transport <type>`: Transport protocol (http/https/ble, default: http)
- `--port <number>`: Port number (default: 8080)
- `--sec_ver <version>`: Security version (0/1/2, default: 1)

Example:
```bash
esp-rainmaker-cli getnodeconfig N7FXSyMjeYFhWcRyDig7t3 --local --pop 2c4d470d
```

**Performance comparison:**
- Cloud API: 500-2000ms response time
- Local Control: 50-200ms response time (5-10x faster)

#### Raw Local Control Mode (--local-raw)

The `--local-raw` mode provides an alternative local control mechanism that uses raw provisioning endpoints. This is particularly useful during provisioning over BLE when esp_local_ctrl may not be available.

```bash
# Basic usage over HTTP
esp-rainmaker-cli getnodeconfig <nodeid> --local-raw --pop <pop_value>

# Over BLE (requires device name)
esp-rainmaker-cli getnodeconfig <nodeid> --local-raw --transport ble --device_name PROV_aabbcc --pop <pop_value>

# With timestamp for signed response
esp-rainmaker-cli getnodeconfig <nodeid> --local-raw --pop <pop_value> --timestamp 1737100800
```

**Options for --local-raw:**
- `--local-raw`: Enable raw local control mode
- `--pop <value>`: Proof of Possession for device authentication
- `--transport <type>`: Transport protocol (http/ble, default: http)
- `--device_name <name>`: BLE device name (required for BLE transport, e.g., PROV_aabbcc)
- `--timestamp <value>`: Unix timestamp for signed response
- `--sec_ver <version>`: Security version (0/1/2, default: 1)

**Key differences from --local mode:**

| Feature | --local (esp_local_ctrl) | --local-raw (provisioning endpoints) |
|---------|--------------------------|--------------------------------------|
| Protocol | ESP Local Control | Raw protocomm (get_config endpoint) |
| Transport | HTTP/HTTPS | HTTP/BLE |
| Data Transfer | Single response | 200-byte chunked (for large configs) |
| Signed Response | Not supported | Supported (with --timestamp) |

**Note:** The `--local-raw` mode uses protobuf-based chunked transfer to handle large node configurations that exceed BLE MTU limits. The config is automatically split into 200-byte fragments and reassembled by the CLI.

#### Proxy Reporting Mode (--proxy-report)

The `--proxy-report` mode automatically retrieves signed node configuration from the device and reports it to the RainMaker cloud proxy API.

```bash
# Report node config to cloud via proxy API
esp-rainmaker-cli getnodeconfig <nodeid> --local-raw --pop <pop_value> --proxy-report

# Over BLE during provisioning
esp-rainmaker-cli getnodeconfig <nodeid> --local-raw --transport ble --device_name PROV_aabbcc --pop <pop_value> --proxy-report
```

**How it works:**
1. Automatically uses the current Unix timestamp
2. Retrieves node configuration from the device with signed response
3. POSTs the signed payload to `/user/nodes/{node_id}/proxy/config`
4. The cloud verifies the signature and processes the configuration

**Response format from device:**
```json
{
    "node_payload": {
        "data": {
            "node_id": "N7FXSyMjeYFhWcRyDig7t3",
            "config_version": "2024-01-15",
            "info": { ... },
            "devices": [ ... ],
            "services": [ ... ]
        },
        "timestamp": 1737100800
    },
    "signature": "base64_encoded_signature..."
}
```

**Cloud proxy API response:**
```json
{
    "status": "success",
    "description": "Node config request queued successfully"
}
```

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