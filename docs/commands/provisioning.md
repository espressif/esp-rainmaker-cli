# Provisioning Documentation

ESP RainMaker requires devices to be provisioned before they can connect to the cloud. This documentation explains the provisioning process.

## Overview

Provisioning is the process of configuring a claimed device to connect to your Wi-Fi network. It involves:
1. Connecting to the device's provisioning mode
2. Sending Wi-Fi credentials to the device

## Prerequisites

Before provisioning:
1. Have a claimed ESP32 device (see [Claiming Documentation](./claiming.md))
2. Know the device's Proof of Possession (PoP) code
3. Have the device in provisioning mode (typically after claiming)

## Provisioning Command

```bash
esp-rainmaker-cli provision <pop>
```

Where:
- `pop` is the Proof of Possession code for the device

Example:
```bash
esp-rainmaker-cli provision abcd1234
```

## Provisioning Process in Detail

### Steps

1. **Enter provisioning mode**: 
   - For most devices, this happens automatically after claiming
   - Some devices require a button press or specific sequence

2. **Get the Proof of Possession (PoP)**:
   - This is displayed during the claiming process
   - Or it may be printed on the device/packaging
   - Or it may be a default value specified in the firmware

3. **Run the provision command**:
   ```bash
   esp-rainmaker-cli provision abcd1234
   ```
   (Replace with your PoP code)

4. **During provisioning**:
   - The CLI will launch a browser or web interface
   - You'll select your Wi-Fi network and enter the password
   - The credentials will be securely transmitted to the device

5. **After provisioning**:
   - The device will connect to your Wi-Fi network
   - It will then connect to the ESP RainMaker cloud
   - The device status should change to "online"

## Troubleshooting

### Device Not in Provisioning Mode

If the device doesn't enter provisioning mode:
- Reset the device and try again
- Check the device's documentation for specific instructions
- Some devices have a button combination to enter provisioning mode

### Wi-Fi Connection Failures

If the device cannot connect to Wi-Fi:
- Ensure your Wi-Fi network is operational
- Check that you entered the correct password
- Some devices only support 2.4GHz networks, not 5GHz
- Verify the device is within range of your Wi-Fi router

### Browser Not Opening

If the provisioning browser interface doesn't open:
- Try manually opening the URL shown in the CLI output
- Check if you have a default browser configured
- Try running the command with administrative privileges

### Provisioning Timeout

If provisioning times out:
- Ensure the device is still in provisioning mode
- Try resetting the device and starting again
- Check if there are any firewall settings blocking connections

## Best Practices

1. **Strong Wi-Fi Passwords**: Use strong passwords for your Wi-Fi network
2. **Secure Network**: Provision devices on a secure Wi-Fi network
3. **Close Proximity**: Keep the device close to your Wi-Fi router during provisioning
4. **Stable Connection**: Ensure your computer has a stable internet connection during provisioning
5. **Device Reset**: If in doubt, reset the device and restart the provisioning process 