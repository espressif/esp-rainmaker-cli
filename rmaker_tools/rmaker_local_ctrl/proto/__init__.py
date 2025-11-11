# SPDX-FileCopyrightText: 2018-2022 Espressif Systems (Shanghai) CO LTD
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

# protocomm component related python files - use local copies
constants_pb2 = _load_source('constants_pb2', os.path.join(local_ctrl_dir, 'constants_pb2.py'))
sec0_pb2      = _load_source('sec0_pb2',      os.path.join(local_ctrl_dir, 'sec0_pb2.py'))
sec1_pb2      = _load_source('sec1_pb2',      os.path.join(local_ctrl_dir, 'sec1_pb2.py'))
sec2_pb2      = _load_source('sec2_pb2',      os.path.join(local_ctrl_dir, 'sec2_pb2.py'))
session_pb2   = _load_source('session_pb2',   os.path.join(local_ctrl_dir, 'session_pb2.py'))

# wifi_provisioning component related python files - check if they exist locally
wifi_constants_pb2_path = os.path.join(local_ctrl_dir, 'wifi_constants_pb2.py')
if os.path.exists(wifi_constants_pb2_path):
    wifi_constants_pb2 = _load_source('wifi_constants_pb2', wifi_constants_pb2_path)
else:
    # Import from rmaker_prov if not available locally to avoid conflicts
    rmaker_prov_dir = os.path.join(current_dir, '..', '..', 'rmaker_prov')
    wifi_constants_pb2 = _load_source('wifi_constants_pb2', os.path.join(rmaker_prov_dir, 'wifi_provisioning', 'python', 'wifi_constants_pb2.py'))

# Similar approach for other wifi files
wifi_config_pb2_path = os.path.join(local_ctrl_dir, 'wifi_config_pb2.py')
if os.path.exists(wifi_config_pb2_path):
    wifi_config_pb2 = _load_source('wifi_config_pb2', wifi_config_pb2_path)
else:
    rmaker_prov_dir = os.path.join(current_dir, '..', '..', 'rmaker_prov')
    wifi_config_pb2 = _load_source('wifi_config_pb2', os.path.join(rmaker_prov_dir, 'wifi_provisioning', 'python', 'wifi_config_pb2.py'))

wifi_scan_pb2_path = os.path.join(local_ctrl_dir, 'wifi_scan_pb2.py')
if os.path.exists(wifi_scan_pb2_path):
    wifi_scan_pb2 = _load_source('wifi_scan_pb2', wifi_scan_pb2_path)
else:
    rmaker_prov_dir = os.path.join(current_dir, '..', '..', 'rmaker_prov')
    wifi_scan_pb2 = _load_source('wifi_scan_pb2', os.path.join(rmaker_prov_dir, 'wifi_provisioning', 'python', 'wifi_scan_pb2.py'))

# For wifi_ctrl_pb2, create a simple stub since it's not commonly used
class WifiCtrlPb2:
    pass

wifi_ctrl_pb2 = WifiCtrlPb2()
