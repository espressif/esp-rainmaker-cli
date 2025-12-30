# SPDX-FileCopyrightText: 2018-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

"""Protobuf helpers for Wi-Fi control (prov-ctrl) endpoint."""

import os
import sys

# Import proto similar to other provisioning helpers so this works for
# both pip-installed packages and repo checkouts.
try:
    import proto  # type: ignore
except ImportError:  # pragma: no cover - fallback for editable installs
    current_file = os.path.abspath(__file__)
    rmaker_tools_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    for parent in ('rmaker_prov', 'rmaker_local_ctrl'):
        parent_dir = os.path.join(rmaker_tools_dir, parent)
        proto_path = os.path.join(parent_dir, 'proto')
        if os.path.exists(proto_path):
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            try:
                import proto  # type: ignore
                break
            except ImportError:
                continue
    else:
        raise ImportError('Could not locate proto module for wifi_ctrl helpers')

from ..utils.convenience import str_to_bytes


def print_verbose(security_ctx, data: str) -> None:
    if getattr(security_ctx, 'verbose', False):
        print(f'++++ {data} ++++')


def _make_ctrl_payload(msg_type):
    payload = proto.wifi_ctrl_pb2.WiFiCtrlPayload()
    payload.msg = msg_type
    # Set the appropriate oneof field based on message type
    # This makes the message structure explicit and unambiguous
    if msg_type == proto.wifi_ctrl_pb2.TypeCmdCtrlReset:
        payload.cmd_ctrl_reset.CopyFrom(proto.wifi_ctrl_pb2.CmdCtrlReset())
    elif msg_type == proto.wifi_ctrl_pb2.TypeRespCtrlReset:
        payload.resp_ctrl_reset.CopyFrom(proto.wifi_ctrl_pb2.RespCtrlReset())
    elif msg_type == proto.wifi_ctrl_pb2.TypeCmdCtrlReprov:
        payload.cmd_ctrl_reprov.CopyFrom(proto.wifi_ctrl_pb2.CmdCtrlReprov())
    elif msg_type == proto.wifi_ctrl_pb2.TypeRespCtrlReprov:
        payload.resp_ctrl_reprov.CopyFrom(proto.wifi_ctrl_pb2.RespCtrlReprov())
    return payload


def ctrl_reset_request(security_ctx):
    """Build encrypted CmdCtrlReset payload."""
    cmd = _make_ctrl_payload(proto.wifi_ctrl_pb2.TypeCmdCtrlReset)
    enc_cmd = security_ctx.encrypt_data(cmd.SerializeToString())
    print_verbose(security_ctx, f'Client -> Device (CmdCtrlReset): 0x{enc_cmd.hex()}')
    return enc_cmd.decode('latin-1')


def ctrl_reset_response(security_ctx, response_data):
    """Parse response for CmdCtrlReset and raise on failure."""
    dec_resp = security_ctx.decrypt_data(str_to_bytes(response_data))
    resp = proto.wifi_ctrl_pb2.WiFiCtrlPayload()
    resp.ParseFromString(dec_resp)
    print_verbose(security_ctx, f'CtrlReset status: 0x{resp.status}')
    if resp.msg != proto.wifi_ctrl_pb2.TypeRespCtrlReset or resp.status != 0:
        raise RuntimeError('CtrlReset failed')


def ctrl_reprov_request(security_ctx):
    """Build encrypted CmdCtrlReprov payload."""
    cmd = _make_ctrl_payload(proto.wifi_ctrl_pb2.TypeCmdCtrlReprov)
    enc_cmd = security_ctx.encrypt_data(cmd.SerializeToString())
    print_verbose(security_ctx, f'Client -> Device (CmdCtrlReprov): 0x{enc_cmd.hex()}')
    return enc_cmd.decode('latin-1')


def ctrl_reprov_response(security_ctx, response_data):
    """Parse response for CmdCtrlReprov and raise on failure."""
    dec_resp = security_ctx.decrypt_data(str_to_bytes(response_data))
    resp = proto.wifi_ctrl_pb2.WiFiCtrlPayload()
    resp.ParseFromString(dec_resp)
    print_verbose(security_ctx, f'CtrlReprov status: 0x{resp.status}')
    if resp.msg != proto.wifi_ctrl_pb2.TypeRespCtrlReprov or resp.status != 0:
        raise RuntimeError('CtrlReprov failed')
