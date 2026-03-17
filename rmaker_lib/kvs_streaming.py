# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
import sys
import time
import re
from datetime import datetime
from typing import Optional, Callable


try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceCandidate, RTCConfiguration, RTCIceServer
    from aiortc.contrib.media import MediaPlayer, MediaRelay
    from aiortc.sdp import candidate_from_sdp
    AIORTC_AVAILABLE = True
    AIORTC_IMPORT_ERROR = None
except ImportError as e:
    AIORTC_AVAILABLE = False
    AIORTC_IMPORT_ERROR = str(e)
    # Provide a stub so class definitions don't crash at import time
    class VideoStreamTrack:
        def __init__(self): pass
        def stop(self): pass

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    import websockets
    import json
    import base64
    import binascii
    from botocore.auth import SigV4QueryAuth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials
    import uuid
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from rmaker_lib.logger import log
from rmaker_lib.aws_credentials import AWSCredentials


class VideoStatistics:
    """Class to track video streaming statistics."""

    def __init__(self):
        self.frames_received = 0
        self.start_time = time.time()
        self.resolution = None
        self.codec = None
        # Per-interval tracking for instantaneous FPS
        self._interval_frames = 0
        self._interval_start = time.time()
        # RTP-level stats from aiortc (updated via update_rtp_stats)
        self._last_packets = 0
        self._last_packets_lost = 0
        self._interval_packets = 0
        self._interval_packets_lost = 0
        self._rtp_bitrate_mbps = 0.0

    def update_frame(self, resolution=None, codec=None):
        """Update statistics with a new decoded frame."""
        self.frames_received += 1
        self._interval_frames += 1
        if resolution:
            self.resolution = resolution
        if codec:
            self.codec = codec

    def update_rtp_stats(self, packets_received, packets_lost):
        """Update with RTP-level stats from aiortc receiver.getStats()."""
        new_packets = packets_received - self._last_packets
        new_lost = packets_lost - self._last_packets_lost
        self._interval_packets += new_packets
        self._interval_packets_lost += new_lost
        self._last_packets = packets_received
        self._last_packets_lost = packets_lost

    def get_stats_string(self):
        """Get formatted statistics string with instantaneous FPS and RTP bitrate."""
        now = time.time()
        interval = now - self._interval_start
        if interval > 0:
            fps = self._interval_frames / interval
            # Estimate bitrate from RTP packets (avg ~1200 bytes per RTP packet)
            self._rtp_bitrate_mbps = (self._interval_packets * 1200 * 8) / interval / 1000000
        else:
            fps = 0

        loss_pct = 0
        if self._interval_packets + self._interval_packets_lost > 0:
            loss_pct = self._interval_packets_lost / (self._interval_packets + self._interval_packets_lost) * 100

        # Reset interval counters
        self._interval_frames = 0
        self._interval_packets = 0
        self._interval_packets_lost = 0
        self._interval_start = now

        resolution_str = f"{self.resolution[0]}x{self.resolution[1]}" if self.resolution else "Unknown"
        codec_str = self.codec or "Unknown"
        elapsed_total = now - self.start_time

        return (
            f"[STATS] Frames: {self.frames_received} | "
            f"Resolution: {resolution_str} | "
            f"Codec: {codec_str} | "
            f"FPS: {fps:.1f} | "
            f"Bitrate: ~{self._rtp_bitrate_mbps:.1f} Mbps | "
            f"Loss: {loss_pct:.1f}% | "
            f"Elapsed: {int(elapsed_total)}s"
        )


def is_video_display_available():
    """
    Check if video display device is available.

    :return: True if display is available, False otherwise
    :rtype: bool
    """
    # Check DISPLAY environment variable (Linux/macOS)
    if sys.platform != 'win32':
        display = os.environ.get('DISPLAY')
        if not display:
            return False

    # Check if OpenCV can create a window
    # On macOS, cv2 operations can hang, so be conservative
    if CV2_AVAILABLE:
        try:
            # Try to create a test window
            # Note: On macOS, this might hang if X11/display server isn't properly configured
            test_img = np.zeros((100, 100, 3), dtype=np.uint8)
            cv2.namedWindow('test', cv2.WINDOW_NORMAL)
            cv2.destroyWindow('test')
            return True
        except Exception:
            return False

    return False


class KVSViewerTrack(VideoStreamTrack):
    """Video track for receiving KVS WebRTC video stream."""

    def __init__(self, stats: VideoStatistics, show_video: bool, save_path: Optional[str] = None, remote_track=None):
        super().__init__()
        self.stats = stats
        self.show_video = show_video
        self.save_path = save_path
        self.remote_track = remote_track  # The actual track received from remote peer
        self.writer = None
        if save_path and CV2_AVAILABLE:
            # Will be initialized when we know the resolution
            pass

    async def recv(self):
        """Receive video frame from remote track."""
        # If we have a remote track, receive from it; otherwise use parent's recv
        if self.remote_track:
            frame = await self.remote_track.recv()
        else:
            frame = await super().recv()

        # Convert frame to numpy array
        if CV2_AVAILABLE:
            img = frame.to_ndarray(format="bgr24")
            height, width = img.shape[:2]
            frame_size = img.nbytes

            # Update statistics
            self.stats.update_frame(frame_size, resolution=(width, height), codec="H264")

            # Save frame if needed
            if self.save_path and self.writer is None:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.writer = cv2.VideoWriter(self.save_path, fourcc, 30.0, (width, height))

            if self.writer:
                self.writer.write(img)

            # Display or return frame
            if self.show_video:
                try:
                    # On macOS, cv2.imshow can hang if not properly initialized
                    # Use a try-except and make it non-blocking
                    cv2.imshow('KVS Video Stream', img)
                    # waitKey(1) returns immediately, non-blocking
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        # Allow user to quit by pressing 'q'
                        log.info("User pressed 'q' to quit")
                        return None
                except cv2.error as e:
                    log.warning(f"OpenCV error displaying frame: {e}. Switching to stats-only mode.")
                    self.show_video = False
                except Exception as e:
                    log.warning(f"Failed to display video frame: {e}. Switching to stats-only mode.")
                    self.show_video = False

        return frame

    def stop(self):
        """Stop the track and cleanup."""
        if self.writer:
            self.writer.release()
        if self.show_video and CV2_AVAILABLE:
            cv2.destroyAllWindows()
        super().stop()


