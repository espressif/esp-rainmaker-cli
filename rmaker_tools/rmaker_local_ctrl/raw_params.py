#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import sys
import os

# Import from common shared modules
try:
    from ..common.transport.transport_ble import Transport_BLE
    from ..common.transport.transport_http import Transport_HTTP
    from ..common.security.security0 import Security0
    from ..common.security.security1 import Security1
    from ..common.security.security2 import Security2
except ImportError:
    # For standalone execution
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from rmaker_tools.common.transport.transport_ble import Transport_BLE
        from rmaker_tools.common.transport.transport_http import Transport_HTTP
        from rmaker_tools.common.security.security0 import Security0
        from rmaker_tools.common.security.security1 import Security1
        from rmaker_tools.common.security.security2 import Security2
    except ImportError:
        from transport.transport_ble import Transport_BLE
        from transport.transport_http import Transport_HTTP
        from security.security0 import Security0
        from security.security1 import Security1
        from security.security2 import Security2

def get_security(secver, sec_patch_ver, username, password, pop='', verbose=False):
    if secver == 2:
        return Security2(sec_patch_ver, username, password, verbose)
    if secver == 1:
        return Security1(pop, verbose)
    if secver == 0:
        return Security0(verbose)
    return None

async def get_version(tp):
    """
    Get version/capabilities from proto-ver endpoint
    """
    try:
        response = await tp.send_data('proto-ver', '---')
        if not response:
            return None
        if isinstance(response, bytes):
            response = response.decode('utf-8')
        return response
    except Exception as e:
        print(f"Error getting version: {e}")
        return None

def check_local_ctrl_capability(version_response):
    """
    Check if device supports local_ctrl capability in rmaker_extra.cap

    :param version_response: Response from proto-ver endpoint
    :type version_response: str

    :return: True if device supports local_ctrl, False otherwise
    :rtype: bool
    """
    try:
        info = json.loads(version_response)

        # Check for rmaker_extra top-level key
        if 'rmaker_extra' not in info:
            return False

        # Check for local_ctrl capability in rmaker_extra.cap
        rmaker_caps = info.get('rmaker_extra', {}).get('cap', [])
        if 'local_ctrl' not in rmaker_caps:
            return False

        return True

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Failed to parse version response for capabilities: {e}")
        return False

async def get_transport(sel_transport, service_name, port=None):
    try:
        if sel_transport == 'http':
            try:
                from ..common.transport.transport_http import Transport_HTTP
            except ImportError:
                from rmaker_tools.common.transport.transport_http import Transport_HTTP
            if port:
                service_name = f"{service_name}:{port}" if ':' not in service_name else service_name
            return Transport_HTTP(service_name, None)
        elif sel_transport == 'https':
            import ssl
            try:
                from ..common.transport.transport_http import Transport_HTTP
            except ImportError:
                from rmaker_tools.common.transport.transport_http import Transport_HTTP
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            if port:
                service_name = f"{service_name}:{port}" if ':' not in service_name else service_name
            return Transport_HTTP(service_name, ssl_ctx)
        elif sel_transport == 'ble':
            try:
                from ..common.transport.transport_ble import Transport_BLE
            except ImportError:
                from rmaker_tools.common.transport.transport_ble import Transport_BLE
            # For provisioning endpoints, use the provisioning service UUID
            # The endpoints will be auto-discovered from device advertisement/characteristics
            # We provide a fallback lookup in case auto-discovery fails
            tp = Transport_BLE(
                service_uuid='0000ffff-0000-1000-8000-00805f9b34fb',
                nu_lookup={'get_params': 'ff54',  # Use available slot in provisioning range
                          'set_params': 'ff55'}   # Use available slot in provisioning range
            )
            await tp.connect(devname=service_name)
            return tp
        return None
    except Exception as e:
        print(f"Error establishing transport: {e}")
        return None

