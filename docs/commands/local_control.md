# ESP RainMaker Local Control

ESP RainMaker Local Control provides fast, direct communication with ESP RainMaker devices on the local network, bypassing cloud servers for improved performance and reduced latency.

## Overview

ESP RainMaker Local Control uses the ESP Local Control protocol to communicate directly with ESP RainMaker devices over HTTP transport. This provides:

- **Fast response times**: As the commands need not go via cloud
- **Offline operation**: Works without internet connectivity
- **Reduced bandwidth**: No cloud communication required
- **Enhanced privacy**: Data stays on local network

## Security

ESP Local Control supports three security schemes:

- **Security 0**: No encryption (not recommended for production)
- **Security 1**: X25519 key exchange + AES-CTR encryption with Proof of Possession (PoP)
- **Security 2**: SRP6a + AES-GCM encryption + authentication

Most ESP RainMaker devices use Security 1 with a PoP (Proof of Possession) value.

## Command Usage

All ESP RainMaker CLI commands that support `--local` flag:

### Common Options

```bash
--local                 # Enable local control mode
--pop <value>          # Proof of Possession for security v1
--transport <type>     # Transport: http/https/ble (default: http)
--port <number>        # Port number (default: 8080)
--sec_ver <version>    # Security version: 0/1/2 (default: 1)
```

### Get Node Configuration

```bash
# Get device configuration via local control
esp-rainmaker-cli getnodeconfig <node_id> --local --pop <pop_value>

# With custom transport and port
esp-rainmaker-cli getnodeconfig <node_id> --local --pop <pop_value> --transport https --port 8443

# Example
esp-rainmaker-cli getnodeconfig N7FXSyMjeYFhWcRyDig7t3 --local --pop 2c4d470d
```

### Get Parameters

```bash
# Get current device parameters
esp-rainmaker-cli getparams <node_id> --local --pop <pop_value>

# Example
esp-rainmaker-cli getparams N7FXSyMjeYFhWcRyDig7t3 --local --pop 2c4d470d
```

### Set Parameters

```bash
# Set device parameters
esp-rainmaker-cli setparams <node_id> <params_json> --local --pop <pop_value>

# Example - Turn on light with 75% brightness
esp-rainmaker-cli setparams N7FXSyMjeYFhWcRyDig7t3 \
  '{"Light": {"Power": true, "Brightness": 75}}' \
  --local --pop 2c4d470d
```

## Finding Device Information

### Node ID
The Node ID is displayed in the ESP RainMaker mobile app or can be found using:
```bash
esp-rainmaker-cli getnodes
```

### Proof of Possession (PoP)
The PoP value can be found:
1. On the device's QR code or label (for provisioning)
2. In the device configuration via cloud (for local control)
   ```bash
   esp-rainmaker-cli getparams <node_id>
   ```
   Look for `"Local Control"` service with `"POP"` parameter.

### Device IP Address
By default, the CLI uses mDNS resolution (`<node_id>.local`). You can also specify direct IP:
```bash
esp-rainmaker-cli getnodeconfig 192.168.1.100:8080 --local --pop <pop_value>
```

## Library Usage

For integration with other Python applications (like esp-rainmaker-mcp):

### Synchronous Interface

```python
from rmaker_tools.rmaker_local_ctrl.integration import run_local_control_sync

# Get configuration
config = run_local_control_sync(
    nodeid="N7FXSyMjeYFhWcRyDig7t3",
    operation="get_config",
    pop="2c4d470d",
    transport="http",
    port=8080,
    sec_ver=1
)

# Get parameters
params = run_local_control_sync(
    nodeid="N7FXSyMjeYFhWcRyDig7t3",
    operation="get_params",
    pop="2c4d470d"
)

# Set parameters
success = run_local_control_sync(
    nodeid="N7FXSyMjeYFhWcRyDig7t3",
    operation="set_params",
    data={"Light": {"Power": True, "Brightness": 50}},
    pop="2c4d470d"
)
```

### Asynchronous Interface

```python
import asyncio
from rmaker_tools.rmaker_local_ctrl import (
    get_rainmaker_config, get_rainmaker_params, set_rainmaker_params,
    get_security, get_transport, establish_session
)

async def control_device():
    # Setup transport and security
    transport = await get_transport("http", "N7FXSyMjeYFhWcRyDig7t3.local:8080")
    security = get_security(1, 0, "", "", "2c4d470d", False)

    # Establish session
    if not await establish_session(transport, security):
        return None

    # Get configuration
    config = await get_rainmaker_config(transport, security)

    # Get parameters
    params = await get_rainmaker_params(transport, security)

    # Set parameters
    success = await set_rainmaker_params(
        transport, security,
        {"Light": {"Power": True}}
    )

    return config, params, success

# Run async function
config, params, success = asyncio.run(control_device())
```

## Troubleshooting

### Connection Issues

1. **Device not found**: Ensure device is on same network and Node ID is correct
2. **Authentication failed**: Verify PoP value is correct
3. **Timeout**: Check if device is powered on and network is stable

### Security Issues

1. **Invalid PoP**: Get correct PoP from device label or cloud configuration
2. **Security mismatch**: Verify device security version with `--sec_ver` option

### Network Issues

1. **mDNS resolution**: Try direct IP address instead of `<node_id>.local`
2. **Port conflicts**: Check if port 8080 is available or use custom port
3. **Network connectivity**: Ensure both the CLI and device are on the same local network

### Debug Mode

Enable verbose logging for troubleshooting:
```python
# In library usage, pass verbose=True
security = get_security(1, 0, "", "", "2c4d470d", verbose=True)
```

## Protocol Details

