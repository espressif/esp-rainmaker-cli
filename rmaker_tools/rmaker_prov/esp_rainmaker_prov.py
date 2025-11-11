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
import json
import textwrap
import time
import os
import sys
from getpass import getpass


try:
    # Use proper package imports
    from .prov import user_mapping as cloud_config_prov
    from .prov import prov_util as esp_prov
    from . import challenge_response
except ImportError:
    # Fallback: Direct imports using full module path
    current_dir = os.path.dirname(__file__)
    sys.path.insert(0, current_dir)
    
    # Import using importlib for better control
    import importlib.util
    
    # Import user_mapping
    user_mapping_path = os.path.join(current_dir, 'prov', 'user_mapping.py')
    spec = importlib.util.spec_from_file_location("user_mapping", user_mapping_path)
    cloud_config_prov = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cloud_config_prov)
    
    # Import prov_util
    prov_util_path = os.path.join(current_dir, 'prov', 'prov_util.py')
    spec = importlib.util.spec_from_file_location("prov_util", prov_util_path)
    esp_prov = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(esp_prov)
    
    # Import challenge_response
    challenge_response_path = os.path.join(current_dir, 'challenge_response.py')
    spec = importlib.util.spec_from_file_location("challenge_response", challenge_response_path)
    challenge_response = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(challenge_response)

# Set this to true to allow exceptions to be thrown
config_throw_except = True


def on_except(err):
    if config_throw_except:
        raise RuntimeError(err)
    else:
        print(err)


def custom_config(tp, sec, custom_id, custom_key):
    """
    Send custom config data
    """
    try:
        message = cloud_config_prov.custom_cloud_config_request(sec,
                                                                custom_id,
                                                                custom_key)
        response = tp.send_data('cloud_user_assoc', message)
        return cloud_config_prov.custom_cloud_config_response(sec, response)
    except RuntimeError as e:
        on_except(e)
        return None


def desc_format(*args):
    """
    Text Format to print the CLI help section for arguments
    """
    desc = ''
    for arg in args:
        desc += textwrap.fill(replace_whitespace=False, text=arg) + "\n"
    return desc


def get_wifi_creds_from_scanlist(transport_mode, obj_transport,
                                 obj_security, userid, secretkey):
    """
    Displays a Wi-Fi scanlist and gets Wi-Fi creds as input from user
    """
    if not esp_prov.has_capability(obj_transport, 'wifi_scan'):
        print("Wi-Fi Scan List is not supported by provisioning service")
        print("Rerun esp_prov with SSID and Passphrase as argument")
        exit(3)

    while True:
        print("Scanning Wi-Fi AP's...")
        access_points = esp_prov.scan_wifi_APs(transport_mode,
                                               obj_transport,
                                               obj_security)
        len_access_points = len(access_points)
        end_time = time.time()
        if access_points is None:
            print("Scanning Wi-Fi AP's - Failed")
            exit(8)

        if len_access_points == 0:
            print("No access_points found")
            exit(9)

        print("Select the Wi-Fi network from the following list:")
        print("{0: >4} {1: <33} {2: <12} {3: >4} {4: <4} {5: <16}".format(
            "S.N.", "SSID", "BSSID", "CHN", "RSSI", "AUTH"))
        for i in range(len_access_points):
            print("[{0: >2}] {1: <33} {2: <12} {3: >4} {4: <4} {5: <16}"
                  .format(i + 1, access_points[i]["ssid"],
                          access_points[i]["bssid"],
                          access_points[i]["channel"],
                          access_points[i]["rssi"],
                          access_points[i]["auth"]))

        # Add option to join a new network which is not part of scan list
        print("[{0: >2}] {1: <33}".format(len_access_points + 1,
              "Join another network"))
        while True:
            try:
                select = int(input("Select AP by number (0 to rescan) : "))
                if select < 0 or select > len_access_points + 1:
                    raise ValueError
                break
            except ValueError:
                print("Invalid selection! Retry")

        if select != 0:
            break

    if select == len_access_points + 1:
        ssid = input("Enter ssid :")
    else:
        ssid = access_points[select - 1]["ssid"]
    prompt_str = "Enter passphrase for {0} : ".format(ssid)
    passphrase = getpass(prompt_str)

    return ssid, passphrase


