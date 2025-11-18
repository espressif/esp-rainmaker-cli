# Copyright 2020 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# APIs for interpreting and creating protobuf packets for `custom-config` protocomm endpoint

from __future__ import print_function
from future.utils import tobytes
import sys
import os
prov_path = os.path.join(os.path.dirname(__file__),"../")
sys.path.insert(0, prov_path)

try:
    import utils
    # Check if str_to_hexstr is available, if not add it
    if not hasattr(utils, 'str_to_hexstr'):
        def str_to_hexstr(string):
            return ''.join('{:02x}'.format(ord(c)) for c in string)
        utils.str_to_hexstr = str_to_hexstr
except ImportError:
    # Create minimal utils module with required functions
    class UtilsModule:
        @staticmethod
        def str_to_hexstr(string):
            return ''.join('{:02x}'.format(ord(c)) for c in string)
    utils = UtilsModule()

# Import proto module and custom_cloud_config_pb2 directly
try:
    import proto
    # If proto doesn't have custom_cloud_config_pb2, load it directly
    if not hasattr(proto, 'custom_cloud_config_pb2'):
        import importlib.util
        custom_config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'custom_cloud_config_pb2.py')
        spec = importlib.util.spec_from_file_location("custom_cloud_config_pb2", custom_config_path)
        custom_cloud_config_pb2 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(custom_cloud_config_pb2)
        # Add it to the proto module
        proto.custom_cloud_config_pb2 = custom_cloud_config_pb2
except ImportError:
    # Fallback: create a minimal proto-like object
    class ProtoModule:
        pass
    proto = ProtoModule()
    
    # Load custom_cloud_config_pb2 directly
    import importlib.util
    custom_config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'custom_cloud_config_pb2.py')
    spec = importlib.util.spec_from_file_location("custom_cloud_config_pb2", custom_config_path)
    custom_cloud_config_pb2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(custom_cloud_config_pb2)
    proto.custom_cloud_config_pb2 = custom_cloud_config_pb2


def print_verbose(security_ctx, data):
    if (security_ctx.verbose):
        print("++++ " + data + " ++++")


def custom_cloud_config_request(security_ctx, userid, secretkey):
    # Form protobuf request packet from custom-config data
    # Try to use the newer RainMaker proto first, fallback to old one
    try:
        if hasattr(proto, 'esp_rmaker_user_mapping_pb2'):
            cmd = proto.esp_rmaker_user_mapping_pb2.RMakerConfigPayload()
            cmd.msg = proto.esp_rmaker_user_mapping_pb2.TypeCmdSetUserMapping
            cmd.cmd_set_user_mapping.UserID = userid
            cmd.cmd_set_user_mapping.SecretKey = secretkey
        else:
            # Fallback to old proto
            cmd = proto.custom_cloud_config_pb2.CloudConfigPayload()
            cmd.msg = proto.custom_cloud_config_pb2.TypeCmdGetSetDetails
            cmd.cmd_get_set_details.UserID = tobytes(userid)
            cmd.cmd_get_set_details.SecretKey = tobytes(secretkey)
    except:
        # Final fallback to old proto
        cmd = proto.custom_cloud_config_pb2.CloudConfigPayload()
        cmd.msg = proto.custom_cloud_config_pb2.TypeCmdGetSetDetails
        cmd.cmd_get_set_details.UserID = tobytes(userid)
        cmd.cmd_get_set_details.SecretKey = tobytes(secretkey)

    enc_cmd = security_ctx.encrypt_data(cmd.SerializeToString()).decode('latin-1')
    print_verbose(security_ctx, "Client -> Device (CustomConfig cmd) " + utils.str_to_hexstr(enc_cmd))
    return enc_cmd

def custom_cloud_config_response(security_ctx, response_data):
    # Interpret protobuf response packet
    decrypt = security_ctx.decrypt_data(tobytes(response_data))
    
    # Try to use the newer RainMaker proto first, fallback to old one
    try:
        if hasattr(proto, 'esp_rmaker_user_mapping_pb2'):
            cmd_resp = proto.esp_rmaker_user_mapping_pb2.RMakerConfigPayload()
            cmd_resp.ParseFromString(decrypt)
            print_verbose(security_ctx, "RMakerConfig msg value " + str(cmd_resp.msg))
            print_verbose(security_ctx, "RMakerConfig Status " + str(cmd_resp.resp_set_user_mapping.Status))
            print_verbose(security_ctx, "RMakerConfig Node ID " + str(cmd_resp.resp_set_user_mapping.NodeId))
            return cmd_resp.resp_set_user_mapping.Status, cmd_resp.resp_set_user_mapping.NodeId
        else:
            # Fallback to old proto
            cmd_resp = proto.custom_cloud_config_pb2.CloudConfigPayload()
            cmd_resp.ParseFromString(decrypt)
            print_verbose(security_ctx, "CustomConfig msg value " + str(cmd_resp.msg))
            print_verbose(security_ctx, "CustomConfig Status " + str(cmd_resp.resp_get_set_details.Status))
            print_verbose(security_ctx, "CustomConfig Device Secret " + str(cmd_resp.resp_get_set_details.DeviceSecret))
            return cmd_resp.resp_get_set_details.Status, cmd_resp.resp_get_set_details.DeviceSecret
    except:
        # Final fallback to old proto
        cmd_resp = proto.custom_cloud_config_pb2.CloudConfigPayload()
        cmd_resp.ParseFromString(decrypt)
        print_verbose(security_ctx, "CustomConfig msg value " + str(cmd_resp.msg))
        print_verbose(security_ctx, "CustomConfig Status " + str(cmd_resp.resp_get_set_details.Status))
        print_verbose(security_ctx, "CustomConfig Device Secret " + str(cmd_resp.resp_get_set_details.DeviceSecret))
        return cmd_resp.resp_get_set_details.Status, cmd_resp.resp_get_set_details.DeviceSecret
