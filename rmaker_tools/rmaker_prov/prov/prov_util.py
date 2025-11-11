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

from __future__ import print_function
from builtins import input
import argparse
import textwrap
import time
import os
import sys
import json
from getpass import getpass

# Try relative imports first (when used as a package)
try:
    from ...common import security
    from ...common import transport
    from ...common import prov
except ImportError:
    # Fallback: try absolute imports (for pip-installed packages)
    try:
        from rmaker_tools.common import security
        from rmaker_tools.common import transport
        from rmaker_tools.common import prov
    except ImportError:
        # Last resort: use local modules if they exist (backward compatibility)
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        import security
        import transport
        import prov

# Set this to true to allow exceptions to be thrown
config_throw_except = True

def on_except(err):
    if config_throw_except:
        raise RuntimeError(err)
    else:
        print(err)

def get_security(secver, sec_patch_ver=0, username='', password='', pop=None, verbose=False):
    """
    Get Security based on input parameters
    `secver`: Security Version (Security0/Security1/Security2)
    `sec_patch_ver`: Security patch version for Security2
    `username`: Username for Security2
    `password`: Password for Security2  
    `pop`: Proof Of Possession for Security1
    """
    # Ensure pop is always a string (not None) to avoid len() errors in Security1
    if pop is None:
        pop = ''
    
    if secver == 2:
        return security.Security2(sec_patch_ver, username, password, verbose)
    elif secver == 1:
        return security.Security1(pop, verbose)
    elif secver == 0:
        return security.Security0(verbose)
    return None

def get_sec_patch_ver(tp, verbose=False):
    """
    Get security patch version from device
    """
    try:
        response = tp.send_data('proto-ver', '---')
        if verbose:
            print('proto-ver response : ', response)
        try:
            info = json.loads(response)
            return info['prov'].get('sec_patch_ver', 0)
        except ValueError:
            return 0
    except Exception:
        return 0

def get_transport(sel_transport, service_name):
    """
    Get object of class `Transport` based on input parameters
    `sel_transport` - Transport Mode (softap/ble)
    `service_name` - Service Name to connect to
    """
    try:
        tp = None
        if (sel_transport == 'softap'):
            if service_name is None:
                service_name = '192.168.4.1:80'
            tp = transport.Transport_HTTP(service_name)
        elif (sel_transport == 'ble'):
            # BLE client is now capable of automatically figuring out
            # the primary service from the advertisement data and the
            # characteristics corresponding to each endpoint.
            # Below, the service_uuid field and 16bit UUIDs in the nu_lookup
            # table are provided only to support devices running older firmware,
            # in which case, the automated discovery will fail and the client
            # will fallback to using the provided UUIDs instead
            nu_lookup = {'prov-session': 'ff51', 'prov-config': 'ff52', 'proto-ver': 'ff53'}
# Debug info removed for cleaner output
            
            # Check if this is the ESP-IDF version or our version
            import inspect
            import asyncio
            sig = inspect.signature(transport.Transport_BLE.__init__)
            if len(sig.parameters) == 3:  # self, service_uuid, nu_lookup
                ble_transport = transport.Transport_BLE(service_uuid='0000ffff-0000-1000-8000-00805f9b34fb',
                                                        nu_lookup=nu_lookup)
                
                # Create sync wrapper for async transport
                class SyncBLETransport:
                    def __init__(self, async_transport, device_name):
                        self.async_transport = async_transport
                        self.device_name = device_name
                        self.loop = None
                        self._connect()
                    
                    def _connect(self):
                        # Connect to the BLE device
                        async def connect():
                            await self.async_transport.connect(self.device_name)
                        
                        self.loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self.loop)
                        self.loop.run_until_complete(connect())
                    
                    def send_data(self, ep_name, data):
                        # Sync wrapper for async send_data
                        async def send():
                            return await self.async_transport.send_data(ep_name, data)
                        
                        if self.loop is None:
                            self.loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(self.loop)
                        
                        return self.loop.run_until_complete(send())
                    
                    def disconnect(self):
                        # Sync wrapper for async disconnect
                        if self.loop is not None:
                            async def disconnect():
                                await self.async_transport.disconnect()
                            self.loop.run_until_complete(disconnect())
                            self.loop.close()
                            self.loop = None
                    
                    def __del__(self):
                        try:
                            self.disconnect()
                        except:
                            pass
                
                tp = SyncBLETransport(ble_transport, service_name)
            else:  # Our version with name parameter
                tp = transport.Transport_BLE(service_uuid='0000ffff-0000-1000-8000-00805f9b34fb',
                                             nu_lookup=nu_lookup,
                                             name=service_name)
        elif (sel_transport == 'console'):
            tp = transport.Transport_Console()
        return tp
    except RuntimeError as e:
        on_except(e)
        return None

def version_match(tp, protover, verbose=False):
    """
    Check version match
    """
    try:
        response = tp.send_data('proto-ver', protover)

        if verbose:
            print("proto-ver response : ", response)

        # First assume this to be a simple version string
        if response.lower() == protover.lower():
            return True

        try:
            # Else interpret this as JSON structure containing
            # information with versions and capabilities of both
            # provisioning service and application
            info = json.loads(response)
            if info['prov']['ver'].lower() == protover.lower():
                return True

        except ValueError:
            # If decoding as JSON fails, it means that capabilities
            # are not supported
            return False

    except Exception as e:
        on_except(e)
        return None