def provision_device(transport_mode, pop, userid, secretkey,
                     ssid=None, passphrase=None, security_version=None,
                     sec2_username='', sec2_password='', device_name=None, session=None):
    """
    Wi-Fi Provision a device

    :param transport_mode: The transport mode for communicating
                           with the device.
                           Can be either ble or softap.
    :type transport_mode: str

    :param pop:  The Proof of Possession pin for the device.
    :type pop: str

    :param userid: The User's ID that will be used for User-Node mapping.
    :type userid: str

    :param secretkey: The randomly generated secret key that will be used
                      for User-Node mapping.
    :type secretkey: str

    :param ssid: Target network SSID. Can be used if you want to
                 skip the Wi-Fi scan list.,
                 defaults to 'None' i.e. uses Wi-Fi Scan list
    :type ssid: str, optional

    :param passphrase: Password for the network whose SSID has been provided.\
        Required only if an SSID has been provided and the network
        is not Open.,
        defaults to 'None'
    :type passphrase: str, optional

    :param security_version: Security version (0, 1, or 2). If None, 
                            auto-detected from device capabilities.
    :type security_version: int, optional

    :param sec2_username: Username for Security 2 (SRP6a)
    :type sec2_username: str, optional

    :param sec2_password: Password for Security 2 (SRP6a)
    :type sec2_password: str, optional

    :param device_name: Device name for BLE transport (e.g., PROV_d76c30)
    :type device_name: str, optional

    :param session: Authenticated session object for challenge-response
    :type session: object, optional

    :return: nodeid (Node Identifier) on Success, None on Failure
    :rtype: str | None
    """
    # Ensure pop is always a string (not None) to avoid len() errors
    if pop is None:
        pop = ''
    
    # Set service name based on transport mode
    if transport_mode.lower() == 'ble':
        service_name = device_name  # Use device name for BLE
    else:
        service_name = None  # Use default for SoftAP (192.168.4.1:80)

    obj_transport = esp_prov.get_transport(transport_mode, service_name)
    if obj_transport is None:
        print("Establishing connection to node - Failed")
        return None

    # Auto-detect security version if not specified
    if security_version is None:
        # First check if capabilities are supported or not
        if not esp_prov.has_capability(obj_transport):
            print('Security capabilities could not be determined, defaulting to Security 1')
            security_version = 1
        else:
            # When no_sec is present, use security 0, else security 1
            security_version = int(not esp_prov.has_capability(obj_transport, 'no_sec'))
        print(f'==== Auto-detected Security Scheme: {security_version} ====')

    # Fetch and print device capabilities before checking pop requirements
    # This helps users understand why pop might be required
    # Store the response to reuse later for challenge-response check
    version_response = None
    try:
        print("Checking device capabilities...")
        version_response = esp_prov.get_version(obj_transport)
        if version_response:
            print(f"Device capabilities response: {version_response}")
        else:
            print("Device capabilities response: (empty or not available)")
    except Exception as e:
        # If we can't get capabilities, continue anyway
        print(f"Could not retrieve device capabilities: {e}")

    # Handle Security 1 PoP requirements
    if security_version == 1:
        if not esp_prov.has_capability(obj_transport, 'no_pop'):
            if len(pop) == 0:
                print("Proof of Possession argument not provided for Security 1")
                print("Note: Device does not support 'no_pop' capability. Pop is required for Security 1.")
                return None
        elif len(pop) != 0:
            print('Proof of Possession will be ignored (device supports no_pop capability)')
            pop = ''

    # Handle Security 2 credentials
    sec_patch_ver = 0
    if security_version == 2:
        sec_patch_ver = esp_prov.get_sec_patch_ver(obj_transport)
        if len(sec2_username) == 0:
            sec2_username = input('Security Scheme 2 - SRP6a Username required: ')
        if len(sec2_password) == 0:
            sec2_password = getpass('Security Scheme 2 - SRP6a Password required: ')

    obj_security = esp_prov.get_security(security_version, sec_patch_ver, 
                                       sec2_username, sec2_password, pop)
    if obj_security is None:
        print("Invalid Security Version")
        return None

    if not esp_prov.establish_session(obj_transport, obj_security):
        print("Establishing session - Failed")
        print("Ensure that security scheme and\
               proof of possession are correct")
        return None
    print("Establishing session - Successful")

    # Initialize nodeid and challenge_response_performed flag
    nodeid = None
    challenge_response_performed = False
    
    # Check for challenge-response capability and perform if supported
    if session is not None:
        try:
            # Reuse capabilities response from earlier, or fetch if not available
            if version_response is None:
                print("Attempting to get device capabilities...")
                version_response = esp_prov.get_version(obj_transport)
                if version_response:
                    print(f"Device capabilities response: {version_response}")
            # If we already have it, no need to print again
            
            # Check if device needs to be claimed before provisioning
            if version_response:
                try:
                    capabilities = json.loads(version_response)
                    if 'rmaker' in capabilities:
                        rmaker_caps = capabilities.get('rmaker', {}).get('cap', [])
                        if 'claim' in rmaker_caps or 'camera_claim' in rmaker_caps:
                            raise RuntimeError("Please claim the node before provisioning")
                except (json.JSONDecodeError, KeyError):
                    # If we can't parse capabilities, continue with provisioning
                    pass
            
            if version_response and challenge_response.has_challenge_response_capability(version_response):
                print("Device supports challenge-response, initiating user-node association...")
                success, nodeid = challenge_response.perform_challenge_response_flow(
                    obj_transport, obj_security, session)
                if not success:
                    print("Challenge-response user-node association failed")
                    return None
                print("Challenge-response user-node association successful")
                challenge_response_performed = True
            else:
                print("Device does not support challenge-response, proceeding with traditional flow")
        except RuntimeError:
            # Re-raise RuntimeError (claim requirement) to be handled by caller
            raise
        except Exception as e:
            print(f"Failed to check challenge-response capability - Exception: {e}")
            print(f"Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            print("Proceeding with traditional provisioning flow")
    else:
        print("No session provided, proceeding with traditional flow")

    if not (ssid and passphrase):
        ssid, passphrase = get_wifi_creds_from_scanlist(transport_mode,
                                                        obj_transport,
                                                        obj_security,
                                                        userid,
                                                        secretkey)

    # Only perform traditional custom_config if challenge-response wasn't performed
    if not challenge_response_performed:
        try:
            status, nodeid = custom_config(obj_transport,
                                           obj_security,
                                           userid,
                                           secretkey)
            if status != 0:
                print("Sending user information to node - Failed")
                return None
            print("Sending user information to node - Successful")
        except Exception as e:
            # Handle devices that don't support cloud_user_assoc endpoint
            if "Invalid endpoint" in str(e) or "cloud_user_assoc" in str(e):
                print("Device does not support user-node association endpoint")
                print("Proceeding with WiFi provisioning only (manual node addition required)")
                nodeid = "unknown"  # Will need manual addition to account
            else:
                print(f"User-node association failed: {e}")
                return None

    if not esp_prov.send_wifi_config(obj_transport,
                                     obj_security,
                                     ssid,
                                     passphrase):
        print("Sending Wi-Fi credentials to node - Failed")
        return None
    print("Sending Wi-Fi credentials to node - Successful")

    if not esp_prov.apply_wifi_config(obj_transport, obj_security):
        print("Applying Wi-Fi config to node - Failed")
        return None
    print("Applying Wi-Fi config to node - Successful")

    while True:
        time.sleep(5)
        ret = esp_prov.get_wifi_config(obj_transport, obj_security)
        if ret == 'connected':
            print("Wi-Fi Provisioning Successful.")
            return (nodeid, challenge_response_performed)
        elif ret == 'connecting':
            continue  # Keep waiting for connection
        elif ret in ('disconnected', 'failed', 'unknown') or ret is None:
            print("Wi-Fi Provisioning Failed.")
            return None
        else:
            # Unexpected return value, treat as failure
            print(f"Wi-Fi Provisioning Failed. Unexpected status: {ret}")
            return None
    print("Exiting Wi-Fi Provisioning.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=desc_format(
                                     'ESP RainMaker Provisioning tool\
                                      for configuring node '
                                     'running protocomm based\
                                     provisioning service.'),
                                     formatter_class=argparse.
                                     RawTextHelpFormatter)

    parser.add_argument("--transport", required=True, dest='mode', type=str,
                        help=desc_format(
                            'Mode of transport over which provisioning\
                            is to be performed.',
                            'This should be one of "softap", "ble", or "console"'))

    parser.add_argument("--sec_ver", dest='secver', type=int, default=None,
                        help=desc_format(
                            'Protocomm security scheme used by the provisioning service for secure '
                            'session establishment. Accepted values are :',
                            '\t- 0 : No security',
                            '\t- 1 : X25519 key exchange + AES-CTR encryption',
                            '\t      + Authentication using Proof of Possession (PoP)',
                            '\t- 2 : SRP6a + AES-GCM encryption',
                            'If not specified, security version is auto-detected from device capabilities'))

    parser.add_argument("--pop", dest='pop', type=str, default='',
                        help=desc_format(
                            'This specifies the Proof of possession (PoP) when security scheme 1 '
                            'is used. Required for Security 1, ignored for Security 2'))

    parser.add_argument("--sec2_username", dest='sec2_usr', type=str, default='',
                        help=desc_format(
                            'Username for security scheme 2 (SRP6a)'))

    parser.add_argument("--sec2_pwd", dest='sec2_pwd', type=str, default='',
                        help=desc_format(
                            'Password for security scheme 2 (SRP6a)'))

    parser.add_argument("--userid", dest='userid',
                        required=True, type=str, default='',
                        help=desc_format(
                             'Custom config data to be sent\
                             to device: UserID'))

    parser.add_argument("--secretkey", dest='secretkey',
                        required=True, type=str, default='',
                        help=desc_format(
                            'Custom config data to be sent\
                            to device: SecretKey'))

    parser.add_argument("--ssid", dest='ssid', type=str, default='',
                        help=desc_format(
                            'This configures the device to use\
                            SSID of the Wi-Fi network to which '
                            'we would like it to connect to permanently,\
                            once provisioning is complete. '
                            'If would prefer to use Wi-Fi scanning\
                            if supported by the provisioning service,\
                            this need not '
                            'be specified.'))
    # Eg. --ssid "MySSID" (double quotes needed if ssid has special characters)

    parser.add_argument("--passphrase", dest='passphrase',
                        type=str, default='',
                        help=desc_format(
                            'This configures the device to use Passphrase\
                            for the Wi-Fi network to which '
                            'we would like it to connect to permanently,\
                            once provisioning is complete. '
                            'If would prefer to use Wi-Fi scanning\
                            if supported by the provisioning service,\
                            this need not '
                            'be specified'))

    args = parser.parse_args()

    if not (args.userid and args.secretkey):
        parser.error("Error. --userid and --secretkey are required.")

    if (args.ssid or args.passphrase) and not (args.ssid and args.passphrase):
        parser.error("Error. --ssid and --passphrase are required.")

    # Validate security 2 requirements
    if args.secver == 2 and not (args.sec2_usr or args.sec2_pwd):
        print("Warning: Security 2 selected but no username/password provided. "
              "You will be prompted for credentials.")

    result = provision_device(args.mode, args.pop, args.userid,
                              args.secretkey, args.ssid, args.passphrase,
                              args.secver, args.sec2_usr, args.sec2_pwd)
    # Handle tuple return for backward compatibility
    if isinstance(result, tuple):
        node_id, _ = result
    else:
        node_id = result
