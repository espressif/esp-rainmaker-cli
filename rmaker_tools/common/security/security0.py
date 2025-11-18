# SPDX-FileCopyrightText: 2018-2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#

# APIs for interpreting and creating protobuf packets for
# protocomm endpoint with security type protocomm_security0

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
from .security import Security


class Security0(Security):
    def __init__(self, verbose):
        # Initialize state of the security1 FSM
        self.session_state = 0
        self.verbose = verbose
        Security.__init__(self, self.security0_session)

    def security0_session(self, response_data):
        # protocomm security0 FSM which interprets/forms
        # protobuf packets according to present state of session
        if (self.session_state == 0):
            self.session_state = 1
            return self.setup0_request()
        if (self.session_state == 1):
            self.setup0_response(response_data)
            return None

    def setup0_request(self):
        # Form protocomm security0 request packet
        setup_req = proto.session_pb2.SessionData()
        setup_req.sec_ver = 0
        session_cmd = proto.sec0_pb2.S0SessionCmd()
        setup_req.sec0.sc.MergeFrom(session_cmd)
        return setup_req.SerializeToString().decode('latin-1')

    def setup0_response(self, response_data):
        # Interpret protocomm security0 response packet
        setup_resp = proto.session_pb2.SessionData()
        setup_resp.ParseFromString(str_to_bytes(response_data))
        # Check if security scheme matches
        if setup_resp.sec_ver != proto.session_pb2.SecScheme0:
            raise RuntimeError('Incorrect security scheme')

    def encrypt_data(self, data):
        # Passive. No encryption when security0 used
        return data

    def decrypt_data(self, data):
        # Passive. No encryption when security0 used
        return data
