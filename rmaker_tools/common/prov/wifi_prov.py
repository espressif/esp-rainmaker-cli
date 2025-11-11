# SPDX-FileCopyrightText: 2018-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#
# APIs for interpreting and creating protobuf packets for Wi-Fi provisioning
import sys
import os

# Import proto - it should be available from the parent module (rmaker_local_ctrl or rmaker_prov)
try:
    import proto
except ImportError:
    # Try to find proto in parent modules
    current_file = os.path.abspath(__file__)
    # Go up to rmaker_tools
    rmaker_tools_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    for parent in ['rmaker_prov', 'rmaker_local_ctrl']:
        parent_dir = os.path.join(rmaker_tools_dir, parent)
        proto_path = os.path.join(parent_dir, 'proto')
        if os.path.exists(proto_path):
            # Add parent directory to path so proto can be imported as a module
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            try:
                import proto
                break
            except ImportError:
                continue
    else:
        raise ImportError("Could not find proto module")

from ..utils.convenience import str_to_bytes


def print_verbose(security_ctx, data):
    if (security_ctx.verbose):
        print(f'++++ {data} ++++')


def config_get_status_request(security_ctx):
    # Form protobuf request packet for GetStatus command
    cfg1 = proto.wifi_config_pb2.WiFiConfigPayload()
    cfg1.msg = proto.wifi_config_pb2.TypeCmdGetStatus
    cmd_get_status = proto.wifi_config_pb2.CmdGetStatus()
    cfg1.cmd_get_status.MergeFrom(cmd_get_status)
    encrypted_cfg = security_ctx.encrypt_data(cfg1.SerializeToString())
    print_verbose(security_ctx, f'Client -> Device (Encrypted CmdGetStatus): 0x{encrypted_cfg.hex()}')
    return encrypted_cfg.decode('latin-1')


def config_get_status_response(security_ctx, response_data):
    # Interpret protobuf response packet from GetStatus command
    decrypted_message = security_ctx.decrypt_data(str_to_bytes(response_data))
    cmd_resp1 = proto.wifi_config_pb2.WiFiConfigPayload()
    cmd_resp1.ParseFromString(decrypted_message)
    print_verbose(security_ctx, f'CmdGetStatus type: {str(cmd_resp1.msg)}')
    print_verbose(security_ctx, f'CmdGetStatus status: {str(cmd_resp1.resp_get_status.status)}')

    if cmd_resp1.resp_get_status.sta_state == 0:
        print('==== WiFi state: Connected ====')
        return 'connected'
    elif cmd_resp1.resp_get_status.sta_state == 1:
        print('++++ WiFi state: Connecting... ++++')
        # Check if attempt_failed field exists (may not be present in all protocol versions)
        try:
            if cmd_resp1.resp_get_status.HasField('attempt_failed'):
                if cmd_resp1.resp_get_status.attempt_failed.attempts_remaining:
                    print(cmd_resp1.resp_get_status)
                else:
                    print('attempt_failed {\n  attempts_remaining: 0\n}')
        except (AttributeError, ValueError):
            # Field doesn't exist in this protocol version, skip it
            pass
        return 'connecting'
    elif cmd_resp1.resp_get_status.sta_state == 2:
        print('---- WiFi state: Disconnected ----')
        return 'disconnected'
    elif cmd_resp1.resp_get_status.sta_state == 3:
        print('---- WiFi state: Connection Failed ----')
        if cmd_resp1.resp_get_status.fail_reason == 0:
            print('---- Failure reason: Incorrect Password ----')
        elif cmd_resp1.resp_get_status.fail_reason == 1:
            print('---- Failure reason: Incorrect SSID ----')
        return 'failed'
    return 'unknown'


def config_set_config_request(security_ctx, ssid, passphrase):
    # Form protobuf request packet for SetConfig command
    cmd = proto.wifi_config_pb2.WiFiConfigPayload()
    cmd.msg = proto.wifi_config_pb2.TypeCmdSetConfig
    cmd.cmd_set_config.ssid = str_to_bytes(ssid)
    cmd.cmd_set_config.passphrase = str_to_bytes(passphrase)
    enc_cmd = security_ctx.encrypt_data(cmd.SerializeToString())
    print_verbose(security_ctx, f'Client -> Device (SetConfig cmd): 0x{enc_cmd.hex()}')
    return enc_cmd.decode('latin-1')


def config_set_config_response(security_ctx, response_data):
    # Interpret protobuf response packet from SetConfig command
    decrypt = security_ctx.decrypt_data(str_to_bytes(response_data))
    cmd_resp4 = proto.wifi_config_pb2.WiFiConfigPayload()
    cmd_resp4.ParseFromString(decrypt)
    print_verbose(security_ctx, f'SetConfig status: 0x{str(cmd_resp4.resp_set_config.status)}')
    return cmd_resp4.resp_set_config.status


def config_apply_config_request(security_ctx):
    # Form protobuf request packet for ApplyConfig command
    cmd = proto.wifi_config_pb2.WiFiConfigPayload()
    cmd.msg = proto.wifi_config_pb2.TypeCmdApplyConfig
    enc_cmd = security_ctx.encrypt_data(cmd.SerializeToString())
    print_verbose(security_ctx, f'Client -> Device (ApplyConfig cmd): 0x{enc_cmd.hex()}')
    return enc_cmd.decode('latin-1')


def config_apply_config_response(security_ctx, response_data):
    # Interpret protobuf response packet from ApplyConfig command
    decrypt = security_ctx.decrypt_data(str_to_bytes(response_data))
    cmd_resp5 = proto.wifi_config_pb2.WiFiConfigPayload()
    cmd_resp5.ParseFromString(decrypt)
    print_verbose(security_ctx, f'ApplyConfig status: 0x{str(cmd_resp5.resp_apply_config.status)}')
    return cmd_resp5.resp_apply_config.status
