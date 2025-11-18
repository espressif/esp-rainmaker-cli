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

## Best Practices

1. **Use Security 1 or 2** with proper PoP for production devices
2. **Cache PoP values** to avoid repeated lookups
3. **Handle timeouts** gracefully with retry logic
5. **Implement connection pooling** for multiple operations
6. **Validate responses** before processing data
7. **Use async interface** for better performance in applications

## Examples

See the [node_management.md](node_management.md) and [parameters.md](parameters.md) documentation for more specific command examples and use cases.
