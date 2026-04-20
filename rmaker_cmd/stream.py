# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
from rmaker_lib import node
from rmaker_lib.logger import log
from rmaker_lib.profile_utils import get_session_with_profile


def extract_channel_parameter(node_details):
    """
    Extract channel parameter from node details.

    :param node_details: Node details dictionary
    :type node_details: dict

    :return: Channel name/ARN or None
    :rtype: str | None
    """
    try:
        # Try to get from params
        params = node_details.get('params', {})

        # Look for channel parameter in device params
        # Channel parameter is typically in camera device params
        for device_name, device_params in params.items():
            if isinstance(device_params, dict):
                # Check common channel parameter names
                channel_names = ['Channel', 'channel', 'channel_name', 'ChannelName',
                               'kvs_channel', 'KVSChannel', 'channel_arn', 'ChannelARN']

                for channel_key in channel_names:
                    if channel_key in device_params:
                        channel_value = device_params[channel_key]
                        if channel_value:
                            log.info(f"Found channel parameter '{channel_key}': {channel_value}")
                            return channel_value

        # Try to get from config
        config = node_details.get('config', {})
        devices = config.get('devices', [])

        for device in devices:
            device_name = device.get('name', '')
            device_params = device.get('params', [])

            # Look for channel parameter in device config
            for param_config in device_params:
                param_name = param_config.get('name', '')

                # Check if this is a channel parameter
                if 'channel' in param_name.lower():
                    # Get the actual value from params
                    if device_name in params:
                        device_param_values = params[device_name]
                        if isinstance(device_param_values, dict) and param_name in device_param_values:
                            channel_value = device_param_values[param_name]
                            if channel_value:
                                log.info(f"Found channel parameter from config: {channel_value}")
                                return channel_value

        log.warning("Channel parameter not found in node details")
        return None

    except Exception as e:
        log.error(f"Error extracting channel parameter: {e}")
        return None


def _stream_via_kvs(vars, node_id, save_path, duration, stats_only, region_override):
    """Stream video using KVS cloud signaling."""
    from rmaker_lib.aws_credentials import get_video_streaming_credentials
    from rmaker_lib.kvs_streaming import start_kvs_streaming

    s = get_session_with_profile(vars or {})

    # Get node details to extract channel parameter
    log.info(f"Fetching node details for {node_id}...")
    node_obj = node.Node(node_id, s)
    node_params = node_obj.get_node_params()
    node_config = node_obj.get_node_config()

    node_details = {
        'params': node_params,
        'config': node_config
    }

    channel_name = extract_channel_parameter(node_details)
    if not channel_name:
        print("Error: Channel parameter not found in device configuration.")
        print("Please ensure the device is a camera device with video streaming enabled.")
        return

    log.info(f"Channel parameter: {channel_name}")

    # Get AWS credentials
    log.info("Requesting AWS credentials for video streaming...")
    aws_creds = get_video_streaming_credentials(s, node_id, channel_name)

    if region_override:
        aws_creds.region = region_override

    channel_arn = channel_name

    print(f"\nStarting video stream from node {node_id} (KVS cloud signaling)...")
    print(f"Channel: {channel_arn}")
    if save_path:
        print(f"Saving video to: {save_path}")
    if stats_only:
        print("Statistics mode enabled")
    print()

    show_video_param = False if stats_only else None

    asyncio.run(start_kvs_streaming(
        credentials=aws_creds,
        channel_arn=channel_arn,
        show_video=show_video_param,
        save_path=save_path,
        duration=duration,
        stats_only=stats_only
    ))

    # Post-stream summary for saved video
    if save_path:
        import os
        if os.path.isfile(save_path) and os.path.getsize(save_path) > 0:
            size_mb = os.path.getsize(save_path) / (1024 * 1024)
            print(f"Video saved: {save_path} ({size_mb:.1f} MB)")
        else:
            print(f"Warning: Video file was not saved. No frames were received or recording failed.")


def stream_video(vars=None):
    """
    Stream video from a camera device using WebRTC via KVS cloud signaling.

    :param vars: Parameters dict from argparse
    :type vars: dict | None
    """
    if not vars or 'nodeid' not in vars:
        print("Error: Node ID is required.")
        print("Usage: esp-rainmaker-cli stream <nodeid> [options]")
        return

    node_id = vars['nodeid']
    save_path = vars.get('output') or vars.get('save')
    region_override = vars.get('region')
    duration = vars.get('duration')
    stats_only = vars.get('stats_only', False)

    # Validate duration
    if duration is not None:
        if duration <= 0:
            print(f"Error: Duration must be a positive number of seconds, got: {duration}")
            return

    # Validate output path
    if save_path:
        import os
        valid_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.webm')
        _, ext = os.path.splitext(save_path)
        if not ext:
            print(f"Error: Output path must be a file with a video extension {valid_extensions}, got: {save_path}")
            return
        if ext.lower() not in valid_extensions:
            print(f"Error: Unsupported video format '{ext}'. Supported formats: {', '.join(valid_extensions)}")
            return
        # Check that the parent directory exists
        parent_dir = os.path.dirname(save_path)
        if parent_dir and not os.path.isdir(parent_dir):
            print(f"Error: Output directory does not exist: {parent_dir}")
            return

    try:
        _stream_via_kvs(vars, node_id, save_path, duration, stats_only, region_override)
    except KeyboardInterrupt:
        print("\nStream interrupted by user")
    except ImportError as e:
        print(f"\nMissing dependency: {e}")
    except Exception as e:
        error_str = str(e)
        error_name = type(e).__name__

        # User-friendly AWS error messages
        if 'AccessDeniedException' in error_str or 'AccessDenied' in error_str:
            print("\nError: Access denied to AWS KVS service.")
            print("This usually means the streaming credentials have expired or are insufficient.")
            print("Please ensure the device has valid streaming permissions configured.")
        elif 'ResourceNotFoundException' in error_str:
            print("\nError: KVS channel not found.")
            print("Please verify the device has a valid streaming channel configured.")
        elif 'ClientError' in error_name and 'credentials' in error_str.lower():
            print("\nError: Invalid AWS credentials for streaming.")
            print("Please try logging in again or check your device configuration.")
        elif 'socket' in error_str.lower() or 'Connection' in error_name:
            print(f"\nConnection error: {e}")
            print("Please check your network connection and try again.")
        else:
            log.error(f"Streaming error: {e}")
            print(f"\nError: {e}")
        return