async def establish_session(tp, sec):
    """Establish security session for provisioning transport"""
    try:
        # For raw endpoints, we may not need a session if security is 0
        if isinstance(sec, Security0):
            # Security0 doesn't need session establishment
            return True

        # For Security1/Security2, we need to establish session using prov-session endpoint
        # This follows the same pattern as provisioning: iterative handshake
        if isinstance(sec, Security1) or isinstance(sec, Security2):
            # Security1/Security2 use iterative handshake:
            # 1. Call security_session(None) to get initial request
            # 2. Send request to prov-session endpoint
            # 3. Call security_session(response) to process response and get next request
            # 4. Repeat until security_session returns None (session established)
            response = None
            while True:
                request = sec.security_session(response)
                if request is None:
                    # Session establishment complete
                    break

                # Send request to prov-session endpoint
                response = await tp.send_data('prov-session', request)
                if response is None:
                    print("Failed to get response from prov-session endpoint")
                    return False

            return True

        return True
    except Exception as e:
        print(f"Error establishing session: {e}")
        return False

async def sign_via_ch_resp(tp, security_ctx, challenge_str):
    """
    Sign a challenge string via ch_resp endpoint (challenge-response)

    :param tp: Transport object
    :param security_ctx: Security context (required)
    :param challenge_str: Challenge string to sign (JSON string)
    :return: Tuple of (success, signature_hex) where signature_hex is hex-encoded signature
    """
    try:
        # Import protobuf module
        import os
        import sys
        current_dir = os.path.dirname(__file__)
        config_dir = os.path.join(current_dir, '..', 'rmaker_prov', 'config')
        if config_dir not in sys.path:
            sys.path.insert(0, config_dir)
        import esp_rmaker_chal_resp_pb2

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

        # Encrypt the message using security context
        # Security0 doesn't encrypt, Security1/Security2 do
        if security_ctx and not isinstance(security_ctx, Security0):
            encrypted_bytes = security_ctx.encrypt_data(serialized_msg)
            encrypted_msg = encrypted_bytes.decode('latin-1') if isinstance(encrypted_bytes, bytes) else encrypted_bytes
        else:
            # Security0: send raw bytes as latin-1 string
            encrypted_msg = serialized_msg.decode('latin-1') if isinstance(serialized_msg, bytes) else serialized_msg

        # Send to device
        response_data = await tp.send_data('ch_resp', encrypted_msg)
        if not response_data:
            print("No response from device for challenge")
            return False, None

        # Decrypt and parse response
        if security_ctx and not isinstance(security_ctx, Security0):
            # Convert response to bytes for decryption
            if isinstance(response_data, bytes):
                response_bytes = response_data
            else:
                response_bytes = response_data.encode('latin-1')

            decrypted_data = security_ctx.decrypt_data(response_bytes)
            if decrypted_data is None:
                print("Failed to decrypt challenge response")
                return False, None
        else:
            # Security0: response is already decrypted, just convert to bytes
            decrypted_data = response_data.encode('latin-1') if isinstance(response_data, str) else response_data

        # Parse protobuf response
        resp_msg = esp_rmaker_chal_resp_pb2.RMakerChRespPayload()
        resp_msg.ParseFromString(decrypted_data)

        # Check response status
        if resp_msg.status != esp_rmaker_chal_resp_pb2.RMakerChRespStatus.Success:
            print(f"Device returned error status: {resp_msg.status}")
            return False, None

        if resp_msg.msg != esp_rmaker_chal_resp_pb2.RMakerChRespMsgType.TypeRespChallengeResponse:
            print(f"Unexpected response message type: {resp_msg.msg}")
            return False, None

        # Extract response payload
        if not resp_msg.HasField('respChallengeResponsePayload'):
            print("No challenge response payload in device response")
            return False, None

        resp_payload = resp_msg.respChallengeResponsePayload
        challenge_response_bytes = resp_payload.payload

        # Convert binary signature to hex (lowercase, matching backend expectation)
        signature_hex = challenge_response_bytes.hex().lower()

        print(f"Received signature from ch_resp endpoint: {len(signature_hex)} hex chars ({len(challenge_response_bytes)} bytes)")
        return True, signature_hex

    except Exception as e:
        print(f"Error signing via ch_resp endpoint: {e}")
        import traceback
        traceback.print_exc()
        return False, None

async def get_raw_params(tp, security_ctx=None, timestamp=None):
    """
    Get params using raw get_params endpoint with fragmentation support.

    :param tp: Transport object
    :param security_ctx: Security context (optional)
    :param timestamp: Optional timestamp to include in request (for signed response)
    """
    # Use the generic get_raw_data function with data_type=0 (params)
    from .raw_config import get_raw_data
    return await get_raw_data(tp, data_type=0, security_ctx=security_ctx, timestamp=timestamp)

