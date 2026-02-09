# Provisioning Documentation

ESP RainMaker requires devices to be provisioned before they can connect to the cloud. This documentation explains the provisioning process.

## Overview

Provisioning is the process of configuring a device to connect to your Wi-Fi network and associate it with your ESP RainMaker account. It involves:
1. Establishing a secure connection to the device
2. Exchanging user credentials and device association
3. Sending Wi-Fi credentials to the device
4. Verifying successful Wi-Fi connection

## Prerequisites

Before provisioning:
1. Have the device in provisioning mode
2. Know the device's Proof of Possession (PoP) code (if required by security scheme)

## Provisioning Command

### Basic Syntax
```bash
esp-rainmaker-cli provision [--pop <pop>] [options]
```

### Core Parameters
- `--pop <pop>`: Proof of Possession code for the device (required for Security 1, unless device supports `no_pop` capability, or provided via `--qrcode`)
- `--transport <mode>`: Communication method (softap, ble, console, on-network)
- `--sec_ver <version>`: Security scheme (0, 1, or 2)
- `--qrcode <json>`: QR code payload as JSON string (extracts transport, device_name, and pop)

### Transport Modes

#### BLE (Bluetooth Low Energy) - Recommended
```bash
esp-rainmaker-cli provision --pop abcd1234 --transport ble --device_name PROV_d76c30
```

#### SoftAP (Wi-Fi Access Point)
```bash
esp-rainmaker-cli provision --pop abcd1234 --transport softap
```

#### Console (Serial/UART)
```bash
esp-rainmaker-cli provision --pop abcd1234 --transport console
```

#### On-Network (HTTP via mDNS Discovery)

The on-network transport is used for challenge-response based user-node mapping when the device is already connected to the network. This mode **does not perform Wi-Fi provisioning** - it only maps the device to your account.

This works with:
- **Dedicated Challenge-Response Service**: Devices running the standalone on-network challenge-response service
- **Local Control with Challenge-Response**: Devices with Local Control enabled and `ch_resp` endpoint registered

```bash
# Discover devices via mDNS and select interactively
esp-rainmaker-cli provision --transport on-network --pop abcd1234

# Connect directly using hostname (e.g., for Local Control)
esp-rainmaker-cli provision --transport on-network --pop abcd1234 \
  --device-host <node_id>.local

# Connect directly using IP address
esp-rainmaker-cli provision --transport on-network --pop abcd1234 \
  --device-ip 192.168.1.100

# With custom port and discovery timeout
esp-rainmaker-cli provision --transport on-network --pop abcd1234 \
  --device-host mydevice.local --device-port 8080 --discovery-timeout 10.0
```

**On-Network Specific Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--device-ip` | Direct IP address (bypasses mDNS discovery) | - |
| `--device-host` | Device hostname (e.g., `<node_id>.local`) | - |
| `--device-port` | HTTP port for connection | 80 |
| `--discovery-timeout` | mDNS discovery timeout in seconds | 5.0 |

**Disabling Challenge-Response After Mapping:**

After a successful user-node mapping (via any transport), the CLI can optionally send a disable command to the device to prevent further mapping attempts. This is a security measure to ensure only one user can map the device.

The `--disable-chal-resp` and `--no-disable-chal-resp` flags are available for all transports (on-network, BLE, SoftAP), but have transport-specific default behaviors:

- **On-Network Transport**: By default, challenge-response is disabled (`disable_chal_resp=True`). After successful mapping, the CLI sends a disable command to the device, which:
  - Disables the challenge-response handler (returns "Disabled" status for future attempts)
  - Removes mDNS TXT records related to challenge-response
  - For standalone on-network service: Stops the HTTP server after a short delay

- **BLE/SoftAP Transport**: By default, challenge-response remains enabled (`disable_chal_resp=False`). This allows retrying the complete provisioning workflow (including challenge-response) if Wi-Fi provisioning fails.

To override the default behavior:
```bash
# For on-network: Keep challenge-response enabled after mapping
esp-rainmaker-cli provision --transport on-network --pop abcd1234 --no-disable-chal-resp

