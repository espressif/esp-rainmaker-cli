#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

"""
On-network challenge-response user-node mapping for ESP RainMaker

This module provides functionality to discover devices on the local network
via mDNS and perform challenge-response authentication for user-node mapping.
"""

import os
import sys
from typing import Optional, Tuple, Dict, Any

try:
    from rmaker_lib.logger import log
except ImportError:
    import logging
    log = logging.getLogger(__name__)

# Import challenge-response functions
try:
    from . import challenge_response
except ImportError:
    current_dir = os.path.dirname(__file__)
    sys.path.insert(0, current_dir)
    import challenge_response

# Import transport and security
try:
    from ..common.transport.transport_http import Transport_HTTP
    from ..common.security.security0 import Security0
    from ..common.security.security1 import Security1
    from ..common.security.security2 import Security2
    from ..common.discovery.mdns_discovery import (
        discover_chal_resp_devices,
        discover_device_by_name,
        discover_device_by_ip,
        DeviceInfo,
        list_discovered_devices,
        select_device_interactive
    )
except ImportError:
    from rmaker_tools.common.transport.transport_http import Transport_HTTP
    from rmaker_tools.common.security.security0 import Security0
    from rmaker_tools.common.security.security1 import Security1
    from rmaker_tools.common.security.security2 import Security2
    from rmaker_tools.common.discovery.mdns_discovery import (
        discover_chal_resp_devices,
        discover_device_by_name,
        discover_device_by_ip,
        DeviceInfo,
        list_discovered_devices,
        select_device_interactive
    )


def get_security_for_device(device: DeviceInfo, pop: str = '',
                            sec2_username: str = '', sec2_password: str = '',
                            sec_ver_override: Optional[int] = None) -> Any:
    """
    Get appropriate security object based on device info

    :param device: Device information from discovery
    :param pop: Proof of Possession for Security 1
    :param sec2_username: Username for Security 2
    :param sec2_password: Password for Security 2
    :param sec_ver_override: Override security version from device info
    :return: Security object
    """
    sec_ver = sec_ver_override if sec_ver_override is not None else device.security_version

    if sec_ver == 0:
        log.info("Using Security 0 (no security)")
        return Security0(verbose=False)
    elif sec_ver == 1:
        log.info(f"Using Security 1 (POP required: {device.pop_required})")
        return Security1(pop, verbose=False)
    elif sec_ver == 2:
        log.info("Using Security 2")
        return Security2(sec_patch_ver=0, username=sec2_username,
                        password=sec2_password, verbose=False)
    else:
        log.warning(f"Unknown security version {sec_ver}, defaulting to Security 1")
        return Security1(pop, verbose=False)


def establish_http_session(device: DeviceInfo, security: Any) -> Tuple[Optional[Transport_HTTP], bool]:
    """
    Establish HTTP connection and security session with device

    :param device: Device information
    :param security: Security object
    :return: Tuple of (transport, success)
    """
    try:
        # Create HTTP transport
        if device.ip.find(':'):
            # IPv6 address
            hostname = f"[{device.ip}]:{device.port}"
        else:
            hostname = f"{device.ip}:{device.port}"
        log.info(f"Connecting to device at {hostname}")

        transport = Transport_HTTP(hostname, ssl_context=None)

        # Both on-network challenge-response and local control use the same
        # esp_local_ctrl/* endpoints for consistency
        session_endpoint = "esp_local_ctrl/session"

        log.info(f"Establishing security session via {session_endpoint}...")
        response = None
        while True:
            request = security.security_session(response)
            if request is None:
                break
            response = transport.send_data(session_endpoint, request)
            if response is None:
                log.error(f"Failed to establish security session via {session_endpoint}")
                return None, False

        log.info("Security session established")
        return transport, True

    except Exception as e:
        log.error(f"Failed to connect to device: {e}")
        return None, False


def send_challenge_via_http(transport: Transport_HTTP, security: Any,
                           challenge_str: str) -> Tuple[bool, Optional[str], Optional[bytes]]:
    """
    Send challenge to device via HTTP and get response

    :param transport: HTTP transport object
    :param security: Security object
    :param challenge_str: Challenge string from cloud
    :return: Tuple of (success, node_id, challenge_response_bytes)
    """
    return challenge_response.send_challenge_to_device(transport, security, challenge_str)