async def set_raw_params(tp, new_params, security_ctx=None):
    """
    Set params using raw set_params endpoint
    """
    try:
        # Convert params to JSON string
        if isinstance(new_params, dict):
            params_json = json.dumps(new_params)
        elif isinstance(new_params, str):
            params_json = new_params
        else:
            print(f"Invalid params format: {type(new_params)}")
            return {'status': 'error', 'message': f'Invalid params format: {type(new_params)}'}

        # For Security1/Security2, encrypt the request
        if security_ctx and not isinstance(security_ctx, Security0):
            # Encrypt the request using security context (encrypt_data expects bytes)
            # Decode to latin-1 string for transport layer (which will re-encode it)
            encrypted_bytes = security_ctx.encrypt_data(params_json.encode('utf-8'))
            request = encrypted_bytes.decode('latin-1') if isinstance(encrypted_bytes, bytes) else encrypted_bytes
        else:
            request = params_json

        # Send JSON to set_params endpoint
        response = await tp.send_data('set_params', request)
        if not response:
            return {'status': 'error', 'message': 'No response from device'}

        # Decrypt response if security is enabled
        if security_ctx and not isinstance(security_ctx, Security0):
            # BLE transport returns string, but encrypted data is binary
            # Convert string back to bytes using latin-1 (1:1 mapping) before decrypting
            if isinstance(response, bytes):
                response_bytes = response
            else:
                response_bytes = response.encode('latin-1')

            decrypted = security_ctx.decrypt_data(response_bytes)
            if decrypted is None:
                print("Failed to decrypt response")
                return {'status': 'error', 'message': 'Failed to decrypt response'}

            # Decode decrypted bytes as UTF-8
            if isinstance(decrypted, bytes):
                response = decrypted.decode('utf-8')
            else:
                response = str(decrypted)
        else:
            # Parse response
            if isinstance(response, bytes):
                response = response.decode('utf-8')
            elif not isinstance(response, str):
                response = str(response)

        # Parse JSON response and return it (caller can check status)
        try:
            response_json = json.loads(response)
            # Return the parsed JSON response
            return response_json
        except json.JSONDecodeError:
            # Fallback: if not JSON, wrap it but preserve raw response
            response_str = response.strip()
            # Return as dict with status for consistency, but include raw response
            if response_str.upper() == 'OK':
                return {'status': 'success', 'message': 'OK', 'raw_response': response_str}
            return {
                'status': 'success' if len(response_str) > 0 else 'error',
                'message': response_str,
                'raw_response': response_str  # Include raw response for debugging
            }
    except Exception as e:
        print(f"Error setting params: {e}")
        return {'status': 'error', 'message': str(e)}

