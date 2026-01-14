#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

"""
Challenge-Response based user-node association for ESP RainMaker
"""

import json
import requests
import time
import os
import sys
from rmaker_lib.logger import log

# Import protobuf module using absolute path
current_dir = os.path.dirname(__file__)
config_dir = os.path.join(current_dir, 'config')
sys.path.insert(0, config_dir)
import esp_rmaker_chal_resp_pb2

# Human-readable status messages
STATUS_MESSAGES = {
    0: "Success",
    1: "Fail",
    2: "InvalidParam",
    3: "Disabled - Challenge-response has been disabled on device",
}


def get_status_message(status_code):
    """Get human-readable message for status code"""
    return STATUS_MESSAGES.get(status_code, f"Unknown status ({status_code})")


def has_challenge_response_capability(version_response):
    """
    Check if device supports challenge-response capability

    :param version_response: Response from proto-ver endpoint
    :type version_response: str

    :return: True if device supports challenge-response
    :rtype: bool
    """
    try:
        info = json.loads(version_response)

        # Check for rmaker_extra top-level key
        if 'rmaker_extra' not in info:
            log.debug("Device does not support rmaker_extra capability")
            return False

        # Check for ch_resp capability in rmaker_extra.cap
        rmaker_caps = info.get('rmaker_extra', {}).get('cap', [])
        if 'ch_resp' not in rmaker_caps:
            log.debug("Device does not support ch_resp capability")
            return False

        log.info("Device supports challenge-response capability")
        return True

    except (json.JSONDecodeError, KeyError) as e:
        log.debug(f"Failed to parse version response for capabilities: {e}")
        return False


def send_challenge_to_device(transport, security, challenge_str):
    """
    Send challenge string to device via ch_resp endpoint

    :param transport: Transport object for communication
    :param security: Security object for encryption
    :param challenge_str: Challenge string from cloud API
    :type challenge_str: str

    :return: Tuple of (success, node_id, challenge_response_bytes)
    :rtype: tuple
    """
    try:
        log.info("Sending challenge to device...")

        # Encode challenge as UTF-8 bytes
        challenge_bytes = challenge_str.encode('utf-8')

        # Create command payload
        cmd_payload = esp_rmaker_chal_resp_pb2.CmdCRPayload()
        cmd_payload.payload = challenge_bytes

        # Create main message
        msg = esp_rmaker_chal_resp_pb2.RMakerChRespPayload()
        msg.msg = esp_rmaker_chal_resp_pb2.RMakerChRespMsgType.TypeCmdChallengeResponse
        msg.status = esp_rmaker_chal_resp_pb2.RMakerChRespStatus.Success
        msg.cmdChallengeResponsePayload.CopyFrom(cmd_payload)

        # Serialize and encrypt message
        serialized_msg = msg.SerializeToString()
        encrypted_msg = security.encrypt_data(serialized_msg)

        # Send to device
        response_data = transport.send_data('ch_resp', encrypted_msg.decode('latin-1'))
        if not response_data:
            log.error("No response from device for challenge")
            return False, None, None

        # Decrypt and parse response
        decrypted_data = security.decrypt_data(response_data.encode('latin-1'))
        resp_msg = esp_rmaker_chal_resp_pb2.RMakerChRespPayload()
        resp_msg.ParseFromString(decrypted_data)

        # Check response status
        if resp_msg.status != esp_rmaker_chal_resp_pb2.RMakerChRespStatus.Success:
            status_msg = get_status_message(resp_msg.status)
            log.error(f"Device returned error: {status_msg}")
            return False, None, None

        if resp_msg.msg != esp_rmaker_chal_resp_pb2.RMakerChRespMsgType.TypeRespChallengeResponse:
            log.error(f"Unexpected response message type: {resp_msg.msg}")
            return False, None, None

        # Extract response payload
        if not resp_msg.HasField('respChallengeResponsePayload'):
            log.error("No challenge response payload in device response")
            return False, None, None

        resp_payload = resp_msg.respChallengeResponsePayload
        node_id = resp_payload.node_id
        challenge_response_bytes = resp_payload.payload

        # Validate response length (should be 256 bytes for RSA-2048, but we don't enforce this)
        log.info(f"Received challenge response: {len(challenge_response_bytes)} bytes, node_id: {node_id}")

        return True, node_id, challenge_response_bytes

    except Exception as e:
        log.error(f"Failed to exchange challenge with device: {e}")
        return False, None, None


def initiate_challenge_mapping(session):
    """
    Call cloud API to initiate challenge-response mapping

    :param session: Authenticated session object
    :return: Tuple of (success, challenge_str, request_id)
    :rtype: tuple
    """
    try:
        log.info("Initiating challenge-response mapping with cloud...")

        # Get fresh token (will refresh if expired)
        # This ensures we always have a valid token even if it expired
        # between session creation and this API call
        try:
            id_token = session.config.get_access_token()
        except Exception:
            # Fallback to stored token if get_access_token fails
            id_token = session.id_token

        # Prepare request
        url = f"{session.config.get_host()}user/nodes/mapping/initiate"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': id_token
        }

        # Request body with timeout
        data = {"timeout": 360}  # 6 minutes timeout

        # Make API call
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse response
        resp_data = response.json()
        challenge = resp_data.get('challenge')
        request_id = resp_data.get('request_id')

        if not challenge or not request_id:
            log.error("Invalid response from mapping initiate API")
            return False, None, None

        log.info(f"Received challenge from cloud, request_id: {request_id}")
        return True, challenge, request_id

    except requests.exceptions.RequestException as e:
        log.error(f"Failed to initiate challenge mapping: {e}")
        return False, None, None
    except (json.JSONDecodeError, KeyError) as e:
        log.error(f"Invalid response format from mapping initiate: {e}")
        return False, None, None