# For BLE/SoftAP: Disable challenge-response after successful mapping
esp-rainmaker-cli provision --transport ble --pop abcd1234 --disable-chal-resp
esp-rainmaker-cli provision --transport softap --pop abcd1234 --disable-chal-resp
```

**Discovery Behavior:**

When using on-network transport without `--device-ip` or `--device-host`, the CLI discovers devices via mDNS service `_esp_rmaker_chal_resp._tcp`. This service is used by both:

1. **Standalone Challenge-Response Service**
   - Devices with `CONFIG_ESP_RMAKER_ON_NETWORK_CHAL_RESP_ENABLE` enabled
   - Standalone HTTP server on port 80 (default)

2. **Local Control Challenge-Response**
   - Devices with `CONFIG_ESP_RMAKER_LOCAL_CTRL_CHAL_RESP_ENABLE` enabled
   - Challenge-response via Local Control's `ch_resp` endpoint
   - Uses the same mDNS service type for consistency

Both implementations announce the same `_esp_rmaker_chal_resp._tcp` service with TXT records: `node_id`, `port`, `sec_version`, `pop_required`.

The CLI displays discovered devices with Instance Name, Node ID, IP, Port, Security version, PoP requirement, and service type:

```
Discovered 2 device(s):
------------------------------------------------------------------------------------------------------------------------
#   Instance Name        Node ID                   IP Address       Port   Sec  PoP      Service
------------------------------------------------------------------------------------------------------------------------
1   MyDevice             XeRQn9TDhQDTfhrGgcLesA    192.168.1.100    80     1    Yes      ChalResp
2   XeRQn9TDhQDTfhrGgcLesA    192.168.1.101    8080   1    No       ChalResp
------------------------------------------------------------------------------------------------------------------------

Select device number (or 'q' to quit):
```

Note: Instance name defaults to node_id if not set via `esp_rmaker_local_ctrl_enable_chal_resp(instance_name)` or `config.mdns_instance_name`.

If PoP is required but not provided via `--pop`, the CLI will prompt interactively.

**Prerequisites:**
- Device must be connected to the same network as the CLI host
- Device must have one of:
  - On-network challenge-response service enabled (`CONFIG_ESP_RMAKER_ON_NETWORK_CHAL_RESP_ENABLE`), OR
  - Local Control with challenge-response enabled (`CONFIG_ESP_RMAKER_LOCAL_CTRL_CHAL_RESP_ENABLE`)
- Install `zeroconf` for mDNS discovery: `pip install zeroconf`

## Security Schemes

The CLI supports multiple security schemes. PoP requirements vary by security scheme:

- **Security 0**: PoP not required (no security)
- **Security 1**: PoP required unless device supports `no_pop` capability
- **Security 2**: PoP not required (uses username/password instead)

### Security 0 (No Security)
```bash
# PoP not required for Security 0
esp-rainmaker-cli provision --sec_ver 0
```

### Security 1 (X25519 + AES-CTR + PoP) - Default
```bash
# PoP required unless device supports 'no_pop' capability
esp-rainmaker-cli provision --pop abcd1234 --sec_ver 1

# If device supports 'no_pop', PoP can be omitted
esp-rainmaker-cli provision --sec_ver 1
```

### Security 2 (SRP6a + AES-GCM)
```bash
# PoP not required for Security 2 (uses username/password instead)
esp-rainmaker-cli provision --sec_ver 2 \
  --sec2_username myuser --sec2_password mypass
```

## Complete Examples

### BLE Provisioning with Auto-detection
```bash
# Let the CLI auto-detect security scheme
esp-rainmaker-cli provision --pop abcd1234 \
  --transport ble \
  --device_name PROV_d76c30
```

### BLE Provisioning with Pre-configured Wi-Fi
```bash
# Skip Wi-Fi selection by providing credentials
esp-rainmaker-cli provision --pop abcd1234 \
  --transport ble \
  --device_name PROV_d76c30 \
  --ssid "MyWiFiNetwork" \
  --passphrase "MyWiFiPassword"
```

### SoftAP Provisioning with Security 2
```bash
# Use advanced security with username/password
esp-rainmaker-cli provision --pop abcd1234 \
  --transport softap \
  --sec_ver 2 \
  --sec2_username admin \
  --sec2_password secure123
```

### Provisioning with QR Code Payload
```bash
# Use QR code payload to automatically extract transport, device_name, and pop
esp-rainmaker-cli provision \
  --qrcode '{"ver":"v1","name":"PROV_fc9ea3","pop":"7a9d365e","transport":"ble"}' \
  --ssid "MyWiFiNetwork" \
  --passphrase "MyWiFiPassword"

# QR code values can be overridden by explicit options
esp-rainmaker-cli provision \
  --qrcode '{"ver":"v1","name":"PROV_fc9ea3","pop":"7a9d365e","transport":"ble"}' \
  --transport softap \
  --ssid "MyWiFiNetwork" \
  --passphrase "MyWiFiPassword"
```

### Provisioning Without PoP
```bash
# Security 0 - No PoP required
esp-rainmaker-cli provision --sec_ver 0 --transport ble --device_name PROV_d76c30

