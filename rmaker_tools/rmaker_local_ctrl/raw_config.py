#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

"""
Raw Config Retrieval Module

This module handles retrieving node configuration via raw endpoints with
fragmentation support. The config data is split into 200-byte chunks and
reassembled by the client.

Protocol:
1. Client sends CmdGetConfig with offset=0 (and optional timestamp for signing)
2. Device returns first fragment with total length
3. Client continues requesting with increasing offsets until all data received
4. If timestamp provided, response is signed: {"node_payload": {...}, "signature": "..."}
"""

import asyncio
import json
import sys
import os

# Try to import protobuf module - generate if not available
try:
    from . import esp_rmaker_prov_local_ctrl_pb2 as local_ctrl_pb2
except ImportError:
    # Protobuf module not found - will need to be generated
    local_ctrl_pb2 = None

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
    """Get version/capabilities from proto-ver endpoint"""
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
    """Check if device supports local_ctrl capability in rmaker_extra.cap"""
    try:
        info = json.loads(version_response)
        if 'rmaker_extra' not in info:
            return False
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
            tp = Transport_BLE(
                service_uuid='0000ffff-0000-1000-8000-00805f9b34fb',
                nu_lookup={'get_params': 'ff54',  # Use available slot for params endpoint
                          'get_config': 'ff56'}   # Use available slot for config endpoint
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
        if isinstance(sec, Security0):
            return True

        if isinstance(sec, Security1) or isinstance(sec, Security2):
            response = None
            while True:
                request = sec.security_session(response)
                if request is None:
                    break
                response = await tp.send_data('prov-session', request)
                if response is None:
                    print("Failed to get response from prov-session endpoint")
                    return False
            return True
        return True
    except Exception as e:
        print(f"Error establishing session: {e}")
        return False


def create_get_data_request(data_type, offset, timestamp=None):
    """
    Create a protobuf request for get_data endpoint (params or config).

    :param data_type: 0 for params, 1 for config
    :param offset: Offset for chunking
    :param timestamp: Optional timestamp for signed response
    """
    if local_ctrl_pb2:
        # Use generated protobuf
        msg = local_ctrl_pb2.RMakerLocalCtrlPayload()
        msg.msg = local_ctrl_pb2.TypeCmdGetData
        # Set DataType enum: 0 for params, 1 for config
        if data_type == 0:
            msg.cmdGetData.DataType = local_ctrl_pb2.TypeParams
        else:
            msg.cmdGetData.DataType = local_ctrl_pb2.TypeConfig
        msg.cmdGetData.Offset = offset
        if timestamp is not None:
            msg.cmdGetData.Timestamp = timestamp
            msg.cmdGetData.HasTimestamp = True
        return msg.SerializeToString()
    else:
        # Manual protobuf construction (simplified)
        # This is a fallback - ideally the proto should be generated
        # Build CmdGetData message
        cmd_data = b''
        # Field 1: DataType (enum, wire type 0)
        cmd_data += bytes([0x08]) + _encode_varint(data_type)
        # Field 2: Offset (uint32, wire type 0)
        cmd_data += bytes([0x10]) + _encode_varint(offset)
        # Field 3: Timestamp (int64, wire type 0)
        if timestamp is not None:
            cmd_data += bytes([0x18]) + _encode_varint(timestamp)
            # Field 4: HasTimestamp (bool, wire type 0)
            cmd_data += bytes([0x20, 0x01])

        # Build RMakerLocalCtrlPayload
        payload = b''
        # Field 1: msg (enum, wire type 0) = TypeCmdGetData = 0
        payload += bytes([0x08, 0x00])
        # Field 10: cmdGetData (message, wire type 2)
        payload += bytes([0x52]) + _encode_varint(len(cmd_data)) + cmd_data

        return payload


def _encode_varint(value):
    """Encode an integer as a varint"""
    bits = value & 0x7f
    value >>= 7
    result = b''
    while value:
        result += bytes([(0x80 | bits)])
        bits = value & 0x7f
        value >>= 7
    result += bytes([bits])
    return result


def parse_get_data_response(data):
    """
    Parse a protobuf response from get_data endpoint (params or config).

    Returns: (status, offset, payload_bytes, total_len) or None on error
    """
    if local_ctrl_pb2:
        # Use generated protobuf
        try:
            msg = local_ctrl_pb2.RMakerLocalCtrlPayload()
            msg.ParseFromString(data)
            if msg.msg != local_ctrl_pb2.TypeRespGetData:
                print(f"Unexpected message type: {msg.msg}")
                return None
            resp = msg.respGetData
            return (resp.Status, resp.Buf.Offset, resp.Buf.Payload, resp.Buf.TotalLen)
        except Exception as e:
            print(f"Failed to parse protobuf response: {e}")
            return None
    else:
        # Manual protobuf parsing (simplified)
        # This handles the basic structure we expect
        try:
            return _parse_data_response_manual(data)
        except Exception as e:
            print(f"Failed to manually parse response: {e}")
            return None


def _parse_data_response_manual(data):
    """Manually parse the protobuf response"""
    idx = 0

    def read_varint():
        nonlocal idx
        result = 0
        shift = 0
        while True:
            if idx >= len(data):
                raise ValueError("Truncated varint")
            b = data[idx]
            idx += 1
            result |= (b & 0x7f) << shift
            if not (b & 0x80):
                break
            shift += 7
        return result

    def read_bytes_field():
        nonlocal idx
        length = read_varint()
        result = data[idx:idx + length]
        idx += length
        return result

    status = 0
    offset = 0
    payload = b''
    total_len = 0

    while idx < len(data):
        tag_wire = read_varint()
        field_num = tag_wire >> 3
        wire_type = tag_wire & 0x07

        if field_num == 1 and wire_type == 0:
            # msg (enum)
            msg_type = read_varint()
            if msg_type != 1:  # TypeRespGetData
                print(f"Unexpected message type: {msg_type}")
                return None
        elif field_num == 11 and wire_type == 2:
            # respGetData (message)
            resp_data = read_bytes_field()
            # Parse RespGetConfig
            resp_idx = 0

            def resp_read_varint():
                nonlocal resp_idx
                result = 0
                shift = 0
                while True:
                    if resp_idx >= len(resp_data):
                        raise ValueError("Truncated varint in response")
                    b = resp_data[resp_idx]
                    resp_idx += 1
                    result |= (b & 0x7f) << shift
                    if not (b & 0x80):
                        break
                    shift += 7
                return result

            def resp_read_bytes():
                nonlocal resp_idx
                length = resp_read_varint()
                result = resp_data[resp_idx:resp_idx + length]
                resp_idx += length
                return result

            while resp_idx < len(resp_data):
                resp_tag_wire = resp_read_varint()
                resp_field = resp_tag_wire >> 3
                resp_wire = resp_tag_wire & 0x07

                if resp_field == 1 and resp_wire == 0:
                    status = resp_read_varint()
                elif resp_field == 2 and resp_wire == 2:
                    # PayloadBuf
                    buf_data = resp_read_bytes()
                    buf_idx = 0

                    def buf_read_varint():
                        nonlocal buf_idx
                        result = 0
                        shift = 0
                        while True:
                            if buf_idx >= len(buf_data):
                                raise ValueError("Truncated varint in buf")
                            b = buf_data[buf_idx]
                            buf_idx += 1
                            result |= (b & 0x7f) << shift
                            if not (b & 0x80):
                                break
                            shift += 7
                        return result

                    def buf_read_bytes():
                        nonlocal buf_idx
                        length = buf_read_varint()
                        result = buf_data[buf_idx:buf_idx + length]
                        buf_idx += length
                        return result

                    while buf_idx < len(buf_data):
                        buf_tag_wire = buf_read_varint()
                        buf_field = buf_tag_wire >> 3
                        buf_wire = buf_tag_wire & 0x07

                        if buf_field == 1 and buf_wire == 0:
                            offset = buf_read_varint()
                        elif buf_field == 2 and buf_wire == 2:
                            payload = buf_read_bytes()
                        elif buf_field == 3 and buf_wire == 0:
                            total_len = buf_read_varint()
                        else:
                            # Skip unknown field
                            if buf_wire == 0:
                                buf_read_varint()
                            elif buf_wire == 2:
                                buf_read_bytes()
                else:
                    # Skip unknown field
                    if resp_wire == 0:
                        resp_read_varint()
                    elif resp_wire == 2:
                        resp_read_bytes()
        else:
            # Skip unknown field
            if wire_type == 0:
                read_varint()
            elif wire_type == 2:
                read_bytes_field()

    return (status, offset, payload, total_len)


async def get_raw_data(tp, data_type, security_ctx=None, timestamp=None):
    """
    Get node data (params or config) using raw get_data endpoint with fragmentation support.

    :param tp: Transport object
    :param data_type: 0 for params, 1 for config
    :param security_ctx: Security context for encryption/decryption
    :param timestamp: Optional timestamp for signed response
    :return: Complete data JSON string or None on error
    """
    try:
        data_buffer = b''
        offset = 0
        total_len = None
        endpoint_name = 'get_params' if data_type == 0 else 'get_config'

        while True:
            # Create request (returns bytes)
            request = create_get_data_request(
                data_type,
                offset,
                timestamp if offset == 0 else None  # Only send timestamp on first request
            )

            # Encrypt if security is enabled
            if security_ctx and not isinstance(security_ctx, Security0):
                request = security_ctx.encrypt_data(request)

            # Convert bytes to latin-1 string for transport layer
            # (transport will encode it back to bytes)
            if isinstance(request, bytes):
                request = request.decode('latin-1')

            # Send request
            response = await tp.send_data(endpoint_name, request)
            if not response:
                print("No response from device")
                return None

            # Decrypt if security is enabled
            if security_ctx and not isinstance(security_ctx, Security0):
                if isinstance(response, str):
                    response = response.encode('latin-1')
                response = security_ctx.decrypt_data(response)
                if response is None:
                    print("Failed to decrypt response")
                    return None

            # Ensure response is bytes
            if isinstance(response, str):
                response = response.encode('latin-1')

            # Parse response
            parsed = parse_get_data_response(response)
            if parsed is None:
                print("Failed to parse response")
                return None

            status, resp_offset, payload, resp_total_len = parsed

            if status != 0:  # Not Success
                print(f"Device returned error status: {status}")
                return None

            # Validate offset
            if resp_offset != offset:
                print(f"Offset mismatch: expected {offset}, got {resp_offset}")
                return None

            # Set total length from first response
            if total_len is None:
                total_len = resp_total_len
                data_name = "params" if data_type == 0 else "config"
                print(f"{data_name.capitalize()} total length: {total_len} bytes")

            # Append payload
            data_buffer += payload
            offset += len(payload)

            print(f"Received fragment: offset={resp_offset}, len={len(payload)}, progress={offset}/{total_len}")

            # Check if we have all data
            if offset >= total_len:
                break

        # Decode the complete data
        data_str = data_buffer.decode('utf-8')

        # Parse as JSON to validate
        try:
            data_json = json.loads(data_str)
            return data_json
        except json.JSONDecodeError as e:
            print(f"Warning: Data is not valid JSON: {e}")
            print(f"Raw data: {data_str[:200]}...")
            return data_str

    except Exception as e:
        data_name = "params" if data_type == 0 else "config"
        print(f"Error getting {data_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_raw_config_operation(nodeid, **kwargs):
    """
    Run raw config retrieval operation.

    :param nodeid: Node ID (used as service name for HTTP, or fallback for BLE)
    :param kwargs: Options including pop, transport, port, sec_ver, device_name, timestamp
    :return: Config dict/string or None on error
    """
    # Use the generic function with data_type=1 (config)
    return await run_raw_data_operation(nodeid, data_type=1, **kwargs)


def run_raw_config_sync(nodeid, **kwargs):
    """
    Synchronous wrapper for raw config retrieval.
    """
    try:
        return asyncio.run(run_raw_config_operation(nodeid, **kwargs))
    except Exception as e:
        print(f"Raw config sync wrapper failed: {e}")
        return None


async def run_raw_data_operation(nodeid, data_type, **kwargs):
    """
    Run raw data retrieval operation (params or config).

    :param nodeid: Node ID (used as service name for HTTP, or fallback for BLE)
    :param data_type: 0 for params, 1 for config
    :param kwargs: Options including pop, transport, port, sec_ver, device_name, timestamp
    :return: Data dict/string or None on error
    """
    pop = kwargs.get('pop', '')
    transport = kwargs.get('transport', 'ble')
    sec_ver = kwargs.get('sec_ver', 0)
    port = kwargs.get('port', None)
    device_name = kwargs.get('device_name', None)
    timestamp = kwargs.get('timestamp', None)
    endpoint_name = 'get_params' if data_type == 0 else 'get_config'
    data_name = 'params' if data_type == 0 else 'config'

    # Build service name
    if transport.lower() == 'ble':
        service_name = device_name if device_name else nodeid
    else:
        service_name = nodeid

    transport_obj = None
    try:
        # Establish transport
        transport_obj = await get_transport(transport, service_name, port)
        if transport_obj is None:
            print("Failed to establish transport")
            if transport.lower() == 'ble':
                print("Note: For BLE transport, ensure the device is in provisioning mode.")
            return None

        # Check capabilities
        version_response = await get_version(transport_obj)
        if not version_response:
            print("Error: Failed to retrieve device capabilities.")
            return None

        if not check_local_ctrl_capability(version_response):
            print("Error: Device does not support local control via raw endpoints.")
            print("Please ensure the device has CONFIG_ESP_RMAKER_ENABLE_PROV_LOCAL_CTRL enabled.")
            return None

        # Extract security version from proto-ver response
        actual_sec_ver = sec_ver
        sec_patch_ver = 0
        try:
            info = json.loads(version_response)
            if 'prov' in info and 'sec_ver' in info['prov']:
                actual_sec_ver = int(info['prov']['sec_ver'])
                sec_patch_ver = int(info['prov'].get('sec_patch_ver', 0))
                print(f"Auto-detected Security Scheme: {actual_sec_ver}")
            elif actual_sec_ver is None or actual_sec_ver == 0:
                prov_caps = info.get('prov', {}).get('cap', [])
                if 'no_sec' in prov_caps:
                    actual_sec_ver = 0
                else:
                    actual_sec_ver = 1
                print(f"Auto-detected Security Scheme: {actual_sec_ver} (from capabilities)")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Could not determine security version: {e}")
            if actual_sec_ver is None:
                actual_sec_ver = 1

        # Setup security
        security_obj = get_security(actual_sec_ver, sec_patch_ver, '', '', pop, False)
        if security_obj is None:
            print("Failed to setup security")
            return None

        # Establish session
        if not await establish_session(transport_obj, security_obj):
            print("Failed to establish session")
            return None

        # Get data with fragmentation
        data = await get_raw_data(transport_obj, data_type, security_obj, timestamp)
        return data

    except Exception as e:
        print(f"Raw {data_name} operation failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        try:
            if transport_obj:
                await transport_obj.disconnect()
        except:
            pass
