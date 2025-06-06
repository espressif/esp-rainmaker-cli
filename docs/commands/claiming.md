# Claiming Documentation

ESP RainMaker requires devices to be claimed before they can be used. This documentation explains the claiming process.

## Overview

Claiming is the process of associating an ESP32 device with your ESP RainMaker account. It involves:
1. Connecting to the device
2. Generating cloud credentials
3. Flashing these credentials to the device

## Claiming Command

```bash
esp-rainmaker-cli claim <port> [options]
```

Where:
- `port` is the serial port where your device is connected

Options:
- `--platform`: Node platform (ESP32, ESP32-S2, ESP32-C3, etc.)
- `--mac`: Node MAC address in the format AABBCC112233
- `--addr`: Flash address where claim data will be written (default: 0x340000)
- `--outdir`: Directory to store claim files
- `--matter`: Use Matter claiming (for Matter-enabled devices)

Example:
```bash
esp-rainmaker-cli claim /dev/ttyUSB0 --platform esp32
```

## Claiming Process in Detail

### Prerequisites

Before claiming:
1. Have an ESP32-based device with ESP RainMaker firmware
2. Know which serial port the device is connected to
3. Have the device in a claimable state (typically after flashing the firmware)

### Steps

1. **Connect the device**: Connect your ESP32 device to your computer via USB

2. **Find the serial port**:
   - On Linux/macOS: 
     ```bash
     ls /dev/tty*
     ```
   - On Windows: Check Device Manager under Ports (COM & LPT)

3. **Claim the device**:
   ```bash
   esp-rainmaker-cli claim /dev/ttyUSB0
   ```
   (Replace with your port name)

4. **During claiming**:
   - The CLI will connect to the device
   - Generate cloud credentials
   - Program the credentials to the device
   - The device will reboot

5. **After claiming**:
   - The device should be listed in your ESP RainMaker account
   - Use `getnodes` to check if the device is listed
   - The device is now ready to be provisioned (see [Provisioning Documentation](./provisioning.md))

## Advanced Claiming Options

### Claiming with Custom Flash Address

If your firmware expects the claim data in a specific flash location:

```bash
esp-rainmaker-cli claim /dev/ttyUSB0 --addr 0x350000
```

### Specifying MAC Address

For some workflows, you may need to specify the MAC address:

```bash
esp-rainmaker-cli claim --mac AABBCC112233
```

### Saving Claim Data

To save the claim data files to a specific location:

```bash
esp-rainmaker-cli claim /dev/ttyUSB0 --outdir ~/my_devices/
```

### Matter Claiming

For Matter-enabled devices:

```bash
esp-rainmaker-cli claim /dev/ttyUSB0 --matter
```

## Troubleshooting

### Claiming Issues

#### Connection Problems

If the CLI cannot connect to the device:
- Check if the correct port is specified
- Ensure the device is connected and powered on
- Try a different USB cable or port
- Check if you need special drivers for your device

#### Flashing Problems

If the claiming process fails during flashing:
- Ensure the device is in bootloader mode (some devices need a button press sequence)
- Try specifying the platform with `--platform`
- Verify the flash address is correct for your firmware

## Best Practices

1. **Update Firmware**: Always use the latest firmware on your devices
2. **Secure PoP Codes**: Keep your Proof of Possession (PoP) codes secure, as they provide access to your devices
3. **Documentation**: Document the claim details of your devices for future reference
4. **Backup Claim Data**: Store the claim data securely as it may be needed for recovery 