# Security 1 - PoP optional if device supports 'no_pop' capability
esp-rainmaker-cli provision --sec_ver 1 --transport ble --device_name PROV_d76c30

# Security 2 - No PoP required (uses username/password)
esp-rainmaker-cli provision --sec_ver 2 \
  --transport ble \
  --device_name PROV_d76c30 \
  --sec2_username myuser \
  --sec2_password mypass
```

### Provisioning with Tags and Metadata

You can attach tags and metadata to a node at mapping time. This works with all transport modes and both mapping flows (traditional and challenge-response). See [Node Tags and Metadata](./node_tags_metadata.md) for details.

```bash
# BLE provisioning with tags and metadata
esp-rainmaker-cli provision --pop abcd1234 \
  --transport ble --device_name PROV_d76c30 \
  --tags "location:mumbai,env:production" \
  --metadata '{"serial_no": "abc123"}'

# On-network mapping with tags
esp-rainmaker-cli provision --transport on-network \
  --device-ip 192.168.1.50 --pop abcd1234 \
  --tags "esp.location:office"
```

### User-Node Mapping Without Wi-Fi Provisioning
```bash
# Perform challenge-response mapping and skip sending Wi-Fi credentials
esp-rainmaker-cli provision --pop abcd1234 \
  --transport ble \
  --device_name PROV_d76c30 \
  --no-wifi
```

Use the `--no-wifi` flag when you only need to associate a device with your account (challenge-response). When this flag is set:
- Wi-Fi scanning and credential exchange steps are skipped.
- You must be logged in because an authenticated session is required to complete the mapping.
- The device must advertise the `challenge-response` capability; the CLI will raise an error if the capability is missing.
- All other provisioning steps (security handshake and user association) continue as usual.

This workflow will be useful for BLE-only cases in future, wherein the nodes will be controlled only over BLE.

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--pop` | Proof of possession (required for Security 1 unless device supports `no_pop`, optional for Security 0/2, can be provided via `--qrcode`) | `--pop abcd1234` |
| `--transport` | Transport mode: softap, ble, console, on-network | `--transport ble` |
| `--sec_ver` | Security version: 0, 1, 2 | `--sec_ver 1` |
| `--sec2_username` | Username for Security 2 | `--sec2_username admin` |
| `--sec2_password` | Password for Security 2 | `--sec2_password pass123` |
| `--device_name` | BLE device name | `--device_name PROV_d76c30` |
| `--ssid` | Wi-Fi network name | `--ssid "MyNetwork"` |
| `--passphrase` | Wi-Fi password | `--passphrase "password"` |
| `--qrcode` | QR code payload as JSON string. Extracts `transport`, `name` (device_name), and `pop` from the JSON. Explicit options override QR code values. | `--qrcode '{"ver":"v1","name":"PROV_fc9ea3","pop":"7a9d365e","transport":"ble"}'` |
| `--no-wifi` | Skips Wi-Fi provisioning and performs only user-node mapping (requires authenticated session and device support for challenge-response) | `--no-wifi` |
| `--device-ip` | Device IP address for on-network transport (bypasses mDNS) | `--device-ip 192.168.1.100` |
| `--device-host` | Device hostname for on-network transport (e.g., `<node_id>.local`) | `--device-host XeRQn9TDhQ.local` |
| `--device-port` | Device HTTP port for on-network transport (default: 80) | `--device-port 8080` |
| `--discovery-timeout` | mDNS discovery timeout in seconds for on-network transport (default: 5.0) | `--discovery-timeout 10.0` |
| `--disable-chal-resp` | Disable challenge-response on device after successful mapping (default: True for on-network, False for BLE/SoftAP) | `--disable-chal-resp` |
| `--no-disable-chal-resp` | Do NOT disable challenge-response after successful mapping (overrides `--disable-chal-resp`) | `--no-disable-chal-resp` |
| `--tags` | Comma-separated tags in `key:value` format to attach during node mapping | `--tags "location:pune,name:espressif"` |
| `--metadata` | Metadata as JSON string to attach during node mapping | `--metadata '{"serial_no": "abc123"}'` |

## Provisioning Process

### Typical Flow
1. **Device Discovery**: CLI searches for the device using the specified transport
2. **Security Handshake**: Establishes encrypted communication using PoP
3. **User Association**: Links device to your ESP RainMaker account
4. **Wi-Fi Scanning**: Device scans for available networks (if SSID not provided)
5. **Wi-Fi Configuration**: Sends network credentials to device
6. **Connection Verification**: Confirms device successfully connects to Wi-Fi