def perform_on_network_chal_resp_flow(device: DeviceInfo,
                                      session: Any,
                                      pop: str = '',
                                      sec2_username: str = '',
                                      sec2_password: str = '',
                                      sec_ver_override: Optional[int] = None,
                                      disable_on_success: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Perform complete on-network challenge-response flow for user-node mapping

    :param device: Device information from discovery
    :param session: Authenticated session object
    :param pop: Proof of Possession for Security 1
    :param sec2_username: Username for Security 2
    :param sec2_password: Password for Security 2
    :param sec_ver_override: Override security version from device info
    :param disable_on_success: If True, send disable command after successful mapping.
                               Default is True for on-network (device already provisioned).
    :return: Tuple of (success, node_id)
    """
    try:
        log.info(f"Starting on-network challenge-response flow for device: {device.ip}:{device.port}")

        # Step 1: Get security object
        security = get_security_for_device(device, pop, sec2_username, sec2_password, sec_ver_override)

        # Step 2: Establish HTTP connection and security session
        transport, success = establish_http_session(device, security)
        if not success or not transport:
            log.error("Failed to establish connection with device")
            return False, None

        # ch_resp endpoint is always "ch_resp" for both on-network and local control
        # (Local Control custom handlers are not prefixed with esp_local_ctrl/)
        chal_resp_endpoint = "ch_resp"

        # Step 3: Initiate challenge with cloud
        log.info("Initiating challenge with cloud...")
        success, challenge, request_id = challenge_response.initiate_challenge_mapping(session)
        if not success:
            log.error("Failed to initiate challenge with cloud")
            return False, None

        # Step 4: Send challenge to device and get response
        log.info("Sending challenge to device...")
        success, node_id, challenge_response_bytes = send_challenge_via_http(
            transport, security, challenge)
        if not success:
            # Error details already logged by send_challenge_via_http
            return False, None

        log.info(f"Received response from device, node_id: {node_id}")

        # Step 5: Verify response with cloud
        log.info("Verifying response with cloud...")
        success = challenge_response.verify_challenge_response(
            session, request_id, node_id, challenge_response_bytes)
        if not success:
            log.error("Cloud verification failed")
            return False, None

        log.info(f"On-network challenge-response completed successfully for node: {node_id}")

        # Step 6: Optionally disable challenge-response on device
        if disable_on_success:
            log.info("Disabling challenge-response on device...")
            disable_success = challenge_response.send_disable_chal_resp(
                transport, security, chal_resp_endpoint)
            if not disable_success:
                log.warning("Failed to disable challenge-response on device (mapping still succeeded)")
        else:
            log.debug("Skipping challenge-response disable (disable_on_success=False)")

        return True, node_id

    except Exception as e:
        log.error(f"On-network challenge-response flow failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def discover_and_map_device(session: Any,
                           pop: str = '',
                           sec2_username: str = '',
                           sec2_password: str = '',
                           device_name: Optional[str] = None,
                           device_ip: Optional[str] = None,
                           device_port: int = 80,
                           sec_ver_override: Optional[int] = None,
                           discovery_timeout: float = 5.0,
                           interactive: bool = True,
                           disable_on_success: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Discover devices via mDNS and perform challenge-response mapping

    :param session: Authenticated session object
    :param pop: Proof of Possession for Security 1
    :param sec2_username: Username for Security 2
    :param sec2_password: Password for Security 2
    :param device_name: Optional device name to filter by
    :param device_ip: Optional direct IP address (bypasses discovery)
    :param device_port: Port for direct IP connection
    :param sec_ver_override: Override security version
    :param discovery_timeout: mDNS discovery timeout
    :param interactive: Enable interactive device selection
    :param disable_on_success: If True, disable ch_resp on device after successful mapping
    :return: Tuple of (success, node_id)
    """
    try:
        device = None

        # Option 1: Direct IP connection (bypass mDNS)
        if device_ip:
            log.info(f"Using direct IP connection: {device_ip}:{device_port}")
            device = discover_device_by_ip(device_ip, device_port)
            # For direct IP, we may need to specify security version
            if sec_ver_override is None:
                log.warning("Security version not specified for direct IP connection, defaulting to 1")
                sec_ver_override = 1

        # Option 2: Discover by device name
        elif device_name:
            log.info(f"Searching for device: {device_name}")
            device = discover_device_by_name(device_name, timeout=discovery_timeout)
            if not device:
                log.error(f"Device '{device_name}' not found")
                return False, None

        # Option 3: Discover all devices
        else:
            log.info("Discovering devices on network...")
            devices = discover_chal_resp_devices(timeout=discovery_timeout)

            if not devices:
                log.error("No devices discovered on network")
                return False, None

            # Select device
            if interactive:
                device = select_device_interactive(devices)
                if not device:
                    log.info("Device selection cancelled")
                    return False, None
            else:
                # Auto-select first device
                device = devices[0]
                log.info(f"Auto-selected device: {device}")

        # Determine effective security version
        effective_sec_ver = sec_ver_override if sec_ver_override is not None else device.security_version

        # Interactive prompts for missing credentials
        if interactive:
            # Prompt for PoP if Security 1 and required but not provided
            if effective_sec_ver == 1 and device.pop_required and not pop:
                try:
                    pop = input("Enter Proof of Possession (PoP): ").strip()
                    if not pop:
                        log.error("PoP is required for this device")
                        return False, None
                except KeyboardInterrupt:
                    print()
                    return False, None

            # Prompt for Security 2 credentials if not provided
            if effective_sec_ver == 2:
                if not sec2_username:
                    try:
                        sec2_username = input("Enter Security 2 username: ").strip()
                    except KeyboardInterrupt:
                        print()
                        return False, None
                if not sec2_password:
                    try:
                        import getpass
                        sec2_password = getpass.getpass("Enter Security 2 password: ")
                    except KeyboardInterrupt:
                        print()
                        return False, None

        # Perform challenge-response flow
        return perform_on_network_chal_resp_flow(
            device=device,
            session=session,
            pop=pop,
            sec2_username=sec2_username,
            sec2_password=sec2_password,
            sec_ver_override=sec_ver_override,
            disable_on_success=disable_on_success
        )

    except ImportError as e:
        log.error(f"Missing dependency: {e}")
        log.error("Install required dependencies with: pip install zeroconf")
        return False, None
    except Exception as e:
        log.error(f"Discover and map failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def on_network_map_cli(vars: Dict[str, Any] = None) -> Tuple[bool, Optional[str]]:
    """
    CLI entry point for on-network challenge-response mapping

    :param vars: Dictionary containing CLI arguments
    :return: Tuple of (success, node_id)
    """
    if vars is None:
        vars = {}

    try:
        # Get session
        from rmaker_lib.profile_utils import get_session_with_profile
        session = get_session_with_profile(vars)

        # Extract parameters
        pop = vars.get('pop', '') or ''
        sec2_username = vars.get('sec2_username', '') or ''
        sec2_password = vars.get('sec2_password', '') or ''
        device_name = vars.get('device_name')
        device_ip = vars.get('device_ip')
        device_port = vars.get('device_port', 80) or 80
        sec_ver = vars.get('sec_ver')
        discovery_timeout = vars.get('discovery_timeout', 5.0) or 5.0
        interactive = vars.get('interactive', True)
        # Default to True for on-network transport
        disable_on_success = vars.get('disable_chal_resp', True)

        return discover_and_map_device(
            session=session,
            pop=pop,
            sec2_username=sec2_username,
            sec2_password=sec2_password,
            device_name=device_name,
            device_ip=device_ip,
            device_port=device_port,
            sec_ver_override=sec_ver,
            discovery_timeout=discovery_timeout,
            interactive=interactive,
            disable_on_success=disable_on_success
        )

    except Exception as e:
        log.error(f"On-network mapping failed: {e}")
        return False, None