def verify_challenge_response(session, request_id, node_id, challenge_response_bytes):
    """
    Verify challenge response with cloud API

    :param session: Authenticated session object
    :param request_id: Request ID from initiate call
    :type request_id: str
    :param node_id: Node ID from device
    :type node_id: str
    :param challenge_response_bytes: Binary challenge response from device
    :type challenge_response_bytes: bytes

    :return: True if verification successful
    :rtype: bool
    """
    try:
        log.info("Verifying challenge response with cloud...")

        # Get fresh token (will refresh if expired)
        # This ensures we always have a valid token even if it expired
        # between session creation and this API call
        try:
            id_token = session.config.get_access_token()
        except Exception:
            # Fallback to stored token if get_access_token fails
            id_token = session.id_token

        # Convert binary response to hex string (lowercase)
        challenge_response_hex = challenge_response_bytes.hex().lower()
        log.debug(f"Challenge response hex length: {len(challenge_response_hex)} chars")

        # Prepare request
        url = f"{session.config.get_host()}user/nodes/mapping/verify"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': id_token
        }

        # Request body
        data = {
            "request_id": request_id,
            "node_id": node_id,
            "challenge_response": challenge_response_hex
        }

        # Make API call
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()

        log.info("Challenge response verification successful")
        return True

    except requests.exceptions.RequestException as e:
        log.error(f"Failed to verify challenge response: {e}")
        return False
    except Exception as e:
        log.error(f"Error during challenge response verification: {e}")
        return False


def send_disable_chal_resp(transport, security, endpoint='ch_resp'):
    """
    Send disable command to device to disable challenge-response

    This should be called after successful user-node mapping to prevent
    further mapping attempts.

    :param transport: Transport object for communication
    :param security: Security object for encryption
    :param endpoint: Endpoint name (default: 'ch_resp', use 'esp_local_ctrl/ch_resp' for local ctrl)
    :return: True if disable was successful
    :rtype: bool
    """
    try:
        log.info("Sending disable challenge-response command to device...")

        # Create disable command message
        msg = esp_rmaker_chal_resp_pb2.RMakerChRespPayload()
        msg.msg = esp_rmaker_chal_resp_pb2.RMakerChRespMsgType.TypeCmdDisableChalResp
        msg.status = esp_rmaker_chal_resp_pb2.RMakerChRespStatus.Success
        # cmdDisableChalRespPayload is empty, just set the message type

        # Serialize and encrypt message
        serialized_msg = msg.SerializeToString()
        encrypted_msg = security.encrypt_data(serialized_msg)

        # Send to device
        response_data = transport.send_data(endpoint, encrypted_msg.decode('latin-1'))
        if not response_data:
            log.warning("No response from device for disable command")
            return False

        # Decrypt and parse response
        decrypted_data = security.decrypt_data(response_data.encode('latin-1'))
        resp_msg = esp_rmaker_chal_resp_pb2.RMakerChRespPayload()
        resp_msg.ParseFromString(decrypted_data)

        # Check response
        if resp_msg.msg != esp_rmaker_chal_resp_pb2.RMakerChRespMsgType.TypeRespDisableChalResp:
            log.warning(f"Unexpected response message type: {resp_msg.msg}")
            return False

        if resp_msg.status == esp_rmaker_chal_resp_pb2.RMakerChRespStatus.Success:
            log.info("Challenge-response disabled successfully on device")
            return True
        else:
            log.warning(f"Disable command returned status: {resp_msg.status}")
            return False

    except Exception as e:
        log.warning(f"Failed to send disable command: {e}")
        return False


def perform_challenge_response_flow(transport, security, session, endpoint='ch_resp',
                                    disable_on_success=False):
    """
    Perform complete challenge-response flow for user-node association

    :param transport: Transport object for device communication
    :param security: Security object for encryption
    :param session: Authenticated session object
    :param endpoint: Challenge-response endpoint (default: 'ch_resp')
    :param disable_on_success: If True, send disable command after successful mapping.
                               Default is False for BLE/SoftAP (allows retry if provisioning fails).
                               On-network flows typically set this to True.

    :return: Tuple of (success, node_id)
    :rtype: tuple
    """
    try:
        log.info("Starting challenge-response user-node association...")

        # Step 1: Initiate challenge with cloud
        success, challenge, request_id = initiate_challenge_mapping(session)
        if not success:
            return False, None

        # Step 2: Send challenge to device and get response
        success, node_id, challenge_response = send_challenge_to_device(
            transport, security, challenge)
        if not success:
            return False, None

        # Step 3: Verify response with cloud
        success = verify_challenge_response(session, request_id, node_id, challenge_response)
        if not success:
            return False, None

        log.info(f"Challenge-response flow completed successfully for node: {node_id}")

        # Step 4: Optionally disable challenge-response on device
        if disable_on_success:
            log.info("Disabling challenge-response on device...")
            disable_success = send_disable_chal_resp(transport, security, endpoint)
            if not disable_success:
                log.warning("Failed to disable challenge-response on device (mapping still succeeded)")
        else:
            log.debug("Skipping challenge-response disable (disable_on_success=False)")

        return True, node_id

    except Exception as e:
        log.error(f"Challenge-response flow failed: {e}")
        return False, None