async def run_raw_params_operation(nodeid, operation, data=None, **kwargs):
    """
    Run local control operation using raw endpoints (get_params/set_params)
    """
    # Extract options with defaults
    pop = kwargs.get('pop', '')
    transport = kwargs.get('transport', 'ble')
    sec_ver = kwargs.get('sec_ver', 0)  # Default to 0 for raw endpoints
    port = kwargs.get('port', None)
    device_name = kwargs.get('device_name', None)

    # Build service name
    # For BLE transport, prefer device_name if provided, otherwise fallback to nodeid
    # (fallback allows for future firmware that might advertise with node IDs)
    # For HTTP/HTTPS transport, use nodeid (with .local suffix if needed)
    if transport.lower() == 'ble':
        service_name = device_name if device_name else nodeid
    else:
        service_name = nodeid

    transport_obj = None
    try:
        # Establish transport
        # Note: For BLE transport, the endpoints are only available during active provisioning
        # The device must be in provisioning mode (not yet provisioned, or provisioning restarted)
        transport_obj = await get_transport(transport, service_name, port)
        if transport_obj is None:
            print("Failed to establish transport")
            if transport.lower() == 'ble':
                print("Note: For BLE transport, ensure the device is in provisioning mode.")
                print("The get_params/set_params endpoints are only available during active provisioning.")
            return None

        # Check capabilities before proceeding
        version_response = await get_version(transport_obj)
        if not version_response:
            print("Error: Failed to retrieve device capabilities. Device may not support local control via raw endpoints.")
            return None

        if not check_local_ctrl_capability(version_response):
            print("Error: Device does not support local control via raw endpoints (local_ctrl capability not found).")
            print("Please ensure the device has CONFIG_ESP_RMAKER_ENABLE_PROV_LOCAL_CTRL enabled.")
            return None

        # Extract security version from proto-ver response
        # The capabilities object indicates security version
        actual_sec_ver = sec_ver
        sec_patch_ver = 0
        try:
            info = json.loads(version_response)
            # Check prov.sec_ver field
            if 'prov' in info and 'sec_ver' in info['prov']:
                actual_sec_ver = int(info['prov']['sec_ver'])
                sec_patch_ver = int(info['prov'].get('sec_patch_ver', 0))
                print(f"Auto-detected Security Scheme: {actual_sec_ver}")
            elif actual_sec_ver is None or actual_sec_ver == 0:
                # Fallback: check for no_sec capability
                prov_caps = info.get('prov', {}).get('cap', [])
                if 'no_sec' in prov_caps:
                    actual_sec_ver = 0
                else:
                    actual_sec_ver = 1  # Default to Security 1
                print(f"Auto-detected Security Scheme: {actual_sec_ver} (from capabilities)")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Could not determine security version from capabilities: {e}")
            if actual_sec_ver is None:
                actual_sec_ver = 1  # Default to Security 1

        # Setup security using detected/configured version
        security_obj = get_security(actual_sec_ver, sec_patch_ver, '', '', pop, False)
        if security_obj is None:
            print("Failed to setup security")
            return None

        # Establish session (required for Security1/Security2)
        # Once secure session is established, the get/set params endpoint can be used
        if not await establish_session(transport_obj, security_obj):
            print("Failed to establish session")
            return None

        # Execute operation
        if operation == 'get_params':
            timestamp = kwargs.get('timestamp', None)
            proxy_report = kwargs.get('proxy_report', False)

            # For proxy_report, we need to get params WITHOUT timestamp first,
            # then sign via ch_resp endpoint
            # BUT: if timestamp is explicitly provided (not None), use original flow (send timestamp to node)
            if proxy_report and timestamp is None:
                print("Proxy-report mode: Getting params without timestamp...")
                # Get params without timestamp (using protobuf chunking)
                params = await get_raw_params(transport_obj, security_obj, None)
                if params is None:
                    print("Failed to get params from device")
                    return None

                print(f"Received params: {json.dumps(params, indent=2)}")

                # Create node_payload locally
                import time
                current_timestamp = timestamp if timestamp is not None else int(time.time())
                print(f"Using timestamp: {current_timestamp}")

                node_payload = {
                    "data": params,
                    "timestamp": current_timestamp
                }

                # Create compact JSON (matching backend script)
                challenge_str = json.dumps(node_payload, separators=(',', ':'))
                print(f"Challenge string to sign (length {len(challenge_str)}): {challenge_str}")

                # Sign via ch_resp endpoint
                print("Sending challenge to ch_resp endpoint for signing...")
                success, signature_hex = await sign_via_ch_resp(transport_obj, security_obj, challenge_str)
                if not success:
                    print("Failed to get signature from ch_resp endpoint")
                    return None

                print(f"Received signature (hex, length {len(signature_hex)}): {signature_hex[:100]}...")

                # Create final response with node_payload as a JSON string
                final_response = {
                    "node_payload": challenge_str,
                    "signature": signature_hex
                }
                print("Created final response with node_payload as string and signature")
                return final_response
            else:
                # Normal flow - get params with optional timestamp (using protobuf chunking)
                params = await get_raw_params(transport_obj, security_obj, timestamp)
                return params
        elif operation == 'set_params':
            result = await set_raw_params(transport_obj, data, security_obj)
            return result
        else:
            print(f"Unknown operation: {operation}")
            return None

    except Exception as e:
        print(f"Local control via raw endpoints operation failed: {e}")
        return None
    finally:
        # Disconnect transport
        try:
            if transport_obj:
                await transport_obj.disconnect()
        except:
            pass

def run_raw_params_sync(nodeid, operation, data=None, **kwargs):
    """
    Synchronous wrapper for raw params operations
    """
    try:
        return asyncio.run(run_raw_params_operation(nodeid, operation, data, **kwargs))
    except Exception as e:
        print(f"Raw params sync wrapper failed: {e}")
        return None