ESP RainMaker Local Control is built on the ESP Local Control protocol, which uses Protocol Buffers (protobuf) for efficient binary data serialization. The protocol provides a secure, property-based communication mechanism for controlling ESP devices.

### Key Components

- **Session establishment**: A security handshake is performed when establishing a connection, using the configured security scheme (0, 1, or 2) to authenticate and encrypt the session
- **Property-based communication**: Instead of traditional request/response patterns, the protocol uses properties that can be read and written. ESP RainMaker implements two main properties:
  - `config`: Device configuration (read-only) - contains device capabilities, services, and metadata
  - `params`: Device parameters (read/write) - contains the current state and settings of devices and services
- **Encrypted data transfer**: All data is encrypted using the chosen security scheme (Security 1 uses X25519 + AES-CTR, Security 2 uses SRP6a + AES-GCM)

## Raw Local Control Mode (--local-raw)

In addition to the standard `--local` mode (ESP Local Control), the CLI also supports `--local-raw` mode which uses raw provisioning endpoints. This provides an alternative communication path that is particularly useful during device provisioning.

### Comparison: --local vs --local-raw

| Feature | --local (ESP Local Control) | --local-raw (Raw Provisioning) |
|---------|---------------------------|-------------------------------|
| **Protocol** | ESP Local Control (property-based) | Raw protocomm endpoints |
| **Transport** | HTTP/HTTPS only | HTTP and BLE |
| **Availability** | After provisioning complete | During and after provisioning |
| **Endpoints** | `config`, `params` properties | `get_params`, `set_params`, `get_config` |
| **Data Size** | Limited by HTTP response | Chunked transfer (200 bytes) for large data |
| **Signed Response** | Not supported | Supported (with --timestamp) |
| **Proxy Reporting** | Not supported | Supported (--proxy-report) |

### When to Use --local-raw

Use `--local-raw` when:
- **During provisioning**: When you need to get/set parameters before provisioning is complete
- **Over BLE**: When HTTP transport is not available
- **Signed responses needed**: When you need cryptographically signed data for cloud verification
- **Proxy reporting**: When you need to report device state to cloud via proxy API
- **Large configurations**: When node config exceeds typical HTTP response limits (uses chunked transfer)

### Raw Endpoints

The `--local-raw` mode uses these provisioning endpoints:

| Endpoint | Purpose | Protobuf |
|----------|---------|----------|
| `get_params` | Read device parameters | JSON (with optional signing) |
| `set_params` | Write device parameters | JSON |
| `get_config` | Read node configuration | Protobuf chunked (200 bytes) |

### Usage Examples

#### Over HTTP

```bash
# Get parameters
esp-rainmaker-cli getparams <nodeid> --local-raw --pop <pop_value>

# Set parameters
esp-rainmaker-cli setparams <nodeid> --data '{"Light": {"Power": true}}' --local-raw --pop <pop_value>

# Get node configuration
esp-rainmaker-cli getnodeconfig <nodeid> --local-raw --pop <pop_value>
```

#### Over BLE (During Provisioning)

```bash
# Get parameters over BLE
esp-rainmaker-cli getparams <nodeid> --local-raw --transport ble --device_name PROV_aaf824 --pop <pop_value>

# Set parameters over BLE
esp-rainmaker-cli setparams <nodeid> --data '{"Light": {"Power": true}}' --local-raw --transport ble --device_name PROV_aaf824 --pop <pop_value>

# Get node configuration over BLE
esp-rainmaker-cli getnodeconfig <nodeid> --local-raw --transport ble --device_name PROV_aaf824 --pop <pop_value>
```

#### With Signed Response

```bash
# Get signed parameters (for verification)
esp-rainmaker-cli getparams <nodeid> --local-raw --pop <pop_value> --timestamp 1737100800

# Get signed node configuration
esp-rainmaker-cli getnodeconfig <nodeid> --local-raw --pop <pop_value> --timestamp 1737100800
```

#### With Proxy Reporting

```bash
# Report parameters to cloud proxy API
esp-rainmaker-cli getparams <nodeid> --local-raw --pop <pop_value> --proxy-report

# Report initial parameters to cloud (initparams API)
esp-rainmaker-cli getparams <nodeid> --local-raw --pop <pop_value> --proxy-report --init

# Report node configuration to cloud proxy API
esp-rainmaker-cli getnodeconfig <nodeid> --local-raw --pop <pop_value> --proxy-report
```

### Proxy Reporting

The `--proxy-report` flag enables automatic reporting of signed device data to the RainMaker cloud. This is useful for scenarios where:

1. **User-node association**: During provisioning, report device state for cloud to associate with user
2. **Offline sync**: After reconnecting, sync device state to cloud
3. **Audit trail**: Create a verified record of device state

**Proxy API Endpoints:**

| Command | API Endpoint |
|---------|--------------|
| `getparams --proxy-report` | `/user/nodes/{node_id}/proxy/params` |
| `getparams --proxy-report --init` | `/user/nodes/{node_id}/proxy/initparams` |
| `getnodeconfig --proxy-report` | `/user/nodes/{node_id}/proxy/config` |

**Signed Response Format:**

```json
{
    "node_payload": {
        "data": { ... },
        "timestamp": 1737100800
    },
    "signature": "base64_encoded_ecdsa_signature"
}
```

The signature is generated using the device's private key and can be verified by the cloud using the device's public key (obtained during claiming).

## Best Practices

1. **Use Security 1 or 2** with proper PoP for production devices
2. **Cache PoP values** to avoid repeated lookups
3. **Handle timeouts** gracefully with retry logic
5. **Implement connection pooling** for multiple operations
6. **Validate responses** before processing data
7. **Use async interface** for better performance in applications

## Examples

See the [node_management.md](node_management.md) and [parameters.md](parameters.md) documentation for more specific command examples and use cases.