def has_capability(tp, capability='none', verbose=False):
    """
    Check if Transport object `tp` has capabilities
    as given in input parameter `capability`
    """
    # Note : default value of `capability` argument cannot be empty string
    # because protocomm_httpd expects non zero content lengths
    try:
        response = tp.send_data('proto-ver', capability)

        if verbose:
            print("proto-ver response : ", response)

        try:
            # Interpret this as JSON structure containing
            # information with versions and capabilities of both
            # provisioning service and application
            info = json.loads(response)
            supported_capabilities = info['prov']['cap']
            if capability.lower() == 'none':
                # No specific capability to check, but capabilities
                # feature is present so return True
                return True
            elif capability in supported_capabilities:
                return True
            return False

        except ValueError:
            # If decoding as JSON fails, it means that capabilities
            # are not supported
            return False

    except RuntimeError as e:
        on_except(e)

    return False

def get_version(tp):
    """
    Get Version based on input parameters
    `tp` -  Object of class: Transport 
    """
    response = None
    try:
        response = tp.send_data('proto-ver', '---')
    except RuntimeError as e:
        on_except(e)
        response = ''
    return response

def establish_session(tp, sec):
    """
    Establish Provisioning Session based on input parameters
    `tp` -  Object of class: Transport 
    `sec`- Object of class: Security
    """
    try:
        response = None
        while True:
            request = sec.security_session(response)
            if request is None:
                break
            response = tp.send_data('prov-session', request)
            if (response is None):
                return False
        return True
    except RuntimeError as e:
        on_except(e)
        return None

def scan_wifi_APs(sel_transport, tp, sec):
    """
    Scans Wi-Fi AP's based on input parameters
    `sel_transport` - Transport Mode (softap/ble)
    `tp` -  Object of class: Transport 
    `sec`- Object of class: Security
    """
    APs = []
    group_channels = 0
    readlen = 100
    if sel_transport == 'softap':
        # In case of softAP we must perform the scan on individual channels, one by one,
        # so that the Wi-Fi controller gets ample time to send out beacons (necessary to
        # maintain connectivity with authenticated stations. As scanning one channel at a
        # time will be slow, we can group more than one channels to be scanned in quick
        # succession, hence speeding up the scan process. Though if too many channels are
        # present in a group, the controller may again miss out on sending beacons. Hence,
        # the application must should use an optimum value. The following value usually
        # works out in most cases
        group_channels = 5
    elif sel_transport == 'ble':
        # Read at most 4 entries at a time. This is because if we are using BLE transport
        # then the response packet size should not exceed the present limit of 256 bytes of
        # characteristic value imposed by protocomm_ble. This limit may be removed in the
        # future
        readlen = 4
    try:
        message = prov.scan_start_request(sec, blocking=True, group_channels=group_channels)
        start_time = time.time()
        response = tp.send_data('prov-scan', message)
        prov.scan_start_response(sec, response)

        message = prov.scan_status_request(sec)
        response = tp.send_data('prov-scan', message)
        result = prov.scan_status_response(sec, response)
        if result["count"] != 0:
            index = 0
            remaining = result["count"]
            while remaining:
                count = [remaining, readlen][remaining > readlen]
                message = prov.scan_result_request(sec, index, count)
                response = tp.send_data('prov-scan', message)
                APs += prov.scan_result_response(sec, response)
                remaining -= count
                index += count

    except RuntimeError as e:
        on_except(e)
        return None

    return APs

def send_wifi_config(tp, sec, ssid, passphrase):
    """
    Send Wi-Fi config based on input parameters
    `tp` -  Object of class: Transport 
    `sec`- Object of class: Security
    `ssid` - ssid of Wi-Fi network to configure
    `passphrase` - passphrase of Wi-Fi network to configure
    """
    try:
        message = prov.config_set_config_request(sec, ssid, passphrase)
        response = tp.send_data('prov-config', message)
        return (prov.config_set_config_response(sec, response) == 0)
    except RuntimeError as e:
        on_except(e)
        return None

def apply_wifi_config(tp, sec):
    """
    Apply Wi-Fi config based on input parameters
    `tp` -  Object of class: Transport 
    `sec`- Object of class: Security
    """
    try:
        message = prov.config_apply_config_request(sec)
        response = tp.send_data('prov-config', message)
        return (prov.config_apply_config_response(sec, response) == 0)
    except RuntimeError as e:
        on_except(e)
        return None

def get_wifi_config(tp, sec):
    """
    Get Wi-Fi config based on input parameters
    `tp` -  Object of class: Transport 
    `sec`- Object of class: Security
    """
    try:
        message = prov.config_get_status_request(sec)
        response = tp.send_data('prov-config', message)
        return prov.config_get_status_response(sec, response)
    except RuntimeError as e:
        on_except(e)
        return None
