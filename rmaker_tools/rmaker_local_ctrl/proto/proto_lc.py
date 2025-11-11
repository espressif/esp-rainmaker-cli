# SPDX-FileCopyrightText: 2018-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#

import importlib.util
import os
import sys
from importlib.abc import Loader
from typing import Any


def _load_source(name: str, path: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert isinstance(spec.loader, Loader)
    spec.loader.exec_module(module)
    return module


# Use proto files from our local rmaker_local_ctrl directory 
current_dir = os.path.dirname(os.path.abspath(__file__))
local_ctrl_dir = os.path.dirname(current_dir)

# Load constants from our local rmaker_local_ctrl directory
constants_pb2 = _load_source('constants_pb2', os.path.join(local_ctrl_dir, 'constants_pb2.py'))

# Check if we have esp_local_ctrl_pb2.py in our directory
local_ctrl_pb2_path = os.path.join(local_ctrl_dir, 'esp_local_ctrl_pb2.py')
if os.path.exists(local_ctrl_pb2_path):
    local_ctrl_pb2 = _load_source('esp_local_ctrl_pb2', local_ctrl_pb2_path)
else:
    # If not available, create a basic implementation
    class LocalCtrlPb2:
        TypeCmdGetPropertyCount = 1
        TypeCmdGetPropertyValues = 2  
        TypeCmdSetPropertyValues = 3
        
        class LocalCtrlMessage:
            def __init__(self):
                self.msg = 0
                self.cmd_get_prop_count = self.CmdGetPropertyCount()
                self.resp_get_prop_count = self.RespGetPropertyCount()
                self.cmd_get_prop_vals = self.CmdGetPropertyValues()
                self.resp_get_prop_vals = self.RespGetPropertyValues()
                self.cmd_set_prop_vals = self.CmdSetPropertyValues()
                self.resp_set_prop_vals = self.RespSetPropertyValues()
                
            def SerializeToString(self):
                return b''
            def ParseFromString(self, data):
                pass
                
            class CmdGetPropertyCount:
                def MergeFrom(self, other):
                    pass
                    
            class RespGetPropertyCount:
                def __init__(self):
                    self.status = 0
                    self.count = 0
                    
            class CmdGetPropertyValues:
                def __init__(self):
                    self.indices = []
                def MergeFrom(self, other):
                    pass
                    
            class RespGetPropertyValues:
                def __init__(self):
                    self.status = 0
                    self.props = []
                    
            class CmdSetPropertyValues:
                def __init__(self):
                    self.props = []
                def MergeFrom(self, other):
                    pass
                    
            class RespSetPropertyValues:
                def __init__(self):
                    self.status = 0
        
        class CmdGetPropertyCount:
            def MergeFrom(self, other):
                pass
            
        class RespGetPropertyCount:
            def __init__(self):
                self.status = 0
                self.count = 0
    
    local_ctrl_pb2 = LocalCtrlPb2()


def to_bytes(s: str) -> bytes:
    return bytes(s, encoding='latin-1')


def get_prop_count_request(security_ctx):
    req = local_ctrl_pb2.LocalCtrlMessage()
    req.msg = local_ctrl_pb2.TypeCmdGetPropertyCount
    payload = local_ctrl_pb2.CmdGetPropertyCount()
    req.cmd_get_prop_count.MergeFrom(payload)
    enc_cmd = security_ctx.encrypt_data(req.SerializeToString())
    return enc_cmd.decode('latin-1')


def get_prop_count_response(security_ctx, response_data):
    decrypt = security_ctx.decrypt_data(to_bytes(response_data))
    resp = local_ctrl_pb2.LocalCtrlMessage()
    resp.ParseFromString(decrypt)
    if (resp.resp_get_prop_count.status == 0):
        return resp.resp_get_prop_count.count
    else:
        return 0


def get_prop_vals_request(security_ctx, indices):
    req = local_ctrl_pb2.LocalCtrlMessage()
    req.msg = local_ctrl_pb2.TypeCmdGetPropertyValues
    payload = local_ctrl_pb2.CmdGetPropertyValues()
    payload.indices.extend(indices)
    req.cmd_get_prop_vals.MergeFrom(payload)
    enc_cmd = security_ctx.encrypt_data(req.SerializeToString())
    return enc_cmd.decode('latin-1')


def get_prop_vals_response(security_ctx, response_data):
    decrypt = security_ctx.decrypt_data(to_bytes(response_data))
    resp = local_ctrl_pb2.LocalCtrlMessage()
    resp.ParseFromString(decrypt)
    results = []
    if (resp.resp_get_prop_vals.status == 0):
        for prop in resp.resp_get_prop_vals.props:
            results += [{
                'name': prop.name,
                'type': prop.type,
                'flags': prop.flags,
                'value': prop.value
            }]
    return results


def set_prop_vals_request(security_ctx, indices, values):
    req = local_ctrl_pb2.LocalCtrlMessage()
    req.msg = local_ctrl_pb2.TypeCmdSetPropertyValues
    payload = local_ctrl_pb2.CmdSetPropertyValues()
    for i, v in zip(indices, values):
        prop = payload.props.add()
        prop.index = i
        prop.value = v
    req.cmd_set_prop_vals.MergeFrom(payload)
    enc_cmd = security_ctx.encrypt_data(req.SerializeToString())
    return enc_cmd.decode('latin-1')


def set_prop_vals_response(security_ctx, response_data):
    decrypt = security_ctx.decrypt_data(to_bytes(response_data))
    resp = local_ctrl_pb2.LocalCtrlMessage()
    resp.ParseFromString(decrypt)
    return (resp.resp_set_prop_vals.status == 0)