### Expected Output
```
Looking for BLE device: PROV_d76c30
Discovering...
Connecting...
Getting Services...
==== Auto-detected Security Scheme: 1 ====
Establishing session - Successful
Sending user information to node - Successful
Scanning Wi-Fi AP's...
Select the Wi-Fi network from the following list:
S.N. SSID                              BSSID         CHN RSSI AUTH
[ 1] MyWiFiNetwork                     aa:bb:cc:dd   11  -45  WPA2_PSK
[ 2] Join another network
Select AP by number (0 to rescan) : 1
Enter passphrase for MyWiFiNetwork : ********
Sending Wi-Fi credentials to node - Successful
Applying Wi-Fi config to node - Successful
Wi-Fi Provisioning Successful
```

## Troubleshooting

### Device Not Found
**Problem**: BLE device not discovered
**Solutions**:
- Ensure device is in provisioning mode
- Check device name matches exactly (case-sensitive)
- Verify Bluetooth is enabled on your computer

### Security Handshake Failed
**Problem**: Authentication errors during setup
**Solutions**:
- Verify PoP code is correct (if required for Security 1)
- Check if device supports `no_pop` capability (for Security 1)
- Try different security schemes (`--sec_ver 0`, `1`, or `2`)
- For Security 2, verify username and password are correct
- Reset device and restart provisioning

### Wi-Fi Connection Failed
**Problem**: Device cannot connect to Wi-Fi
**Solutions**:
- Check Wi-Fi password is correct
- Ensure device supports your Wi-Fi band (2.4GHz vs 5GHz)
- Verify Wi-Fi network is operational
- Check signal strength (move device closer to router)

### Transport Errors
**Problem**: Communication issues with device
**Solutions**:
- **BLE**: Install `bleak` package: `pip install bleak>=0.20.0`
- **SoftAP**: Connect to device's Wi-Fi hotspot first
- **Console**: Check serial port permissions and cable connection
- **On-Network**: Install `zeroconf` package: `pip install zeroconf>=0.28.0`

### On-Network Discovery Issues
**Problem**: No devices discovered via mDNS
**Solutions**:
- Ensure device has `CONFIG_ESP_RMAKER_ON_NETWORK_CHAL_RESP_ENABLE` enabled
- Verify device and CLI host are on the same network/subnet
- Check if device firewall allows mDNS (UDP port 5353)
- Try using `--device-ip` or `--device-host` to bypass mDNS discovery
- Increase discovery timeout: `--discovery-timeout 15.0`

### On-Network Connection Failed
**Problem**: Cannot connect to device via HTTP
**Solutions**:
- Verify device IP/hostname is correct
- Check if device HTTP server is running (default port 80)
- Use correct port with `--device-port` if non-default
- Ensure no firewall blocking HTTP connections

## QR Code Provisioning

The `--qrcode` option allows you to pass a QR code payload directly, which automatically extracts provisioning parameters:

- **`transport`**: Transport mode (softap, ble, console)
- **`name`**: Device name (maps to `--device_name` for BLE transport)
- **`pop`**: Proof of Possession code

### How It Works

1. **QR Code as Defaults**: Values from the QR code are used as defaults for `transport`, `device_name`, and `pop`
2. **Explicit Override**: Any explicitly provided options (`--transport`, `--device_name`, `--pop`) will override the corresponding QR code values
3. **Priority Order**: Explicit options > QR code values > Defaults

### Example QR Code Format

```json
{
  "ver": "v1",
  "name": "PROV_fc9ea3",
  "pop": "7a9d365e",
  "transport": "ble"
}
```

### Use Cases

- **Quick Provisioning**: Scan QR code and pass it directly without manually extracting values
- **Batch Provisioning**: Use QR codes from multiple devices in scripts
- **Partial Override**: Use QR code for most values but override specific ones (e.g., change transport mode)

## Best Practices

1. **Use BLE Transport**: Most reliable for initial provisioning
2. **Use On-Network Transport**: For devices already connected to Wi-Fi (e.g., pre-provisioned devices)
3. **Auto-detect Security**: Let CLI determine security scheme automatically
4. **Strong Wi-Fi Passwords**: Use WPA2/WPA3 with strong passwords
5. **Stable Environment**: Provision in area with good Wi-Fi signal
6. **Device Reset**: If provisioning fails, reset device and retry
7. **QR Code Option**: Use `--qrcode` for faster provisioning when QR code payload is available
8. **Use Hostname for On-Network**: Use `--device-host <node_id>.local` for predictable addressing

## Backward Compatibility

The CLI maintains backward compatibility with older syntax:
```bash
# Old format (still works)
esp-rainmaker-cli provision abcd1234

# New format (recommended)
esp-rainmaker-cli provision --pop abcd1234
```

Both formats are supported, but `--pop` is recommended for new usage.
