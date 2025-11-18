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
2. Know the device's Proof of Possession (PoP) code

## Provisioning Command

### Basic Syntax
```bash
esp-rainmaker-cli provision --pop <pop> [options]
```

### Core Parameters
- `--pop <pop>`: Proof of Possession code for the device (required)
- `--transport <mode>`: Communication method (softap, ble, console)
- `--sec_ver <version>`: Security scheme (0, 1, or 2)

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

## Security Schemes

The CLI supports multiple security schemes:

### Security 0 (No Security)
```bash
esp-rainmaker-cli provision --pop abcd1234 --sec_ver 0
```

### Security 1 (X25519 + AES-CTR + PoP) - Default
```bash
esp-rainmaker-cli provision --pop abcd1234 --sec_ver 1
```

### Security 2 (SRP6a + AES-GCM)
```bash
esp-rainmaker-cli provision --pop abcd1234 --sec_ver 2 \
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

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--pop` | Proof of possession (required) | `--pop abcd1234` |
| `--transport` | Transport mode: softap, ble, console | `--transport ble` |
| `--sec_ver` | Security version: 0, 1, 2 | `--sec_ver 1` |
| `--sec2_username` | Username for Security 2 | `--sec2_username admin` |
| `--sec2_password` | Password for Security 2 | `--sec2_password pass123` |
| `--device_name` | BLE device name | `--device_name PROV_d76c30` |
| `--ssid` | Wi-Fi network name | `--ssid "MyNetwork"` |
| `--passphrase` | Wi-Fi password | `--passphrase "password"` |

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
- Verify PoP code is correct
- Try different security schemes (`--sec_ver 0`, `1`, or `2`)
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

## Best Practices

1. **Use BLE Transport**: Most reliable for modern devices
2. **Auto-detect Security**: Let CLI determine security scheme automatically
3. **Strong Wi-Fi Passwords**: Use WPA2/WPA3 with strong passwords
4. **Stable Environment**: Provision in area with good Wi-Fi signal
5. **Device Reset**: If provisioning fails, reset device and retry

## Backward Compatibility

The CLI maintains backward compatibility with older syntax:
```bash
# Old format (still works)
esp-rainmaker-cli provision abcd1234

# New format (recommended)
esp-rainmaker-cli provision --pop abcd1234
```

Both formats are supported, but `--pop` is recommended for new usage.