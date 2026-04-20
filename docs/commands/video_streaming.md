# Video Streaming

## Overview

The `stream` command lets you view a live video feed from an ESP RainMaker camera device using WebRTC. Signaling is handled through AWS Kinesis Video Streams (KVS), the same mechanism used by the ESP RainMaker phone app.

The CLI acts as a WebRTC **viewer** — it connects to the KVS signaling channel advertised by the device, negotiates a peer connection, and renders the incoming video track.

## Prerequisites

Install the optional video streaming dependencies:

```bash
pip install aiortc opencv-python numpy
```

- `aiortc` — WebRTC peer connection and media handling
- `opencv-python` — Video display window (optional if using `--stats-only`)
- `numpy` — Required by opencv

The base dependencies `boto3` and `websockets` are installed automatically with the CLI.

## Command Syntax

```bash
esp-rainmaker-cli stream <nodeid> [options]
```

### Required Arguments

- `<nodeid>` — Node ID of the camera device.

### Optional Arguments

| Flag | Description |
|------|-------------|
| `--output`, `-o` `<path>` | Save video to an MP4 file |
| `--region` `<region>` | Override the AWS region for KVS |
| `--duration` `<seconds>` | Stop the stream after N seconds |
| `--stats-only` | Print RTP statistics (FPS, bitrate, packet loss) without opening a video window |
| `--profile` `<name>` | Use a specific CLI profile |

## Examples

### Basic video stream

```bash
esp-rainmaker-cli stream ABC123node
```

Opens a video window showing the live feed. Press **q** or **Esc** to close.

### Save to file

```bash
esp-rainmaker-cli stream ABC123node --output recording.mp4
```

### Monitor statistics without video

```bash
esp-rainmaker-cli stream ABC123node --stats-only
```

Prints periodic stats (FPS, bitrate, resolution, packet loss) to the terminal. Useful for headless environments or bandwidth testing.

### Timed recording

```bash
esp-rainmaker-cli stream ABC123node --output clip.mp4 --duration 30
```

Records 30 seconds of video and exits automatically.

### Using a different profile

```bash
esp-rainmaker-cli stream ABC123node --profile staging
```

## How It Works

1. The CLI fetches the device's node parameters to find the KVS channel name.
2. Temporary AWS credentials are obtained via the RainMaker `assume_role` API.
3. A SigV4-signed WebSocket connection is opened to the KVS signaling channel.
4. The CLI creates a WebRTC offer, sends it through the signaling channel, and receives the device's answer.
5. ICE candidates are exchanged (trickle ICE) to establish a direct media path.
6. The incoming video track is rendered via OpenCV and/or saved to file.

## Troubleshooting

### "Channel parameter not found"

The device does not advertise a KVS channel in its parameters. Ensure the firmware has video streaming enabled and the device is online.

### No video window appears

- Verify `opencv-python` is installed: `python -c "import cv2; print(cv2.__version__)"`
- On headless systems, use `--stats-only` or `--output` instead.

### Connection timeout / ICE failure

- Ensure the device is online and streaming.
- Check that your network allows outbound UDP traffic (STUN/TURN ports).
- Try `--region` if the default region does not match the device's KVS channel region.

### Debug logging

Use the `--debug` flag for detailed connection logs:

```bash
esp-rainmaker-cli stream ABC123node --debug
```