class KVSStreamingClient:
    """KVS WebRTC streaming client for viewer mode."""

    def __init__(self, credentials: AWSCredentials, channel_arn: str,
                 show_video: bool = None, save_path: Optional[str] = None,
                 stats_callback: Optional[Callable] = None):
        """
        Initialize KVS streaming client.

        :param credentials: AWS credentials for KVS
        :type credentials: AWSCredentials
        :param channel_arn: KVS channel ARN
        :type channel_arn: str
        :param show_video: Whether to show video (None = auto-detect)
        :type show_video: bool | None
        :param save_path: Optional path to save video
        :type save_path: str | None
        :param stats_callback: Optional callback for statistics updates
        :type stats_callback: Callable | None
        """
        if not AIORTC_AVAILABLE:
            error_msg = "aiortc is required for KVS streaming"
            if AIORTC_IMPORT_ERROR:
                error_msg += f"\nImport error: {AIORTC_IMPORT_ERROR}"
            error_msg += "\n\nTo install aiortc, run: pip install aiortc"
            error_msg += "\nNote: If you're using Python 3.13+, you may need Python 3.11 or 3.12,"
            error_msg += "\nor install PyAV separately: pip install av"
            raise ImportError(error_msg)
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for KVS streaming. Install with: pip install boto3")

        self.credentials = credentials
        self.channel_arn = channel_arn
        self.save_path = save_path

        if show_video is None:
            # Default: show video if cv2 is available
            self.show_video = CV2_AVAILABLE
            if not CV2_AVAILABLE:
                log.info("OpenCV not available, using stats-only mode")
        else:
            self.show_video = show_video

        self.stats_callback = stats_callback
        self.stats = VideoStatistics()
        self.peer_connection = None
        self.video_track_handler = None
        self.kvs_client = None
        self.running = False

        # Set up AWS credentials for boto3
        os.environ['AWS_ACCESS_KEY_ID'] = credentials.access_key_id
        os.environ['AWS_SECRET_ACCESS_KEY'] = credentials.secret_access_key
        os.environ['AWS_SESSION_TOKEN'] = credentials.session_token
        os.environ['AWS_DEFAULT_REGION'] = credentials.region

        # Initialize KVS client - boto3 handles sigv4 signing automatically
        # Following Python SDK reference pattern
        self.kvs_client = boto3.client(
            'kinesisvideo',
            region_name=credentials.region,
            aws_access_key_id=credentials.access_key_id,
            aws_secret_access_key=credentials.secret_access_key,
            aws_session_token=credentials.session_token
        )

    def _create_wss_url(self, wss_endpoint, channel_arn, client_id=None):
        """
        Create sigv4 signed WebSocket URL for KVS signaling channel.
        Following Python SDK reference implementation using SigV4QueryAuth.

        :param wss_endpoint: WSS endpoint URL from get_signaling_channel_endpoint
        :type wss_endpoint: str
        :param channel_arn: Channel ARN
        :type channel_arn: str
        :param client_id: Optional client ID (if not provided, generates a new one)
        :type client_id: str | None
        :return: Signed WebSocket URL and client ID
        :rtype: tuple[str, str]
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets is required for WebSocket signaling. Install with: pip install websockets")

        # Generate unique client ID if not provided
        if client_id is None:
            client_id = str(uuid.uuid4())

        # Create botocore credentials
        auth_credentials = Credentials(
            access_key=self.credentials.access_key_id,
            secret_key=self.credentials.secret_access_key,
            token=self.credentials.session_token
        )

        # Use SigV4QueryAuth to sign the request (matches Python SDK reference)
        # Expires in 299 seconds (matches Python SDK)
        sigv4 = SigV4QueryAuth(auth_credentials, 'kinesisvideo', self.credentials.region, 299)
        aws_request = AWSRequest(
            method='GET',
            url=wss_endpoint,
            params={'X-Amz-ChannelARN': channel_arn, 'X-Amz-ClientId': client_id},
        )
        sigv4.add_auth(aws_request)
        prepared_request = aws_request.prepare()

        return prepared_request.url, client_id

    def _encode_msg(self, action, payload, recipient_client_id=None):
        """
        Encode message for WebSocket signaling.
        KVS backend expects PascalCase: action, RecipientClientId, MessagePayload
        Device expects camelCase: messageType, messagePayload, recipientClientId
        We use PascalCase for sending TO KVS backend (which forwards to device).

        :param action: Message action (e.g., 'SDP_OFFER', 'ICE_CANDIDATE')
        :type action: str
        :param payload: Message payload dict
        :type payload: dict
        :param recipient_client_id: Optional recipient client ID
        :type recipient_client_id: str | None
        :return: JSON encoded message string
        :rtype: str
        """
        msg = {
            'action': action,  # KVS backend expects 'action' not 'messageType'
            'MessagePayload': base64.b64encode(json.dumps(payload).encode('ascii')).decode('ascii')  # PascalCase for KVS
        }
        if recipient_client_id:
            msg['RecipientClientId'] = recipient_client_id  # PascalCase for KVS
        return json.dumps(msg)

    def _decode_msg(self, msg):
        """
        Decode message from WebSocket signaling.
        Following KVS SDK format - handles both PascalCase and camelCase for compatibility.

        :param msg: JSON message string
        :type msg: str
        :return: Tuple of (messageType, payload_dict, senderClientId)
        :rtype: tuple[str, dict, str]
        """
        # Handle empty messages gracefully
        if not msg or not msg.strip():
            return '', {}, ''

        try:
            data = json.loads(msg)
            log.debug(f"Decoded message data keys: {list(data.keys())}")

            # Check if MessagePayload exists (PascalCase - KVS SDK format)
            # Also check messagePayload (camelCase) for backward compatibility
            message_payload = data.get('MessagePayload') or data.get('messagePayload')
            if not message_payload:
                log.warning(f"Message missing MessagePayload/messagePayload field: {data}")
                return data.get('messageType', ''), {}, data.get('senderClientId', '')

            payload = json.loads(base64.b64decode(message_payload.encode('ascii')).decode('ascii'))
            log.debug(f"Decoded payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'not a dict'}")
            return data.get('messageType', ''), payload, data.get('senderClientId', '')
        except json.JSONDecodeError as e:
            # Log only if it's not an empty message (which is common for ping/pong)
            if msg.strip():
                log.warning(f"Failed to decode JSON message: {e}, message: {msg[:200]}")
            return '', {}, ''
        except (KeyError, UnicodeDecodeError, binascii.Error) as e:
            log.warning(f"Failed to decode message payload: {e}, message: {msg[:200]}")
            return '', {}, ''

    async def _consume_video_frames(self):
        """Continuously consume frames from the video track to keep the stream alive.

        This method runs as a concurrent task alongside the WebSocket message loop.
        It reads directly from the remote track (not through KVSViewerTrack wrapper)
        and prints stats to console.
        """
        # Get the actual remote video track from the peer connection receivers
        remote_track = None
        if self.video_track_handler and self.video_track_handler.remote_track:
            remote_track = self.video_track_handler.remote_track
        elif self.peer_connection:
            # Fallback: find video track from receivers
            for receiver in self.peer_connection.getReceivers():
                if receiver.track and receiver.track.kind == "video":
                    remote_track = receiver.track
                    break

        if not remote_track:
            log.warning("No remote video track available - cannot consume frames")
            return

        log.info(f"Starting frame consumption from remote track (kind={remote_track.kind}, "
                 f"readyState={remote_track.readyState})")
        if self.peer_connection:
            log.info(f"Connection state: {self.peer_connection.connectionState}, "
                     f"ICE: {self.peer_connection.iceConnectionState}")

        last_stats_time = time.time()
        stats_interval = 2.0

        try:
            while self.running:
                try:
                    frame = await asyncio.wait_for(remote_track.recv(), timeout=5.0)
                    if frame is None:
                        log.info("Video track ended (recv returned None)")
                        break

                    # Update frame stats (no decoding needed)
                    resolution = None
                    if hasattr(frame, 'width') and hasattr(frame, 'height'):
                        resolution = (frame.width, frame.height)
                    self.stats.update_frame(resolution=resolution, codec="H264")

                    # Display video if enabled (decode to BGR only when showing)
                    if self.show_video and CV2_AVAILABLE:
                        try:
                            img = frame.to_ndarray(format="bgr24")
                            h, w = img.shape[:2]
                            img_small = cv2.resize(img, (w // 2, h // 2))
                            cv2.imshow('ESP RainMaker Camera', img_small)
                            key = cv2.waitKey(10) & 0xFF
                            if key == ord('q') or key == 27:
                                self.running = False
                                if self.peer_connection:
                                    asyncio.ensure_future(self.peer_connection.close())
                                cv2.destroyAllWindows()
                                cv2.waitKey(1)  # Flush macOS UI events
                                print("\nVideo closed.")
                                return
                        except Exception as e:
                            log.warning(f"Display error: {e}, disabling video")
                            self.show_video = False

                except asyncio.TimeoutError:
                    conn_state = self.peer_connection.connectionState if self.peer_connection else "unknown"
                    ice_state = self.peer_connection.iceConnectionState if self.peer_connection else "unknown"
                    log.warning(f"No video frames in 5s (conn={conn_state}, ice={ice_state}, "
                                f"track={remote_track.readyState})")
                except Exception as e:
                    if not self.running:
                        log.info("Stream stopped, exiting frame consumption")
                        break
                    log.error(f"Error receiving frame: {e}")
                    import traceback
                    log.error(traceback.format_exc())
                    await asyncio.sleep(0.5)

                # Poll RTP stats and print (must be at loop level, not inside except)
                now = time.time()
                if now - last_stats_time >= stats_interval:
                    # Get real RTP packet counts from aiortc receivers
                    if self.peer_connection:
                        try:
                            for receiver in self.peer_connection.getReceivers():
                                if receiver.track and receiver.track.kind == "video":
                                    stats = await receiver.getStats()
                                    for stat in stats.values():
                                        if hasattr(stat, 'packetsReceived'):
                                            self.stats.update_rtp_stats(
                                                stat.packetsReceived,
                                                getattr(stat, 'packetsLost', 0))
                        except Exception:
                            pass
                    print(self.stats.get_stats_string(), flush=True)
                    last_stats_time = now
        except asyncio.CancelledError:
            log.info("Frame consumption task cancelled")
        except Exception as e:
            log.error(f"Fatal error in frame consumption: {e}")
            import traceback
            log.error(traceback.format_exc())

    async def connect(self):
        """Connect to KVS signaling channel and establish WebRTC connection."""
        # Debug logging for aioice (STUN/TURN) and dtls is enabled at module level
        # This helps verify STUN/TURN binding requests/responses and diagnose DTLS handshake issues
        log.debug("STUN/TURN binding requests/responses will be logged by aioice module (if DEBUG logging enabled)")
        log.debug("DTLS handshake details will be logged by dtls module (if DEBUG logging enabled)")

        # Set up exception handler early to catch TURN/STUN errors
        def exception_handler(loop, context):
            """Handle unhandled exceptions in the event loop."""
            exception = context.get('exception')
            if exception:
                exception_type = type(exception).__name__
                exception_str = str(exception)

                # Handle TURN/STUN errors - these are often non-fatal but provide useful diagnostics
                if ('TransactionFailed' in exception_type or
                    'TURN' in exception_str or
                    'STUN' in exception_str or
                    'Forbidden IP' in exception_str or
                    '403' in exception_str):
                    if self.peer_connection and self.peer_connection.iceConnectionState in ['connected', 'completed']:
                        log.debug(f"Suppressing non-fatal TURN/STUN error (ICE connection established): {exception_type}")
                        log.debug(f"STUN/TURN error details: {exception_str}")
                        return
                    else:
                        # Log TURN/STUN errors during ICE establishment - these might indicate connectivity issues
                        log.warning(f"TURN/STUN error during ICE establishment: {exception_type}")
                        log.warning(f"Error details: {exception_str}")
                        log.warning("This may indicate network/firewall issues preventing STUN/TURN binding requests")
                        # Don't suppress - log it for diagnostics, but don't crash
                        return

                # Log other unhandled exceptions as warnings
                log.warning(f"Unhandled exception in event loop: {context.get('message', 'Unknown error')}")

        # Set exception handler for the event loop
        try:
            loop = asyncio.get_running_loop()
            loop.set_exception_handler(exception_handler)
        except RuntimeError:
            pass

        log.info(f"Connecting to KVS channel: {self.channel_arn}")

        try:
            # Resolve channel name to ARN if needed
            # Following Python SDK reference pattern - use boto3 which handles sigv4 automatically
            actual_channel_arn = self.channel_arn

            if not actual_channel_arn.startswith('arn:aws:kinesisvideo:'):
                log.info(f"Channel name provided, resolving to ARN: {self.channel_arn}")
                try:
                    # Use boto3 client - it handles sigv4 signing automatically
                    describe_response = self.kvs_client.describe_signaling_channel(
                        ChannelName=self.channel_arn
                    )
                    actual_channel_arn = describe_response['ChannelInfo']['ChannelARN']
                    log.info(f"Resolved channel ARN: {actual_channel_arn}")
                except Exception as e:
                    log.error(f"Failed to resolve channel name to ARN: {e}")
                    raise Exception(f"Failed to resolve channel name '{self.channel_arn}' to ARN: {e}")

            # Get signaling channel endpoint using boto3
            # Following Python SDK reference pattern - boto3 handles all sigv4 signing
            response = self.kvs_client.get_signaling_channel_endpoint(
                ChannelARN=actual_channel_arn,
                SingleMasterChannelEndpointConfiguration={
                    'Protocols': ['WSS', 'HTTPS'],
                    'Role': 'VIEWER'
                }
            )

            endpoints = response['ResourceEndpointList']
            wss_endpoint = None
            https_endpoint = None
            for endpoint in endpoints:
                if endpoint['Protocol'] == 'WSS':
                    wss_endpoint = endpoint['ResourceEndpoint']
                elif endpoint['Protocol'] == 'HTTPS':
                    https_endpoint = endpoint['ResourceEndpoint']

            if not wss_endpoint:
                raise Exception("WSS endpoint not found")
            if not https_endpoint:
                raise Exception("HTTPS endpoint not found")

            log.info(f"WSS endpoint: {wss_endpoint}")
            log.info(f"HTTPS endpoint: {https_endpoint}")

            # Prepare ICE servers (following Python SDK reference)
            # Generate client ID first (needed for ICE server config)
            client_id = str(uuid.uuid4())

            # Create kinesis-video-signaling client for ICE server config
            kvs_signaling_client = boto3.client(
                'kinesis-video-signaling',
                endpoint_url=https_endpoint,
                region_name=self.credentials.region,
                aws_access_key_id=self.credentials.access_key_id,
                aws_secret_access_key=self.credentials.secret_access_key,
                aws_session_token=self.credentials.session_token
            )

            # Get ICE server configuration
            ice_server_config = kvs_signaling_client.get_ice_server_config(
                ChannelARN=actual_channel_arn,
                ClientId=client_id
            )

            # Build ICE servers list (following Python SDK reference)
            ice_servers = [RTCIceServer(urls=f'stun:stun.kinesisvideo.{self.credentials.region}.amazonaws.com:443')]
            log.debug(f"Added STUN server: stun:stun.kinesisvideo.{self.credentials.region}.amazonaws.com:443")
            log.info(f"STUN server configured: stun:stun.kinesisvideo.{self.credentials.region}.amazonaws.com:443")
            log.info("STUN binding requests will be sent automatically by aiortc's ICE stack during connectivity checks")

            for ice_server in ice_server_config['IceServerList']:
                ice_servers.append(RTCIceServer(
                    urls=ice_server['Uris'],
                    username=ice_server['Username'],
                    credential=ice_server['Password']
                ))
                log.debug(f"Added TURN server: {ice_server['Uris']}")
                log.info(f"TURN server configured: {ice_server['Uris']}")
                log.info("TURN allocation requests will be sent automatically by aiortc's ICE stack if needed")

            log.info(f"Prepared {len(ice_servers)} ICE servers (1 STUN + {len(ice_servers)-1} TURN)")
            log.info("STUN/TURN binding requests/responses are handled automatically by aiortc's ICE implementation")
            log.info("To see detailed STUN/TURN logs, enable DEBUG logging: logging.getLogger('aioice').setLevel(logging.DEBUG)")

            # Verify at least one ICE server is configured
            if len(ice_servers) == 0:
                raise Exception("No ICE servers configured - at least one STUN or TURN server is required")

            # Create peer connection with ICE servers configuration
            # Note: RTCConfiguration defaults are fine for DTLS:
            # - bundlePolicy: "balanced" (default) - allows media bundling
            # - rtcpMuxPolicy: "require" (default) - RTCP multiplexed over RTP
            # - iceTransportPolicy: "all" (default) - allows all candidate types
            # DTLS role is determined automatically: offerer (us) = DTLS server, answerer (device) = DTLS client
            configuration = RTCConfiguration(iceServers=ice_servers)
            self.peer_connection = RTCPeerConnection(configuration=configuration)
            log.debug("RTCPeerConnection created with default DTLS configuration (offerer = DTLS server)")

            # Store reference to video track handler for later use
            self.video_track_handler = None

            # Set up event handlers (following Python SDK reference)
            @self.peer_connection.on('connectionstatechange')
            async def on_connectionstatechange():
                state = self.peer_connection.connectionState
                ice_state = self.peer_connection.iceConnectionState
                log.info(f'Peer connection state: {state} (ICE: {ice_state})')
                if state == "connecting":
                    log.info("Peer connection connecting (DTLS handshake in progress)")
                    log.info("ICE connectivity checks should be complete (check ICE state logs above)")
                    log.info("STUN/TURN binding requests/responses are handled automatically by aiortc's ICE stack")
                    log.info("DTLS handshake requires ICE to be completed - verify ICE state is 'completed'")
                    log.info("Note: Frames will not be available until DTLS handshake completes (connectionState becomes 'connected')")
                    # Log current ICE state for diagnostics
                    if self.peer_connection:
                        ice_state = self.peer_connection.iceConnectionState
                        log.info(f"Current ICE state: {ice_state} (should be 'completed' for DTLS to proceed)")
                elif state == "connected":
                    log.info("WebRTC peer connection established! (DTLS handshake complete, media flowing)")
                    self.running = True
                    # If frame consumption hasn't started yet, start it now
                    if self.video_track_handler and not hasattr(self, '_frame_task_started'):
                        log.info("DTLS handshake complete - ensuring frame consumption is active")
                        # Frame consumption should already be started, but log to confirm
                elif state == "failed":
                    log.error("WebRTC peer connection failed")
                    log.error("DTLS handshake may have failed or timed out")
                    # Don't immediately set running=False - wait to see if it recovers
                    # The connection might fail temporarily and then recover
                    log.warning("Connection failed, but continuing to monitor for recovery...")
                elif state == "closed":
                    log.info("WebRTC peer connection closed")
                    self.running = False
                elif state == "disconnected":
                    log.warning("WebRTC peer connection disconnected")
                    # Don't set running=False immediately - might reconnect

            @self.peer_connection.on('iceconnectionstatechange')
            async def on_iceconnectionstatechange():
                ice_state = self.peer_connection.iceConnectionState
                conn_state = self.peer_connection.connectionState
                log.info(f'ICE connection state: {ice_state} (connectionState: {conn_state})')


                # Check ICE transport state and writability (DTLS handshake requires writable ICE transport)
                try:
                    # Get transceivers to check ICE transport
                    transceivers = self.peer_connection.getTransceivers()
                    if transceivers:
                        transceiver = transceivers[0]
                        if hasattr(transceiver, 'sender') and transceiver.sender and hasattr(transceiver.sender, 'transport'):
                            ice_transport = transceiver.sender.transport.transport if hasattr(transceiver.sender.transport, 'transport') else None
                            if ice_transport:
                                ice_transport_state = getattr(ice_transport, 'state', 'unknown')
                                log.info(f"ICE transport state: {ice_transport_state}")
                                # Check if transport is writable (needed for DTLS)
                                if hasattr(ice_transport, '_writable'):
                                    log.info(f"ICE transport writable: {ice_transport._writable}")
                except Exception as e:
                    log.debug(f"Could not check ICE transport state: {e}")

                if ice_state == "checking":
                    log.info("ICE connectivity checks in progress (STUN binding requests/responses happening)")
                    log.info("STUN/TURN binding requests are sent automatically by aiortc's ICE stack")
                    log.info("Check aioice debug logs (if enabled) to see STUN/TURN binding request/response details")
                    log.info("STUN binding requests verify network connectivity and help establish media path")
                elif ice_state == "connected":
                    log.info("ICE connection established! (STUN binding successful)")
                    log.info("ICE connectivity checks completed - DTLS handshake should proceed now")
                    log.info("STUN binding responses received successfully - media path is established")
                    log.info("ICE transport should now be writable - DTLS handshake should start automatically")
                elif ice_state == "completed":
                    log.info("ICE connection completed! (All connectivity checks done)")
                    log.info("ICE is ready - DTLS handshake should complete next (connectionState should transition to 'connected')")
                    log.info("STUN/TURN connectivity verified - waiting for DTLS handshake to complete")
                    log.info("ICE transport should be writable - checking DTLS transport state...")


                    # Check DTLS transport state after ICE completes
                    try:
                        receivers = self.peer_connection.getReceivers()
                        for i, receiver in enumerate(receivers):
                            if receiver.transport:
                                dtls_state = receiver.transport.state
                                log.info(f"Receiver {i} DTLS transport state after ICE completed: {dtls_state}")
                                if dtls_state == "new":
                                    log.warning(f"DTLS transport {i} still in 'new' state - handshake not started!")
                                    log.warning("DTLS handshake should start automatically when ICE transport becomes writable")
                                    log.warning("This may indicate an issue with DTLS initialization or certificate exchange")
                                elif dtls_state == "connecting":
                                    log.info(f"DTLS transport {i} is connecting - handshake in progress")


                                    # Check underlying ICE transport to verify it's writable
                                    try:
                                        # Try multiple ways to access ICE transport
                                        ice_transport = None
                                        ice_writable = None
                                        ice_state_attr = None

                                        # Method 1: Direct access via _ice_transport
                                        if hasattr(receiver.transport, '_ice_transport'):
                                            ice_transport = receiver.transport._ice_transport
                                        # Method 2: Access via transport attribute
                                        elif hasattr(receiver.transport, 'transport'):
                                            ice_transport = receiver.transport.transport
                                        # Method 3: Check if transport itself is ICE transport
                                        elif hasattr(receiver.transport, '_writable'):
                                            ice_transport = receiver.transport

                                        if ice_transport:
                                            ice_writable = getattr(ice_transport, '_writable', None)
                                            ice_state_attr = getattr(ice_transport, 'state', None)
                                            log.info(f"  DTLS transport {i} ICE transport state: {ice_state_attr}, writable: {ice_writable}")
                                            if ice_writable is False:
                                                log.error(f"  ICE transport {i} is NOT writable - DTLS handshake cannot proceed!")
                                                log.error("  This indicates ICE connectivity checks did not establish a writable path")
                                            elif ice_writable is True:
                                                log.info(f"  ICE transport {i} IS writable - DTLS handshake should proceed")
                                                log.warning("  If DTLS stays in 'connecting' state, DTLS packets may not be reaching the peer")
                                                log.warning("  Possible causes: firewall/NAT blocking DTLS, packets not being sent/received")
                                            else:
                                                log.warning(f"  Could not determine ICE transport writability (value: {ice_writable})")
                                        else:
                                            log.warning(f"  Could not access ICE transport for receiver {i} - checking alternative methods")
                                            # Try to get transport info from receiver
                                            if hasattr(receiver, 'transport'):
                                                log.info(f"  Receiver {i} transport type: {type(receiver.transport)}")
                                                log.info(f"  Receiver {i} transport attributes: {[attr for attr in dir(receiver.transport) if not attr.startswith('__')]}")
                                    except Exception as e:
                                        log.warning(f"Could not check ICE transport writability for receiver {i}: {e}")
                                        import traceback
                                        log.debug(f"Traceback: {traceback.format_exc()}")

                                elif dtls_state == "connected":
                                    log.info(f"DTLS transport {i} is connected - handshake complete!")
                    except Exception as e:
                        log.debug(f"Could not check DTLS transport state: {e}")

                elif ice_state == "failed":
                    log.error("ICE connection failed")
                    log.error("STUN/TURN binding requests may have failed - check network connectivity and firewall settings")
                    log.error("Verify STUN/TURN servers are reachable and firewall allows UDP traffic on ICE ports")

            @self.peer_connection.on('icegatheringstatechange')
            async def on_icegatheringstatechange():
                log.debug(f'ICE gathering state: {self.peer_connection.iceGatheringState}')

            # Track sent candidates to avoid duplicates
            ice_candidates_sent_set = set()

            # Store websocket reference for ICE candidate handler (will be set when websocket connects)
            websocket_ref = {'socket': None}

            # Set up ICE candidate handler BEFORE websocket connection (to catch early candidates)
            # Handler will use websocket_ref to send candidates when websocket is available
            @self.peer_connection.on('icecandidate')
            async def on_icecandidate(event):
                if event.candidate:
                    candidate_str = event.candidate.candidate

                    # Log candidate details for debugging
                    log.debug(f"ICE candidate event received: candidate={candidate_str}, sdpMid={event.candidate.sdpMid}, sdpMLineIndex={event.candidate.sdpMLineIndex}")

                    # Check if candidate contains IPv4 address (for verification)
                    ipv4_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
                    ipv4_match = re.search(ipv4_pattern, candidate_str)
                    if ipv4_match:
                        log.debug(f"Found IPv4 candidate with IP: {ipv4_match.group(1)}")
                    else:
                        log.debug(f"Candidate does not contain IPv4 address (may be IPv6 or invalid): {candidate_str[:100]}")

                    # Skip if already sent (avoid duplicates)
                    if candidate_str in ice_candidates_sent_set:
                        log.debug(f"Skipping duplicate candidate: {candidate_str[:50]}...")
                        return

                    # Wait for websocket to be available (if not yet connected)
                    websocket = websocket_ref['socket']
                    if websocket is None:
                        log.debug("WebSocket not yet available, candidate will be queued or sent later")
                        # Don't return - we'll try to send it once websocket is available
                        # For now, just log it
                        log.warning(f"ICE candidate gathered before WebSocket connection: {candidate_str[:100]}...")
                        # Still add to set to avoid duplicates
                        ice_candidates_sent_set.add(candidate_str)
                        return

                    # Log sent ICE candidate in JSON format (matches Amazon reference format)
                    candidate_json = {
                        'direction': 'sent',
                        'candidate': candidate_str,
                        'sdpMid': event.candidate.sdpMid,
                        'sdpMLineIndex': event.candidate.sdpMLineIndex,
                        'client_id': client_id,
                        'source': 'icecandidate_event'
                    }
                    log.info(f"ICE CANDIDATE SENT (JSON): {json.dumps(candidate_json, indent=2)}")

                    # Send candidate immediately via websocket (matches Amazon reference)
                    # Format matches device expectations: candidate string with IPv4/IPv6 address
                    candidate_payload = {
                        'candidate': candidate_str,
                        'sdpMid': event.candidate.sdpMid,
                        'sdpMLineIndex': event.candidate.sdpMLineIndex,
                    }
                    candidate_msg = self._encode_msg('ICE_CANDIDATE', candidate_payload, client_id)
                    try:
                        await websocket.send(candidate_msg)
                        ice_candidates_sent_set.add(candidate_str)
                        log.debug(f"Sent ICE candidate via trickle ICE (total: {len(ice_candidates_sent_set)})")
                    except Exception as e:
                        log.warning(f"Failed to send ICE candidate: {e}")
                else:
                    # event.candidate is None - ICE gathering complete
                    log.info("ICE candidate event fired with None - ICE gathering complete")

            # Handle incoming video track from master (viewer receives video)
            # This event fires when remote description is set and tracks are received
            # Following Python SDK reference: wrap received track with our handler
            @self.peer_connection.on('track')
            async def on_track(track):
                log.info(f"Received track: {track.kind} from remote peer")

                # CRITICAL: Check if setRemoteDescription has been called
                # If track is received before setRemoteDescription, DTLS transport may not initialize properly
                if not hasattr(self, '_remote_description_set'):
                    log.warning("Track received BEFORE setRemoteDescription - this may cause DTLS initialization issues")
                    log.warning("DTLS transport may not initialize properly if tracks arrive before remote description is set")

                if track.kind == "video":
                    # Wrap the received video track with our KVSViewerTrack handler
                    # Following Python SDK reference: create wrapper and add it to connection
                    # This allows us to process frames, update stats, and display video
                    # CRITICAL: Adding the track back creates the media path needed for DTLS handshake
                    self.video_track_handler = KVSViewerTrack(self.stats, self.show_video, self.save_path, remote_track=track)
                    self.peer_connection.addTrack(self.video_track_handler)
                    log.info("Video track handler added for incoming stream")

                    # Log connection state after track is added (DTLS should proceed now)
                    conn_state = self.peer_connection.connectionState
                    ice_state = self.peer_connection.iceConnectionState
                    log.info(f"Connection state after track added: {conn_state}, ICE: {ice_state}")
                    log.info("Media path established - DTLS handshake should proceed if ICE is completed")

                    # Verify receiver is active (DTLS handshake requires active receiver)
                    receivers = self.peer_connection.getReceivers()
                    log.info(f"Number of receivers after track added: {len(receivers)}")
                    for i, receiver in enumerate(receivers):
                        if receiver.track and receiver.track.kind == "video":
                            log.info(f"Video receiver {i} is active - DTLS transport should be available")
                            if receiver.transport:
                                dtls_state = receiver.transport.state
                                log.info(f"  DTLS transport state: {dtls_state}")

                                # Try to attach state change listener to monitor DTLS handshake progress
                                try:
                                    if hasattr(receiver.transport, 'on'):
                                        @receiver.transport.on('statechange')
                                        async def on_dtls_statechange():
                                            new_state = receiver.transport.state
                                            log.info(f"DTLS transport {i} state changed to: {new_state}")
                                            if new_state == "connected":
                                                log.info(f"DTLS transport {i} handshake completed successfully!")
                                            elif new_state == "failed":
                                                log.error(f"DTLS transport {i} handshake failed")
                                                # Try to get error details if available
                                                error_details = {}
                                                if hasattr(receiver.transport, '_error'):
                                                    error_details['_error'] = str(receiver.transport._error)
                                                if hasattr(receiver.transport, 'error'):
                                                    error_details['error'] = str(receiver.transport.error)
                                                if hasattr(receiver.transport, '_ssl_error'):
                                                    error_details['_ssl_error'] = str(receiver.transport._ssl_error)
                                                # Check for any exception info
                                                if hasattr(receiver.transport, '__dict__'):
                                                    for attr in ['error', '_error', 'exception', '_exception', 'ssl_error', '_ssl_error']:
                                                        if hasattr(receiver.transport, attr):
                                                            try:
                                                                error_details[attr] = str(getattr(receiver.transport, attr))
                                                            except:
                                                                pass
                                                if error_details:
                                                    log.error(f"DTLS transport {i} error details: {error_details}")
                                                else:
                                                    log.warning(f"DTLS transport {i} failed but no error details available")
                                        log.debug(f"Attached state change listener to DTLS transport {i}")
                                except Exception as e:
                                    log.debug(f"Could not attach state change listener to DTLS transport {i}: {e}")

                                if dtls_state == "connecting":
                                    log.info("  DTLS handshake in progress - this is expected")
                                    log.info("  DTLS handshake should complete automatically when ICE transport is writable")
                                elif dtls_state == "connected":
                                    log.info("  DTLS handshake completed!")
                                elif dtls_state == "failed":
                                    log.error("  DTLS handshake failed - check certificates and network")
                                else:
                                    log.info(f"  DTLS transport state: {dtls_state}")
                            else:
                                log.warning("  No DTLS transport available yet - may need to wait for ICE to complete")
                elif track.kind == "audio":
                    log.info("Received audio track (not processing)")

            # Connect to KVS signaling via WebSocket with sigv4 signing
            # Following Python SDK reference implementation
            if not WEBSOCKETS_AVAILABLE:
                raise ImportError("websockets is required for WebSocket signaling. Install with: pip install websockets")

            # Generate sigv4 signed WebSocket URL using SigV4QueryAuth (matches Python SDK)
            # Note: client_id was already generated above for ICE server config
            signed_wss_url, _ = self._create_wss_url(wss_endpoint, actual_channel_arn, client_id)
            log.info(f"Connecting to WebSocket (client_id: {client_id})...")

            # Establish WebSocket connection using websockets library (matches Python SDK)
            async with websockets.connect(signed_wss_url) as websocket:
                log.info("WebSocket connected, setting up trickle ICE...")

                # Store websocket reference for ICE candidate handler
                websocket_ref['socket'] = websocket

                # Log handler status
                log.debug(f"ICE candidate handler registered: {len(ice_candidates_sent_set)} candidates already gathered")

                # Create offer (viewer initiates connection)
                # For a viewer, we add receive-only transceivers to create a valid offer
                # This signals that we want to receive media without sending any
                self.peer_connection.addTransceiver('video', direction='recvonly')
                self.peer_connection.addTransceiver('audio', direction='recvonly')
                log.info("Added receive-only transceivers, creating offer...")

                # Create offer with receive-only transceivers
                # For trickle ICE, we send the offer immediately and send candidates as they're gathered
                # Create offer - aiortc supports trickle ICE by default when candidates are sent incrementally
                offer = await self.peer_connection.createOffer()

                # CRITICAL: KVS C SDK requires 'a=ice-options:trickle' in SDP to enable trickle ICE
                # Without it, device waits for all candidates before proceeding (non-trickle mode)
                # Check if aiortc already added it, and add if missing
                has_trickle_ice = 'a=ice-options:trickle' in offer.sdp
                log.info(f"aiortc createOffer - trickle ICE attribute present: {has_trickle_ice}")

                if not has_trickle_ice:
                    # Add trickle ICE option to SDP (required by KVS C SDK)
                    # Insert after session-level attributes (after 't=' line)
                    sdp_lines = offer.sdp.split('\r\n') if '\r\n' in offer.sdp else offer.sdp.split('\n')
                    insert_idx = len(sdp_lines)

                    # Find the 't=' line (timing) and insert after it, before any media sections
                    for i, line in enumerate(sdp_lines):
                        if line.startswith('t='):
                            # Look for first 'a=' line after 't=' (session-level attributes)
                            for j in range(i + 1, len(sdp_lines)):
                                if sdp_lines[j].startswith('a='):
                                    insert_idx = j
                                    break
                                elif sdp_lines[j].startswith('m='):
                                    # Media section starts, insert before it
                                    insert_idx = j
                                    break
                            if insert_idx == len(sdp_lines):
                                # No 'a=' found, insert after 't='
                                insert_idx = i + 1
                            break

                    # Insert ice-options:trickle attribute
                    sdp_lines.insert(insert_idx, 'a=ice-options:trickle')
                    offer = RTCSessionDescription(
                        sdp='\r\n'.join(sdp_lines) if '\r\n' in offer.sdp else '\n'.join(sdp_lines),
                        type=offer.type
                    )
                    log.info("Added trickle ICE option (a=ice-options:trickle) to SDP - required by KVS C SDK")
                else:
                    log.info("aiortc already included trickle ICE option in SDP")

                # Set local description with the ORIGINAL offer (aiortc needs its own
                # internal ICE credentials to match its DTLS certificate fingerprints)
                await self.peer_connection.setLocalDescription(offer)

                log.info("Created WebRTC offer (trickle ICE enabled - candidates will be sent as they're gathered)")
                log.info(f"ICE gathering state after setLocalDescription: {self.peer_connection.iceGatheringState}")

                # Wait for ICE gathering to complete (aiortc may gather candidates synchronously)
                # Check if events fired, if not, extract from localDescription after gathering completes
                max_wait = 2.0
                wait_interval = 0.1
                waited = 0.0
                while self.peer_connection.iceGatheringState == "gathering" and waited < max_wait:
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval

                log.info(f"ICE gathering state after wait: {self.peer_connection.iceGatheringState}, candidates sent via events: {len(ice_candidates_sent_set)}")

                # After gathering completes, check if we have candidates in localDescription
                # aiortc doesn't fire icecandidate events reliably, but may add candidates to localDescription.sdp
                if len(ice_candidates_sent_set) == 0 and self.peer_connection.localDescription:
                    log.warning("No ICE candidates sent via events. Checking localDescription SDP for candidates...")

                    local_sdp = self.peer_connection.localDescription.sdp
                    candidate_count_in_sdp = local_sdp.count('a=candidate:')
                    log.info(f"Found {candidate_count_in_sdp} candidate lines in localDescription SDP")

                    if 'a=candidate:' in local_sdp:
                        log.info("Found candidates in localDescription SDP - extracting and sending them")

                        # Extract candidates from localDescription SDP
                        sdp_lines = local_sdp.split('\r\n') if '\r\n' in local_sdp else local_sdp.split('\n')
                        transceivers = self.peer_connection.getTransceivers()
                        current_mid = None
                        mline_index = -1
                        extracted_count = 0

                        for line in sdp_lines:
                            if line.startswith('m='):
                                mline_index += 1
                                current_mid = None
                            elif line.startswith('a=mid:'):
                                current_mid = line.split(':', 1)[1].strip()
                            elif line.startswith('a=candidate:'):
                                # Extract candidate string from SDP line
                                # Format: a=candidate:<foundation> <component-id> <transport> <priority> <ip> <port> typ <type> ...
                                # We need to include "candidate:" prefix to match device format
                                candidate_str = line.split(':', 1)[1].strip()  # This gives us the candidate without "a="
                                # But device expects format: "candidate:0 1 udp ..." (with "candidate:" prefix)
                                # So we need to add "candidate:" prefix if not present
                                if not candidate_str.startswith('candidate:'):
                                    candidate_str = 'candidate:' + candidate_str

                                if candidate_str in ice_candidates_sent_set:
                                    continue

                                # Verify IPv4 format (device expects IPv4 candidates)
                                ipv4_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
                                ipv4_match = re.search(ipv4_pattern, candidate_str)
                                if not ipv4_match:
                                    log.debug(f"Skipping non-IPv4 candidate: {candidate_str[:100]}...")
                                    continue

                                # Determine sdpMid and sdpMLineIndex
                                sdp_mid = current_mid
                                sdp_mline_index = mline_index

                                if not sdp_mid and mline_index < len(transceivers):
                                    transceiver = transceivers[mline_index]
                                    sdp_mid = transceiver.mid if transceiver.mid else str(mline_index)

                                if not sdp_mid:
                                    sdp_mid = str(mline_index) if mline_index >= 0 else "0"
                                if sdp_mline_index < 0:
                                    sdp_mline_index = 0

                                # Send candidate (matches format expected by device)
                                candidate_payload = {
                                    'candidate': candidate_str,
                                    'sdpMid': sdp_mid,
                                    'sdpMLineIndex': sdp_mline_index,
                                }

                                candidate_json = {
                                    'direction': 'sent',
                                    'candidate': candidate_str,
                                    'sdpMid': candidate_payload['sdpMid'],
                                    'sdpMLineIndex': candidate_payload['sdpMLineIndex'],
                                    'client_id': client_id,
                                    'source': 'extracted_from_localdescription_sdp',
                                    'ipv4_address': ipv4_match.group(1)
                                }
                                log.info(f"ICE CANDIDATE SENT (JSON): {json.dumps(candidate_json, indent=2)}")

                                candidate_msg = self._encode_msg('ICE_CANDIDATE', candidate_payload, client_id)
                                try:
                                    await websocket.send(candidate_msg)
                                    ice_candidates_sent_set.add(candidate_str)
                                    extracted_count += 1
                                    log.debug(f"Sent extracted IPv4 candidate (total: {len(ice_candidates_sent_set)})")
                                except Exception as e:
                                    log.warning(f"Failed to send extracted candidate: {e}")

                        if extracted_count > 0:
                            log.info(f"Extracted and sent {extracted_count} IPv4 ICE candidates from localDescription SDP")
                        else:
                            log.warning("No IPv4 candidates found in localDescription SDP")
                    else:
                        log.warning("No candidates found in localDescription SDP - aiortc may not be gathering candidates")
                else:
                    log.info(f"ICE candidates sent via events: {len(ice_candidates_sent_set)} candidates")

                # Log SDP offer in JSON format
                offer_json = {
                    'type': offer.type,
                    'sdp': offer.sdp,
                    'client_id': client_id
                }
                log.info(f"SDP OFFER (JSON): {json.dumps(offer_json, indent=2)}")


                # BUNDLE FIX: Unify ice-ufrag/pwd in the SDP we send over the wire.
                # aiortc generates different credentials per m-line, but KVS C SDK
                # uses a single ICE agent for the BUNDLE group. We keep aiortc's
                # internal state untouched (setLocalDescription used original SDP)
                # and only modify the wire SDP so the device sees unified credentials.
                # TODO: This is a workaround - ideally aiortc should merge ICE
                # transports for BUNDLE groups internally.
                wire_sdp = offer.sdp
                wire_sdp_lines = wire_sdp.split('\r\n') if '\r\n' in wire_sdp else wire_sdp.split('\n')
                wire_line_sep = '\r\n' if '\r\n' in wire_sdp else '\n'
                if any(l.startswith('a=group:BUNDLE') for l in wire_sdp_lines):
                    first_ufrag = first_pwd = None
                    in_media = False
                    for line in wire_sdp_lines:
                        if line.startswith('m='):
                            in_media = True
                        elif in_media and line.startswith('a=ice-ufrag:') and first_ufrag is None:
                            first_ufrag = line
                        elif in_media and line.startswith('a=ice-pwd:') and first_pwd is None:
                            first_pwd = line
                            break
                    if first_ufrag and first_pwd:
                        wire_sdp_lines = [
                            first_ufrag if l.startswith('a=ice-ufrag:') else
                            first_pwd if l.startswith('a=ice-pwd:') else l
                            for l in wire_sdp_lines
                        ]
                        log.info(f"BUNDLE: unified ice-ufrag/pwd in wire SDP (ufrag={first_ufrag.split(':',1)[1]})")

                # KVS C SDK fingerprint fix: aiortc includes sha-256, sha-384, and
                # sha-512 fingerprints. KVS SDK stores the LAST fingerprint per media
                # section and always verifies using sha-256. If sha-384 or sha-512 is
                # last, verification fails (STATUS_SSL_REMOTE_CERTIFICATE_VERIFICATION_FAILED).
                # Strip non-sha-256 fingerprints from the wire SDP.
                wire_sdp_lines = [
                    l for l in wire_sdp_lines
                    if not (l.startswith('a=fingerprint:sha-384') or l.startswith('a=fingerprint:sha-512'))
                ]
                wire_sdp = wire_line_sep.join(wire_sdp_lines)
                log.info("Stripped sha-384/sha-512 fingerprints from wire SDP (KVS SDK only supports sha-256)")

                # Send SDP offer to KVS
                offer_payload = {'sdp': wire_sdp, 'type': offer.type}

                # Send offer with our client_id as recipientClientId
                offer_msg = self._encode_msg('SDP_OFFER', offer_payload, client_id)


                try:
                    await websocket.send(offer_msg)
                    log.info("Sent SDP offer to KVS (trickle ICE enabled - sending candidates as they're gathered)")
                except Exception as e:
                    log.error(f"Failed to send SDP offer: {e}")
                    raise

                # Note: ICE candidates will be sent automatically via the on_icecandidate handler above
                # This matches the Amazon reference implementation - candidates are sent as events fire

                # Process WebSocket messages (SDP answer and ICE candidates)
                # Following Amazon reference: both WebSocket message loop and frame consumption run concurrently
                # Keep WebSocket open to receive all ICE candidates while consuming frames
                answer_received = False
                connection_established = False
                frame_task_started = False  # Track if frame consumption task has been started
                # Queue ICE candidates received before setRemoteDescription
                # ICE agent needs remote description (with ICE ufrag/pwd) to respond to STUN requests
                queued_ice_candidates = []
                log.info("Waiting for SDP answer and ICE candidates from KVS...")

                try:
                    async for message in websocket:
                        # Handle different message types from websockets library
                        if isinstance(message, str):
                            # Log raw message for debugging (truncate if too long)
                            log.debug(f"Received WebSocket message (length: {len(message)}): {message[:200]}...")
                            # Text message
                            msg_type, payload, sender_client_id = self._decode_msg(message)
                        else:
                            # Binary or other message types - skip
                            log.debug(f"Skipping non-text message: {type(message)}")
                            continue

                        # Skip empty messages (common for ping/pong frames)
                        if not msg_type:
                            log.debug("Skipping empty message")
                            continue

                        log.info(f"Received WebSocket message type: {msg_type}")

                        if msg_type == 'SDP_ANSWER':
                            # Receive SDP answer - payload is dict with 'sdp' and 'type'
                            if not answer_received:
                                log.info(f"Received SDP answer from {sender_client_id}")

                                # Log SDP answer in JSON format
                                answer_json = {
                                    'type': payload['type'],
                                    'sdp': payload['sdp'],
                                    'sender_client_id': sender_client_id
                                }
                                log.info(f"SDP ANSWER (JSON): {json.dumps(answer_json, indent=2)}")

                                # CRITICAL: Normalize SDP answer to ensure session-level ICE credentials exist
                                # Some implementations (like KVS) only provide media-level ICE credentials
                                # aiortc may need session-level credentials for proper STUN validation
                                answer_sdp = payload['sdp']
                                answer_sdp_lines = answer_sdp.split('\r\n') if '\r\n' in answer_sdp else answer_sdp.split('\n')

                                # Check if BUNDLE is used (RFC 8843)
                                # For BUNDLE: session-level ICE credentials are optional, but if present must match media-level
                                # aiortc may need session-level credentials to extract remote ufrag for STUN validation
                                uses_bundle = 'a=group:BUNDLE' in answer_sdp
                                if uses_bundle:
                                    log.info("BUNDLE detected in SDP answer - will ensure media-level credentials are consistent and add session-level (matching media-level) for STUN validation")

                                # Check if session-level ICE credentials exist (before first 'm=' line)
                                # Note: candidate lines may also appear at session level, so we need to check carefully
                                has_session_ufrag = False
                                has_session_pwd = False
                                session_level_ufrag = None
                                session_level_pwd = None
                                for line in answer_sdp_lines:
                                    if line.startswith('m='):
                                        break  # Reached first media section
                                    if line.startswith('a=ice-ufrag:'):
                                        has_session_ufrag = True
                                        session_level_ufrag = line.split(':', 1)[1].strip()
                                    elif line.startswith('a=ice-pwd:'):
                                        has_session_pwd = True
                                        session_level_pwd = line.split(':', 1)[1].strip()

                                # If no session-level credentials, extract from first media section and add at session level
                                # Use session-level credentials if they exist, otherwise extract from media-level
                                if has_session_ufrag and has_session_pwd and session_level_ufrag and session_level_pwd:
                                    # Session-level credentials already exist - use them
                                    first_media_ufrag = session_level_ufrag
                                    first_media_pwd = session_level_pwd
                                    log.info(f"SDP answer has session-level ICE credentials: ufrag={first_media_ufrag}, pwd length={len(first_media_pwd)}")
                                elif not has_session_ufrag or not has_session_pwd:
                                    log.info("SDP answer missing session-level ICE credentials - normalizing...")
                                    first_media_ufrag = None
                                    first_media_pwd = None
                                    found_first_media = False

                                    for line in answer_sdp_lines:
                                        if line.startswith('m='):
                                            found_first_media = True
                                        elif found_first_media and line.startswith('a=ice-ufrag:'):
                                            first_media_ufrag = line.split(':', 1)[1].strip()
                                        elif found_first_media and line.startswith('a=ice-pwd:'):
                                            first_media_pwd = line.split(':', 1)[1].strip()
                                            break  # Found both, stop

                                if first_media_ufrag and first_media_pwd:
                                    # Only normalize if session-level credentials don't exist
                                    if not has_session_ufrag or not has_session_pwd:
                                        # For BUNDLE, aiortc ignores session-level credentials and uses media-level only
                                        # So we should NOT add session-level credentials for BUNDLE
                                        # Just ensure media-level credentials are consistent across all media sections
                                        normalized_lines = []
                                        in_media_section = False
                                        needs_normalization = False

                                        # First pass: check if media-level credentials are consistent
                                        media_ufrags = []
                                        media_pwds = []
                                        for line in answer_sdp_lines:
                                            if line.startswith('m='):
                                                in_media_section = True
                                            elif in_media_section and line.startswith('a=ice-ufrag:'):
                                                media_ufrags.append(line.split(':', 1)[1].strip())
                                            elif in_media_section and line.startswith('a=ice-pwd:'):
                                                media_pwds.append(line.split(':', 1)[1].strip())

                                        # Check if normalization is needed (inconsistent media-level credentials)
                                        if len(set(media_ufrags)) > 1 or len(set(media_pwds)) > 1:
                                            needs_normalization = True
                                            log.info("Media-level ICE credentials are inconsistent - normalizing to match first media section")

                                        # Second pass: normalize if needed
                                        in_media_section = False
                                        in_session_level = True  # Before first 'm=' line
                                        for line in answer_sdp_lines:
                                            if line.startswith('m='):
                                                in_media_section = True
                                                in_session_level = False
                                                normalized_lines.append(line)
                                            elif in_media_section and line.startswith('a=ice-ufrag:'):
                                                if needs_normalization or uses_bundle:
                                                    # Ensure all media-level credentials match the first one
                                                    normalized_lines.append(f'a=ice-ufrag:{first_media_ufrag}')
                                                    log.debug(f"Normalized media-level ICE ufrag to: {first_media_ufrag}")
                                                else:
                                                    normalized_lines.append(line)
                                            elif in_media_section and line.startswith('a=ice-pwd:'):
                                                if needs_normalization or uses_bundle:
                                                    # Ensure all media-level credentials match the first one
                                                    normalized_lines.append(f'a=ice-pwd:{first_media_pwd}')
                                                    log.debug(f"Normalized media-level ICE pwd")
                                                else:
                                                    normalized_lines.append(line)
                                            elif in_session_level and (line.startswith('a=ice-ufrag:') or line.startswith('a=ice-pwd:')):
                                                # For BUNDLE, replace session-level credentials with media-level ones (RFC 8843: must match)
                                                # For non-BUNDLE, keep existing session-level credentials
                                                if uses_bundle:
                                                    # Replace with media-level credentials to ensure consistency
                                                    if line.startswith('a=ice-ufrag:'):
                                                        normalized_lines.append(f'a=ice-ufrag:{first_media_ufrag}')
                                                        log.debug(f"Replaced session-level ICE ufrag with media-level for BUNDLE: {first_media_ufrag}")
                                                    elif line.startswith('a=ice-pwd:'):
                                                        normalized_lines.append(f'a=ice-pwd:{first_media_pwd}')
                                                        log.debug(f"Replaced session-level ICE pwd with media-level for BUNDLE")
                                                else:
                                                    normalized_lines.append(line)
                                            elif line.strip() == 't=0 0':
                                                # Add session-level credentials after 't=0 0' if not already present
                                                normalized_lines.append(line)
                                                # Check if session-level credentials already exist (will be added in next iteration if not)
                                                session_creds_exist = any(l.startswith('a=ice-ufrag:') or l.startswith('a=ice-pwd:') for l in normalized_lines[-10:] if not l.startswith('m='))
                                                if not session_creds_exist:
                                                    # Add session-level credentials matching media-level (for BUNDLE) or extracted (for non-BUNDLE)
                                                    normalized_lines.append(f'a=ice-ufrag:{first_media_ufrag}')
                                                    normalized_lines.append(f'a=ice-pwd:{first_media_pwd}')
                                                    log.info(f"Added session-level ICE credentials: ufrag={first_media_ufrag}, pwd length={len(first_media_pwd)}")
                                            else:
                                                normalized_lines.append(line)

                                        if needs_normalization or uses_bundle:
                                            answer_sdp = '\r\n'.join(normalized_lines) if '\r\n' in payload['sdp'] else '\n'.join(normalized_lines)
                                            if uses_bundle:
                                                # Verify session-level credentials match media-level (RFC 8843 requirement)
                                                session_level_creds_found = False
                                                session_ufrag_value = None
                                                for i, line in enumerate(normalized_lines):
                                                    if line.startswith('m='):
                                                        break  # Reached first media section
                                                    if line.startswith('a=ice-ufrag:'):
                                                        session_level_creds_found = True
                                                        session_ufrag_value = line.split(':', 1)[1].strip()
                                                    elif line.startswith('a=ice-pwd:'):
                                                        session_level_creds_found = True
                                                if session_level_creds_found and session_ufrag_value == first_media_ufrag:
                                                    log.info(f"SDP answer normalized: ensured media-level ICE credentials are consistent, added session-level matching media-level (BUNDLE) - ufrag={first_media_ufrag}")
                                                elif session_level_creds_found:
                                                    log.warning(f"WARNING: Session-level ICE credentials found but don't match media-level: session={session_ufrag_value}, media={first_media_ufrag}")
                                                else:
                                                    log.warning("WARNING: No session-level ICE credentials found in normalized SDP for BUNDLE")
                                            else:
                                                log.info("SDP answer normalized: ensured media-level ICE credentials are consistent")
                                        elif not uses_bundle:
                                            # For non-BUNDLE, add session-level credentials if not already present
                                            if 'a=ice-ufrag:' not in '\n'.join(normalized_lines[:20]):  # Check session-level
                                                # Find 't=0 0' and insert after it
                                                final_lines = []
                                                inserted = False
                                                for line in normalized_lines:
                                                    final_lines.append(line)
                                                    if line.strip() == 't=0 0' and not inserted:
                                                        final_lines.append(f'a=ice-ufrag:{first_media_ufrag}')
                                                        final_lines.append(f'a=ice-pwd:{first_media_pwd}')
                                                        inserted = True
                                                        log.info(f"Added session-level ICE credentials: ufrag={first_media_ufrag}, pwd length={len(first_media_pwd)}")
                                                if inserted:
                                                    answer_sdp = '\r\n'.join(final_lines) if '\r\n' in payload['sdp'] else '\n'.join(final_lines)
                                                    log.info("SDP answer normalized: added session-level ICE credentials")
                                                else:
                                                    answer_sdp = '\r\n'.join(normalized_lines) if '\r\n' in payload['sdp'] else '\n'.join(normalized_lines)
                                            else:
                                                answer_sdp = '\r\n'.join(normalized_lines) if '\r\n' in payload['sdp'] else '\n'.join(normalized_lines)
                                        else:
                                            answer_sdp = '\r\n'.join(normalized_lines) if '\r\n' in payload['sdp'] else '\n'.join(normalized_lines)
                                    else:
                                        # Session-level credentials already exist
                                        if uses_bundle:
                                            # For BUNDLE, ensure session-level credentials match media-level (RFC 8843 requirement)
                                            # aiortc may need session-level credentials to extract remote ufrag for STUN validation
                                            log.info("Session-level ICE credentials present but BUNDLE detected - ensuring they match media-level")
                                            normalized_lines = []
                                            in_media_section = False
                                            in_session_level = True

                                            for line in answer_sdp_lines:
                                                if line.startswith('m='):
                                                    in_media_section = True
                                                    in_session_level = False
                                                    normalized_lines.append(line)
                                                elif in_session_level and line.startswith('a=ice-ufrag:'):
                                                    # Replace session-level ufrag with media-level one to ensure consistency (RFC 8843)
                                                    normalized_lines.append(f'a=ice-ufrag:{first_media_ufrag}')
                                                    log.debug(f"Replaced session-level ICE ufrag with media-level for BUNDLE: {first_media_ufrag}")
                                                elif in_session_level and line.startswith('a=ice-pwd:'):
                                                    # Replace session-level pwd with media-level one to ensure consistency (RFC 8843)
                                                    normalized_lines.append(f'a=ice-pwd:{first_media_pwd}')
                                                    log.debug(f"Replaced session-level ICE pwd with media-level for BUNDLE")
                                                elif in_media_section and line.startswith('a=ice-ufrag:'):
                                                    # Ensure all media-level credentials match the first one
                                                    normalized_lines.append(f'a=ice-ufrag:{first_media_ufrag}')
                                                    log.debug(f"Normalized media-level ICE ufrag to: {first_media_ufrag}")
                                                elif in_media_section and line.startswith('a=ice-pwd:'):
                                                    # Ensure all media-level credentials match the first one
                                                    normalized_lines.append(f'a=ice-pwd:{first_media_pwd}')
                                                    log.debug(f"Normalized media-level ICE pwd")
                                                else:
                                                    normalized_lines.append(line)

                                            answer_sdp = '\r\n'.join(normalized_lines) if '\r\n' in payload['sdp'] else '\n'.join(normalized_lines)
                                            log.info(f"SDP answer normalized: ensured session-level and media-level ICE credentials match (BUNDLE) - ufrag={first_media_ufrag}")
                                        else:
                                            # For non-BUNDLE, ensure media-level credentials match session-level
                                            log.info("Session-level ICE credentials already present - ensuring media-level credentials match")
                                            normalized_lines = []
                                            in_media_section = False

                                            for line in answer_sdp_lines:
                                                if line.startswith('m='):
                                                    in_media_section = True
                                                    normalized_lines.append(line)
                                                elif in_media_section and line.startswith('a=ice-ufrag:'):
                                                    # Replace media-level ufrag with session-level one to ensure consistency
                                                    normalized_lines.append(f'a=ice-ufrag:{first_media_ufrag}')
                                                    log.debug(f"Normalized media-level ICE ufrag to match session-level")
                                                elif in_media_section and line.startswith('a=ice-pwd:'):
                                                    # Replace media-level pwd with session-level one to ensure consistency
                                                    normalized_lines.append(f'a=ice-pwd:{first_media_pwd}')
                                                    log.debug(f"Normalized media-level ICE pwd to match session-level")
                                                else:
                                                    normalized_lines.append(line)

                                            answer_sdp = '\r\n'.join(normalized_lines) if '\r\n' in payload['sdp'] else '\n'.join(normalized_lines)
                                            log.info("SDP answer normalized: ensured media-level ICE credentials match session-level")
                                else:
                                    log.warning("Could not extract ICE credentials from SDP for normalization")

                                answer = RTCSessionDescription(sdp=answer_sdp, type=payload['type'])


                                # CRITICAL: Check SDP answer setup attribute for DTLS role negotiation
                                # setup:active = DTLS client, setup:passive = DTLS server, setup:actpass = either
                                if 'a=setup:active' in answer_sdp:
                                    log.info("SDP answer indicates device is DTLS client (setup:active)")
                                    log.info("We (offerer) should be DTLS server - this is correct for viewer/master scenario")
                                    log.info("Device (DTLS client) should initiate handshake by sending ClientHello")
                                    log.info("We (DTLS server) will wait for ClientHello and respond with ServerHello")
                                elif 'a=setup:passive' in answer_sdp:
                                    log.info("SDP answer indicates device is DTLS server (setup:passive)")
                                    log.warning("Unexpected: device is DTLS server, we should be DTLS client")
                                elif 'a=setup:actpass' in answer_sdp:
                                    log.info("SDP answer indicates flexible DTLS role (setup:actpass)")

                                # Mark that remote description is being set (for track event handler)
                                self._remote_description_set = True


                                await self.peer_connection.setRemoteDescription(answer)
                                log.info("Set remote description from SDP answer")

                                # Start frame consumption task immediately after setting remote description.
                                # Don't wait for ICE/DTLS to complete - the task handles waiting internally.
                                self.running = True
                                if not frame_task_started:
                                    log.info("Starting frame consumption task after setRemoteDescription")
                                    asyncio.create_task(self._consume_video_frames())
                                    frame_task_started = True


                                # CRITICAL: Verify the normalized SDP was actually applied by checking remoteDescription
                                # This helps diagnose if aiortc is using the normalized SDP or the original one
                                if hasattr(self.peer_connection, 'remoteDescription') and self.peer_connection.remoteDescription:
                                    applied_sdp = self.peer_connection.remoteDescription.sdp
                                    applied_sdp_lines = applied_sdp.split('\r\n') if '\r\n' in applied_sdp else applied_sdp.split('\n')
                                    # Check for session-level ICE credentials (before first 'm=' line)
                                    has_applied_session_ufrag = False
                                    has_applied_session_pwd = False
                                    applied_session_ufrag_value = None
                                    applied_session_pwd_value = None
                                    for line in applied_sdp_lines:
                                        if line.startswith('m='):
                                            break  # Reached first media section
                                        if line.startswith('a=ice-ufrag:'):
                                            has_applied_session_ufrag = True
                                            applied_session_ufrag_value = line.split(':', 1)[1].strip()
                                        elif line.startswith('a=ice-pwd:'):
                                            has_applied_session_pwd = True
                                            applied_session_pwd_value = line.split(':', 1)[1].strip()

                                    # Count total ICE ufrag attributes to verify normalization
                                    total_ufrag_count = sum(1 for line in applied_sdp_lines if line.startswith('a=ice-ufrag:'))

                                    # Extract media-level credentials for comparison
                                    applied_media_ufrags = []
                                    applied_media_pwds = []
                                    current_media_idx = -1
                                    for line in applied_sdp_lines:
                                        if line.startswith('m='):
                                            current_media_idx += 1
                                        elif line.startswith('a=ice-ufrag:'):
                                            ufrag_val = line.split(':', 1)[1].strip()
                                            if current_media_idx >= 0:
                                                applied_media_ufrags.append((current_media_idx, ufrag_val))
                                        elif line.startswith('a=ice-pwd:'):
                                            pwd_val = line.split(':', 1)[1].strip()
                                            if current_media_idx >= 0:
                                                applied_media_pwds.append((current_media_idx, pwd_val))


                                    if uses_bundle:
                                        # For BUNDLE, aiortc uses media-level credentials only (ignores session-level)
                                        if len(applied_media_ufrags) > 0:
                                            # Check if all media-level credentials are consistent
                                            media_ufrag_values = [ufrag[1] for ufrag in applied_media_ufrags]
                                            all_consistent = len(set(media_ufrag_values)) == 1
                                            if all_consistent:
                                                log.info(f"Verified: Media-level ICE credentials are consistent (BUNDLE) - ufrag={media_ufrag_values[0]}")
                                            else:
                                                log.warning(f"WARNING: Media-level ICE credentials are inconsistent (BUNDLE): {media_ufrag_values}")
                                        else:
                                            log.warning("WARNING: No media-level ICE credentials found in applied SDP (BUNDLE)")
                                    else:
                                        # For non-BUNDLE, check both session-level and media-level
                                        if has_applied_session_ufrag and has_applied_session_pwd:
                                            log.info(f"Verified: Normalized SDP with session-level ICE credentials was applied successfully (found {total_ufrag_count} total ICE ufrag attributes)")
                                        else:
                                            log.warning("WARNING: Applied SDP may not have session-level ICE credentials - checking media-level...")
                                            log.info(f"Found {total_ufrag_count} ICE ufrag attributes in applied SDP")
                                            if total_ufrag_count >= 2:
                                                log.info("Note: Media-level ICE credentials present - aiortc may use these for STUN validation")
                                else:
                                    log.warning("Could not verify applied SDP - remoteDescription not available")

                                # CRITICAL: Extract and log ICE credentials from SDP answer for debugging STUN validation failures
                                # aiortc uses these credentials to validate incoming STUN binding requests
                                answer_sdp_lines = answer_sdp.split('\r\n') if '\r\n' in answer_sdp else answer_sdp.split('\n')
                                session_ufrag = None
                                session_pwd = None
                                media_ufrags = []
                                media_pwds = []
                                current_media_index = -1

                                for line in answer_sdp_lines:
                                    if line.startswith('m='):
                                        current_media_index += 1
                                    elif line.startswith('a=ice-ufrag:'):
                                        ufrag_value = line.split(':', 1)[1].strip()
                                        if current_media_index == -1:
                                            # Session-level ufrag
                                            session_ufrag = ufrag_value
                                            log.info(f"SDP answer session-level ICE ufrag: {ufrag_value}")
                                        else:
                                            # Media-level ufrag
                                            media_ufrags.append((current_media_index, ufrag_value))
                                            log.info(f"SDP answer media-level ICE ufrag (media {current_media_index}): {ufrag_value}")
                                    elif line.startswith('a=ice-pwd:'):
                                        pwd_value = line.split(':', 1)[1].strip()
                                        if current_media_index == -1:
                                            # Session-level pwd
                                            session_pwd = pwd_value
                                            log.info(f"SDP answer session-level ICE pwd: {pwd_value[:16]}... (length: {len(pwd_value)})")
                                        else:
                                            # Media-level pwd
                                            media_pwds.append((current_media_index, pwd_value))
                                            log.info(f"SDP answer media-level ICE pwd (media {current_media_index}): {pwd_value[:16]}... (length: {len(pwd_value)})")

                                if session_ufrag and session_pwd:
                                    log.info(f"ICE credentials found: session-level ufrag={session_ufrag}, pwd length={len(session_pwd)}")
                                    log.info("aiortc should use these credentials to validate incoming STUN binding requests")
                                elif media_ufrags and media_pwds:
                                    log.warning(f"Only media-level ICE credentials found (no session-level)")
                                    log.warning("This might cause STUN validation issues if aiortc expects session-level credentials")
                                else:
                                    log.error("No ICE credentials found in SDP answer - STUN validation will fail!")

                                # Also log our local ICE credentials for comparison
                                if hasattr(self.peer_connection, 'localDescription') and self.peer_connection.localDescription:
                                    offer_sdp = self.peer_connection.localDescription.sdp
                                    offer_sdp_lines = offer_sdp.split('\r\n') if '\r\n' in offer_sdp else offer_sdp.split('\n')
                                    local_session_ufrag = None
                                    local_session_pwd = None
                                    for line in offer_sdp_lines:
                                        if line.startswith('a=ice-ufrag:'):
                                            local_session_ufrag = line.split(':', 1)[1].strip()
                                        elif line.startswith('a=ice-pwd:'):
                                            local_session_pwd = line.split(':', 1)[1].strip()
                                    if local_session_ufrag and local_session_pwd:
                                        log.info(f"Local ICE credentials: ufrag={local_session_ufrag}, pwd length={len(local_session_pwd)}")
                                        log.info("STUN requests from device should use USERNAME format: remote_ufrag:local_ufrag")
                                        log.info(f"Expected USERNAME format: {session_ufrag}:{local_session_ufrag}")


                                # CRITICAL: Wait a moment for aiortc to process setRemoteDescription and initialize DTLS transport
                                # The track event may fire before setRemoteDescription completes, causing DTLS transport to not initialize
                                # Also give DTLS handshake time to start - it should begin automatically when ICE completes
                                await asyncio.sleep(0.2)

                                # Log fingerprint verification (aiortc should verify automatically)
                                # Extract fingerprints from SDP for verification
                                offer_fingerprints = []
                                answer_fingerprints = []
                                if hasattr(self.peer_connection, 'localDescription') and self.peer_connection.localDescription:
                                    offer_sdp = self.peer_connection.localDescription.sdp
                                    for match in re.finditer(r'a=fingerprint:sha-256 ([A-F0-9:]+)', offer_sdp):
                                        offer_fingerprints.append(match.group(1))

                                answer_sdp_lines = answer_sdp.split('\r\n') if '\r\n' in answer_sdp else answer_sdp.split('\n')
                                for line in answer_sdp_lines:
                                    if line.startswith('a=fingerprint:sha-256'):
                                        fingerprint = line.split('sha-256', 1)[1].strip()
                                        answer_fingerprints.append(fingerprint)

                                if offer_fingerprints and answer_fingerprints:
                                    log.info(f"Offer fingerprint (sha-256): {offer_fingerprints[0]}")
                                    log.info(f"Answer fingerprint (sha-256): {answer_fingerprints[0]}")
                                    log.info("Fingerprints are different (expected - each peer has its own certificate)")
                                    log.info("aiortc will verify that certificates match fingerprints during DTLS handshake")

                                # Verify DTLS transport was initialized after setRemoteDescription
                                receivers = self.peer_connection.getReceivers()
                                if receivers:
                                    for i, receiver in enumerate(receivers):
                                        if receiver.transport:
                                            dtls_state = receiver.transport.state
                                            log.info(f"DTLS transport {i} state immediately after setRemoteDescription: {dtls_state}")
                                            if dtls_state == "new":
                                                log.warning(f"DTLS transport {i} still in 'new' state - may not have initialized properly")
                                                log.warning("This could indicate a timing issue or DTLS initialization problem")

                                # Log connection state immediately after setRemoteDescription
                                # This helps diagnose DTLS handshake issues
                                conn_state = self.peer_connection.connectionState
                                ice_state = self.peer_connection.iceConnectionState
                                log.info(f"Connection state after setRemoteDescription: {conn_state}, ICE: {ice_state}")

                                # Check if we have transceivers configured (needed for DTLS)
                                transceivers = self.peer_connection.getTransceivers()
                                log.info(f"Number of transceivers: {len(transceivers)}")
                                for i, transceiver in enumerate(transceivers):
                                    log.info(f"Transceiver {i}: kind={transceiver.kind}, direction={transceiver.direction}, currentDirection={transceiver.currentDirection}")

                                # Verify track handler is set (needed for media path and DTLS completion)
                                if self.video_track_handler:
                                    log.info("Video track handler is available - media path should be ready for DTLS")
                                else:
                                    log.warning("Video track handler not yet available - will be set when track is received")
                                    log.warning("DTLS handshake may not complete until track is received and handler is set")

                                # Check receivers (DTLS handshake requires active receivers)
                                receivers = self.peer_connection.getReceivers()
                                log.info(f"Number of receivers after setRemoteDescription: {len(receivers)}")
                                if len(receivers) == 0:
                                    log.warning("No receivers yet - DTLS handshake may wait until track is received")
                                else:
                                    for i, receiver in enumerate(receivers):
                                        log.info(f"Receiver {i}: track={receiver.track.kind if receiver.track else 'None'}, transport={receiver.transport.state if receiver.transport else 'None'}")
                                        if receiver.transport:
                                            log.info(f"  DTLS transport state: {receiver.transport.state}")

                                # Check senders (should be empty for receive-only viewer)
                                senders = self.peer_connection.getSenders()
                                log.debug(f"Number of senders: {len(senders)} (should be 0 for receive-only viewer)")

                                answer_received = True

                                # Start periodic DTLS state monitoring after SDP answer is set
                                async def monitor_dtls_progress():
                                    """Periodically check DTLS handshake progress"""
                                    log.info("DTLS monitoring task started - will check DTLS state every 2 seconds")
                                    start_time = time.time()
                                    last_dtls_state = {}
                                    check_interval = 2.0  # Check every 2 seconds
                                    max_wait = 30.0  # Monitor for up to 30 seconds

                                    while time.time() - start_time < max_wait:
                                        await asyncio.sleep(check_interval)
                                        if not self.peer_connection:
                                            log.warning("Peer connection is None - stopping DTLS monitoring")
                                            break

                                        elapsed_check = int(time.time() - start_time)
                                        log.debug(f"DTLS monitoring check at {elapsed_check}s - connection still active")

                                        conn_state = self.peer_connection.connectionState
                                        ice_state = self.peer_connection.iceConnectionState

                                        # Check DTLS transport states
                                        try:
                                            receivers = self.peer_connection.getReceivers()
                                            dtls_states = {}
                                            for i, receiver in enumerate(receivers):
                                                if receiver.transport:
                                                    dtls_states[i] = receiver.transport.state

                                            # Log if DTLS state changed
                                            for i, state in dtls_states.items():
                                                if i not in last_dtls_state or last_dtls_state[i] != state:
                                                    elapsed = int(time.time() - start_time)
                                                    log.info(f"DTLS transport {i} state changed after {elapsed}s: {last_dtls_state.get(i, 'unknown')} -> {state}")

                                            last_dtls_state = dtls_states.copy()

                                            # Stop monitoring if connection is established or failed
                                            if conn_state == "connected":
                                                log.info("Connection established - stopping DTLS monitoring")
                                                break
                                            elif conn_state == "failed":
                                                log.warning("Connection failed - stopping DTLS monitoring")
                                                break

                                            # Log periodic status if still connecting
                                            if conn_state == "connecting":
                                                elapsed = int(time.time() - start_time)
                                                all_connecting = all(s == "connecting" for s in dtls_states.values())
                                                # Log every 5 seconds OR if elapsed is >= 5 (to catch first 5s mark)
                                                if all_connecting and (elapsed >= 5 and elapsed % 5 == 0):
                                                    # Check ICE transport state for each receiver
                                                    ice_transport_info = {}
                                                    try:
                                                        for i, receiver in enumerate(receivers):
                                                            if receiver.transport:
                                                                ice_transport = receiver.transport._ice_transport if hasattr(receiver.transport, '_ice_transport') else None
                                                                if ice_transport:
                                                                    ice_transport_info[i] = {
                                                                        "state": getattr(ice_transport, 'state', None),
                                                                        "role": getattr(ice_transport, 'role', None),
                                                                        "connection_state": getattr(ice_transport, 'connectionState', None)
                                                                    }
                                                    except Exception as e:
                                                        ice_transport_info = {"error": str(e)}

                                                    log.info(f"DTLS still connecting after {elapsed}s - states: {dtls_states}, ICE transport info: {ice_transport_info}")
                                        except Exception as e:
                                            log.debug(f"Error monitoring DTLS progress: {e}")

                                # Start DTLS monitoring task
                                try:
                                    monitoring_task = asyncio.create_task(monitor_dtls_progress())
                                    log.debug(f"Started DTLS monitoring task: {monitoring_task}")
                                except Exception as e:
                                    log.error(f"Failed to start DTLS monitoring task: {e}")
                                    import traceback
                                    log.debug(f"Traceback: {traceback.format_exc()}")

                                # CRITICAL: Now that setRemoteDescription is called, add any queued ICE candidates
                                # ICE agent can now respond to STUN requests because it has remote ICE credentials
                                if queued_ice_candidates:
                                    log.info(f"Processing {len(queued_ice_candidates)} queued ICE candidates (received before setRemoteDescription)")
                                    for queued_candidate_data in queued_ice_candidates:
                                        try:
                                            candidate = candidate_from_sdp(queued_candidate_data['candidate'])
                                            candidate.sdpMid = queued_candidate_data.get('sdpMid')
                                            candidate.sdpMLineIndex = queued_candidate_data.get('sdpMLineIndex')
                                            await self.peer_connection.addIceCandidate(candidate)
                                            log.info(f"Added queued ICE candidate: {queued_candidate_data['candidate'][:100]}...")
                                        except Exception as e:
                                            log.error(f"Error adding queued ICE candidate: {e}")
                                    queued_ice_candidates.clear()
                                    log.info("Finished processing queued ICE candidates")
                            else:
                                log.warning("Received duplicate SDP_ANSWER, ignoring")

                        elif msg_type == 'ICE_CANDIDATE':
                            # Handle ICE candidate - payload is dict with candidate info
                            try:
                                # Log received ICE candidate in JSON format
                                candidate_json = {
                                    'direction': 'received',
                                    'candidate': payload.get('candidate', ''),
                                    'sdpMid': payload.get('sdpMid'),
                                    'sdpMLineIndex': payload.get('sdpMLineIndex'),
                                    'sender_client_id': sender_client_id
                                }
                                log.info(f"ICE CANDIDATE RECEIVED (JSON): {json.dumps(candidate_json, indent=2)}")

                                # CRITICAL: Check if setRemoteDescription has been called
                                # ICE agent needs remote description (with ICE ufrag/pwd) to respond to STUN requests
                                # If we add candidates before setRemoteDescription, the ICE agent cannot respond to STUN requests
                                if not answer_received:
                                    log.warning("ICE candidate received BEFORE setRemoteDescription - queueing for later")
                                    log.warning("ICE agent cannot respond to STUN requests without remote ICE credentials")
                                    queued_ice_candidates.append({
                                        'candidate': payload.get('candidate', ''),
                                        'sdpMid': payload.get('sdpMid'),
                                        'sdpMLineIndex': payload.get('sdpMLineIndex')
                                    })
                                    log.info(f"Queued ICE candidate (will add after setRemoteDescription). Queue size: {len(queued_ice_candidates)}")
                                    continue

                                candidate = candidate_from_sdp(payload['candidate'])
                                candidate.sdpMid = payload.get('sdpMid')
                                candidate.sdpMLineIndex = payload.get('sdpMLineIndex')

                                # Log candidate details for debugging ICE connectivity
                                candidate_str = payload.get('candidate', '')
                                log.info(f"Adding remote ICE candidate: {candidate_str[:150]}...")
                                log.info(f"  sdpMid: {candidate.sdpMid}, sdpMLineIndex: {candidate.sdpMLineIndex}")
                                if hasattr(candidate, 'address'):
                                    log.info(f"  Remote candidate address: {candidate.address}:{candidate.port}")

                                await self.peer_connection.addIceCandidate(candidate)
                                log.info(f"Successfully added remote ICE candidate from {sender_client_id}")

                                # After adding remote candidate, aiortc should automatically:
                                # 1. Form candidate pairs with local candidates
                                # 2. Perform connectivity checks (STUN binding requests)
                                # 3. Send STUN binding responses when receiving requests
                                # Check ICE state to see if connectivity checks are happening
                                ice_state = self.peer_connection.iceConnectionState
                                ice_gathering_state = self.peer_connection.iceGatheringState
                                log.info(f"ICE connection state after adding candidate: {ice_state}, gathering: {ice_gathering_state}")

                                # CRITICAL: Check if we have local candidates to pair with remote candidate
                                # If no local candidates, no candidate pairs can be formed
                                try:
                                    if hasattr(self.peer_connection, 'localDescription') and self.peer_connection.localDescription:
                                        local_sdp = self.peer_connection.localDescription.sdp
                                        local_candidates = [line for line in local_sdp.split('\n') if 'a=candidate:' in line]
                                        log.info(f"Number of local candidates available for pairing: {len(local_candidates)}")
                                        if len(local_candidates) == 0:
                                            log.error("No local candidates available - cannot form candidate pairs!")
                                            log.error("This will prevent ICE connectivity checks from working")
                                        else:
                                            log.info(f"Local candidates available - should be able to form pairs with remote candidate")
                                            # Log a sample local candidate for comparison
                                            if local_candidates:
                                                log.debug(f"Sample local candidate: {local_candidates[0][:150]}...")

                                        # CRITICAL: Verify setRemoteDescription has been called
                                        # ICE agent needs remote description (with ICE ufrag/pwd) to respond to STUN requests
                                        if hasattr(self.peer_connection, 'remoteDescription') and self.peer_connection.remoteDescription:
                                            log.info("Remote description is set - ICE agent can respond to STUN binding requests")
                                            remote_sdp = self.peer_connection.remoteDescription.sdp
                                            remote_sdp_lines = remote_sdp.split('\r\n') if '\r\n' in remote_sdp else remote_sdp.split('\n')
                                            remote_ufrag = None
                                            remote_pwd = None
                                            in_media_section = False

                                            # Extract session-level credentials first (if present)
                                            for line in remote_sdp_lines:
                                                if line.startswith('m='):
                                                    in_media_section = True
                                                    break
                                                if line.startswith('a=ice-ufrag:'):
                                                    remote_ufrag = line.split(':', 1)[1].strip()
                                                elif line.startswith('a=ice-pwd:'):
                                                    remote_pwd = line.split(':', 1)[1].strip()

                                            # If no session-level credentials, extract from first media section (for BUNDLE)
                                            if not remote_ufrag or not remote_pwd:
                                                in_media_section = False
                                                for line in remote_sdp_lines:
                                                    if line.startswith('m='):
                                                        in_media_section = True
                                                    elif in_media_section and line.startswith('a=ice-ufrag:'):
                                                        remote_ufrag = line.split(':', 1)[1].strip()
                                                        if remote_pwd:  # Found both
                                                            break
                                                    elif in_media_section and line.startswith('a=ice-pwd:'):
                                                        remote_pwd = line.split(':', 1)[1].strip()
                                                        if remote_ufrag:  # Found both
                                                            break

                                            if remote_ufrag and remote_pwd:
                                                log.info(f"Remote ICE credentials available (ufrag: {remote_ufrag[:8]}...) - STUN responses should work")
                                            else:
                                                log.warning("Remote ICE credentials not found in SDP - STUN responses may fail!")
                                        else:
                                            log.warning("Remote description NOT set yet - ICE agent cannot respond to STUN requests!")
                                            log.warning("STUN binding responses will only work after setRemoteDescription is called")
                                except Exception as e:
                                    log.debug(f"Could not check local candidates: {e}")

                                if ice_state == "checking":
                                    log.info("ICE connectivity checks should be in progress - STUN binding requests/responses should be happening")
                                    log.info("Device should be receiving STUN binding responses from us")
                                    log.warning("If device shows 0 STUN responses, responses may be blocked by firewall/NAT")
                                    log.info("aiortc should automatically respond to STUN binding requests from device")
                                    log.info("Enable aioice debug logs to see STUN request/response details")
                                elif ice_state == "completed":
                                    # ICE completed on our side - verify if connection actually works
                                    # The warning about device not showing candidate pair may be misleading
                                    # since we cannot actually verify device state
                                    log.info("ICE completed on our side - checking if connection is actually working")
                                    conn_state = self.peer_connection.connectionState
                                    log.info(f"Connection state: {conn_state} (should be 'connected' if DTLS handshake succeeded)")

                                    # Check if we have active transceivers (indicates connection is working)
                                    try:
                                        transceivers = self.peer_connection.getTransceivers()
                                        active_transceivers = [t for t in transceivers if t.currentDirection is not None]
                                        log.info(f"Active transceivers: {len(active_transceivers)}/{len(transceivers)}")
                                        if active_transceivers:
                                            log.info("Connection appears to be working - transceivers are active")
                                        else:
                                            log.warning("No active transceivers - connection may not be fully established")
                                    except Exception as e:
                                        log.debug(f"Could not check transceivers: {e}")

                                    # Log warning only if connection state is not 'connected'
                                    if conn_state != "connected":
                                        log.warning("ICE already completed on our side - but connection state is not 'connected'")
                                        log.warning("This suggests DTLS handshake may have failed, or STUN responses aren't reaching the device")
                                        log.warning("Possible causes:")
                                        log.warning("  1. Firewall/NAT blocking UDP packets (STUN responses)")
                                        log.warning("  2. One-way connectivity (we can receive but can't send)")
                                        log.warning("  3. Candidate pairs not matching (wrong IPs/ports)")
                                        log.warning("  4. DTLS handshake failed (check DTLS logs)")
                                    else:
                                        log.info("Connection state is 'connected' - connection appears to be working despite warning")
                                elif ice_state == "new":
                                    log.warning("ICE still in 'new' state - connectivity checks haven't started yet")
                                    log.warning("This may indicate that setRemoteDescription hasn't been called, or ICE gathering isn't complete")
                            except Exception as e:
                                log.error(f"Error adding ICE candidate: {e}")

                        elif msg_type == 'STATUS_RESPONSE':
                            # Status response from KVS
                            log.info(f"Status response: {payload}")
                        elif msg_type == 'GO_AWAY':
                            # Server is closing connection
                            log.warning("Received GO_AWAY message from KVS")
                            raise Exception("KVS server closed connection (GO_AWAY)")
                        else:
                            log.debug(f"Unhandled message type: {msg_type}")

                        # Check connection state periodically while processing messages
                        # This allows us to detect when connection is established
                        # Once ICE completes, start frame consumption as a concurrent task
                        # (matches Amazon reference: both WebSocket message loop and frame consumption run concurrently)
                        if answer_received and not connection_established:
                            conn_state = self.peer_connection.connectionState
                            ice_state = self.peer_connection.iceConnectionState

                            if conn_state == "connected":
                                self.running = True
                                connection_established = True
                                log.info("WebRTC connection established!")
                                # Start frame consumption as concurrent task (keeps WebSocket loop running)
                                # Frame consumption is critical for keeping connection alive and completing DTLS
                                # Matches Amazon reference: both loops run concurrently in async mode
                                if self.video_track_handler and not frame_task_started:
                                    log.info("Starting frame consumption task (concurrent with WebSocket message loop)")
                                    asyncio.create_task(self._consume_video_frames())
                                    frame_task_started = True
                            elif ice_state == "completed" and conn_state in ["connecting", "connected"]:
                                self.running = True
                                connection_established = True
                                log.info(f"ICE connection completed - WebRTC connection established! (state: {conn_state})")
                                # Start frame consumption as concurrent task (keeps WebSocket loop running)
                                # Frame consumption is critical for keeping connection alive and completing DTLS
                                # Matches Amazon reference: both loops run concurrently in async mode
                                if self.video_track_handler and not frame_task_started:
                                    log.info("Starting frame consumption task (concurrent with WebSocket message loop)")
                                    asyncio.create_task(self._consume_video_frames())
                                    frame_task_started = True
                            elif conn_state == "failed" and ice_state == "failed":
                                # Both failed - connection is dead, exit message loop
                                raise Exception(f"WebRTC connection failed. State: {conn_state}, ICE: {ice_state}")

                except websockets.exceptions.ConnectionClosed as e:
                    log.warning(f"WebSocket connection closed: {e}")
                    # WebSocket can close after signaling is complete - connection can work without it
                    # Continue monitoring ICE state machine even if WebSocket is closed
                    if not answer_received:
                        raise Exception(f"WebSocket connection closed before SDP answer received: {e}")
                    # If answer was received, continue to monitoring loop below
                except Exception as e:
                    log.error(f"Error processing WebSocket messages: {e}")
                    raise

                # After message loop exits, continue monitoring ICE state machine
                # This matches Amazon reference: keep monitoring even after WebSocket message loop
                # The ICE state machine runs automatically in aiortc but needs the event loop to be active
                # to process STUN binding requests/responses during the "checking" phase.
                # By continuing to monitor and sleep, we keep the event loop running, allowing the
                # ICE state machine to complete its connectivity checks and transition to "connected"/"completed"
                log.info("WebSocket message loop ended, continuing to monitor ICE state machine...")
                if answer_received and not connection_established:
                    # Give ICE state machine time to complete connectivity checks
                    # The ICE state machine is running automatically - we just need to keep the event loop active
                    log.info("SDP answer received, waiting for ICE connectivity checks to complete...")
                    log.info("ICE state machine is running automatically - STUN binding requests/responses handled by aiortc")
                    max_wait_time = 30  # seconds - allow time for ICE connectivity checks
                    wait_start = time.time()
                    while (time.time() - wait_start) < max_wait_time:
                        conn_state = self.peer_connection.connectionState
                        ice_state = self.peer_connection.iceConnectionState

                        log.debug(f"ICE state machine: connectionState={conn_state}, iceConnectionState={ice_state}")

                        if conn_state == "connected" or (ice_state == "completed" and conn_state in ["connecting", "connected"]):
                            self.running = True
                            connection_established = True
                            log.info(f"Connection established! State: {conn_state}, ICE: {ice_state}")
                            break
                        elif conn_state == "failed" and ice_state == "failed":
                            raise Exception(f"WebRTC connection failed. State: {conn_state}, ICE: {ice_state}")

                        # Keep event loop running so ICE state machine can process STUN requests/responses
                        # This is critical - the ICE state machine needs the event loop to be active
                        # to handle STUN binding requests/responses automatically
                        await asyncio.sleep(0.5)

                    if not connection_established:
                        final_state = self.peer_connection.connectionState
                        final_ice = self.peer_connection.iceConnectionState
                        log.warning(f"ICE state machine did not complete within timeout. Final state: {final_state}, ICE: {final_ice}")
                        # Don't raise - let run() method handle it with frame consumption

                if connection_established:
                    log.info("Connection established successfully!")
                else:
                    log.info("Connection not fully established yet - will continue monitoring in run() method")

            log.info("Connected to KVS stream")

        except Exception as e:
            log.error(f"Failed to connect to KVS: {e}")
            raise

    async def run(self, duration: Optional[int] = None):
        """
        Run the streaming client.

        :param duration: Optional duration in seconds to stream
        :type duration: int | None
        """
        # Set up exception handler for unhandled exceptions in background tasks
        # TURN/STUN errors are often non-fatal if ICE connection succeeded
        def exception_handler(loop, context):
            """Handle unhandled exceptions in the event loop."""
            exception = context.get('exception')
            if exception:
                exception_type = type(exception).__name__
                exception_str = str(exception)

                # Suppress TURN/STUN errors if ICE connection is established
                if ('TransactionFailed' in exception_type or
                    'TURN' in exception_str or
                    'STUN' in exception_str or
                    'Forbidden IP' in exception_str or
                    '403' in exception_str):
                    if self.peer_connection and self.peer_connection.iceConnectionState in ['connected', 'completed']:
                        log.debug(f"Suppressing non-fatal TURN/STUN error (ICE connection established): {exception_type}")
                        return

                # Log other unhandled exceptions as warnings
                log.warning(f"Unhandled exception in event loop: {context.get('message', 'Unknown error')}")

        # Set exception handler for the event loop
        try:
            loop = asyncio.get_running_loop()
            loop.set_exception_handler(exception_handler)
        except RuntimeError:
            # If no running loop yet, we'll set it when we connect
            pass

        if not self.running:
            await self.connect()

            # Set exception handler after connection (in case loop wasn't available before)
            try:
                loop = asyncio.get_running_loop()
                loop.set_exception_handler(exception_handler)
            except RuntimeError:
                pass

        start_time = time.time()
        stats_interval = 2.0  # Print stats every 2 seconds
        last_stats_time = start_time

        # Start consuming frames as soon as ICE completes (matches Amazon reference)
        # STUN binding requests/responses are handled automatically by aiortc's ICE stack
        # Frame consumption keeps the connection alive and enables proper STUN responses
        # Note: connectionState might not transition to "connected" until media starts flowing
        log.info("Waiting for ICE connection to complete before consuming frames...")
        max_wait_for_ice = 30  # seconds
        wait_start = time.time()
        ice_completed = False

        while (time.time() - wait_start) < max_wait_for_ice:
            if self.peer_connection:
                conn_state = self.peer_connection.connectionState
                ice_state = self.peer_connection.iceConnectionState

                # Start frame consumption when ICE completes (matches Amazon reference behavior)
                # This keeps the connection alive and enables STUN binding responses
                if ice_state == "completed" or ice_state == "connected":
                    ice_completed = True
                    self.running = True
                    log.info(f"ICE connection {ice_state} - starting frame consumption (connection state: {conn_state})")
                    log.info("STUN binding requests/responses are handled automatically by aiortc ICE stack")
                    break
                elif conn_state == "connected":
                    # Connection fully established
                    ice_completed = True
                    self.running = True
                    log.info("Peer connection established (connected state) - starting frame consumption")
                    break
                elif conn_state == "failed" or ice_state == "failed":
                    raise Exception(f"Connection failed before ICE completion. State: {conn_state}, ICE: {ice_state}")

            await asyncio.sleep(0.2)

        if not ice_completed:
            if self.peer_connection:
                final_ice = self.peer_connection.iceConnectionState
                final_conn = self.peer_connection.connectionState
                raise Exception(f"ICE connection not completed within {max_wait_for_ice} seconds. ICE: {final_ice}, State: {final_conn}")
            else:
                raise Exception(f"Peer connection not available within {max_wait_for_ice} seconds")

        # Frame consumption is started as a concurrent task when ICE completes in connect() method
        # Both WebSocket message loop and frame consumption run concurrently (matches Amazon reference)
        # This ensures frames are consumed immediately while still receiving ICE candidates via WebSocket

        try:
            while self.running:
                if duration and (time.time() - start_time) >= duration:
                    log.info(f"Stream duration ({duration}s) reached, stopping...")
                    break

                # Print statistics periodically if not showing video
                if not self.show_video:
                    current_time = time.time()
                    if current_time - last_stats_time >= stats_interval:
                        stats_str = self.stats.get_stats_string()
                        print(stats_str, flush=True)
                        last_stats_time = current_time

                        if self.stats_callback:
                            self.stats_callback(self.stats)

                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            log.info("Stream interrupted by user")
        except Exception as e:
            log.error(f"Error during streaming: {e}")
            raise
        finally:
            # Cancel frame consumption task
            if frame_task and not frame_task.done():
                frame_task.cancel()
                try:
                    await frame_task
                except asyncio.CancelledError:
                    pass
            await self.stop()

    async def stop(self):
        """Stop the streaming client and cleanup."""
        log.info("Stopping KVS stream...")
        self.running = False

        if self.peer_connection:
            await self.peer_connection.close()

        if self.show_video and CV2_AVAILABLE:
            cv2.destroyAllWindows()

        if not self.show_video:
            # Print final statistics
            print()  # New line after stats
            print("Final Statistics:")
            print(self.stats.get_stats_string())

        log.info("KVS stream stopped")


async def start_kvs_streaming(credentials: AWSCredentials, channel_arn: str,
                              show_video: Optional[bool] = None,
                              save_path: Optional[str] = None,
                              duration: Optional[int] = None,
                              stats_only: bool = False):
    """
    Start KVS video streaming.

    :param credentials: AWS credentials for KVS
    :type credentials: AWSCredentials
    :param channel_arn: KVS channel ARN
    :type channel_arn: str
    :param show_video: Whether to show video (None = auto-detect)
    :type show_video: bool | None
    :param save_path: Optional path to save video
    :type save_path: str | None
    :param duration: Optional duration in seconds to stream
    :type duration: int | None
    :param stats_only: Force statistics mode even if video device available
    :type stats_only: bool

    :raises Exception: If streaming fails
    """
    if stats_only:
        show_video = False

    client = KVSStreamingClient(
        credentials=credentials,
        channel_arn=channel_arn,
        show_video=show_video,
        save_path=save_path
    )

    if client.show_video:
        print("Video display enabled. Press 'q' in the video window or Ctrl+C to stop.\n")
    else:
        print("Stats-only mode. Press Ctrl+C to stop streaming.\n")

    # Run streaming with Ctrl+C support.
    # asyncio.run() handles KeyboardInterrupt by cancelling all tasks.
    # We just need to ensure cleanup happens.
    try:
        await client.run(duration=duration)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nStopping stream...")
    except Exception as e:
        log.error(f"Streaming error: {e}")
    finally:
        try:
            await client.stop()
        except Exception:
            pass
