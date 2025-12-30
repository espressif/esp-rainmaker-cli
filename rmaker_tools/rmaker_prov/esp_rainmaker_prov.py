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
        try:
            print("Scanning Wi-Fi AP's...")
            access_points = esp_prov.scan_wifi_APs(transport_mode,
                                                   obj_transport,
                                                   obj_security)
        except RuntimeError as e:
            print(f"Scanning failed: {e}")
            access_points = None

        len_access_points = len(access_points) if access_points else 0
        end_time = time.time()

        if access_points is None:
            print("Scanning Wi-Fi AP's - Failed")
            if input("Do you want to enter SSID manually? [y/N]: ").strip().lower() in ('y', 'yes'):
                ssid = input("Enter ssid :")
                passphrase = getpass(f"Enter passphrase for {ssid} : ")
                return ssid, passphrase
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
                     sec2_username='', sec2_password='', device_name=None, session=None, no_retry=False, no_wifi=False, disable_chal_resp=False):
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

    :param no_retry: If True, exit immediately if prov-ctrl succeeds without prompting for retry
    :type no_retry: bool, optional

    :param no_wifi: If True, skip WiFi provisioning and only perform challenge-response mapping.
                    Device must support challenge-response capability, otherwise an error is raised.
    :type no_wifi: bool, optional

    :param disable_chal_resp: If True, disable challenge-response on device after successful mapping.
                               Default is False for BLE/SoftAP (allows retry if provisioning fails).
                               On-network flows typically set this to True.
    :type disable_chal_resp: bool, optional

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

    # If --no-wifi is requested, session is required for challenge-response
    if no_wifi and session is None:
        error_msg = ("--no-wifi flag requires an authenticated session for challenge-response mapping. "
                    "Please ensure you are logged in.")
        raise RuntimeError(error_msg)

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
                    obj_transport, obj_security, session, disable_on_success=disable_chal_resp)
                if not success:
                    print("Challenge-response user-node association failed")
                    return None
                print("Challenge-response user-node association successful")
                print(f"✅ Node {nodeid} added to your account successfully!")
                challenge_response_performed = True
            else:
                # Only print this message if we're not in --no-wifi mode
                # (in --no-wifi mode, we'll raise an error below)
                if not no_wifi:
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

    # Handle --no-wifi flag: skip WiFi provisioning if challenge-response was performed
    if no_wifi:
        if challenge_response_performed:
            print("Skipping WiFi provisioning as requested (--no-wifi).")
            return (nodeid, challenge_response_performed)
        else:
            # Device doesn't support challenge-response, but --no-wifi was requested
            error_msg = ("--no-wifi flag requires device to support challenge-response capability. "
                        "This device does not support challenge-response based user-node mapping.")
            raise RuntimeError(error_msg)

    # Set up retry logic for WiFi provisioning
    dynamic_credentials = not bool(ssid and passphrase)
    prov_ctrl_succeeded = False  # Track if prov-ctrl reset succeeded

    def prompt_yes_no(prompt, default=False):
        while True:
            choice = input(prompt).strip().lower()
            if not choice:
                return default
            if choice in ('y', 'yes'):
                return True
            if choice in ('n', 'no'):
                return False
            print('Please respond with yes or no (y/n).')

    def request_device_reset():
        nonlocal prov_ctrl_succeeded
        # Try reset silently - only show messages if it succeeds
        try:
            reset_ok = esp_prov.ctrl_reset(obj_transport, obj_security)
        except RuntimeError as err:
            prov_ctrl_succeeded = False
            return False

        if not reset_ok:
            prov_ctrl_succeeded = False
            return False

        # Only show message if reset succeeded
        print('Device reset via prov-ctrl successful.')
        prov_ctrl_succeeded = True
        time.sleep(2)
        return True

    def handle_retry(reason_msg):
        nonlocal ssid, passphrase, dynamic_credentials, prov_ctrl_succeeded
        if reason_msg:
            print(reason_msg)

        # Try to reset device state before asking user if they want to retry
        if not request_device_reset():
            # If reset failed, print error message and exit without offering retry
            # Don't mention prov-ctrl since it failed silently
            prov_ctrl_succeeded = False
            print('Provisioning Failed. Reset your board to factory defaults and retry.')
            return False

        # If --no-retry is set and reset succeeded, exit with message
        # Don't show factory defaults message since prov-ctrl succeeded
        if no_retry:
            print('Device is reset to provisioning. Please try again')
            return False

        # Only offer retry if reset succeeded
        if not prompt_yes_no('Would you like to retry provisioning? [y/N]: '):
            # User declined retry, but prov-ctrl succeeded, so don't ask to reset to factory defaults
            # Since prov-ctrl succeeded, device is already reset to provisioning state
            print('Provisioning cancelled.')
            return False

        # If we have an SSID, offer to retry with the same SSID but new password
        if ssid:
            if prompt_yes_no(f"Retry with same SSID '{ssid}' and new password? [Y/n]: ", default=True):
                passphrase = getpass(f"Enter passphrase for {ssid} : ")
                dynamic_credentials = True
                return True

        if dynamic_credentials:
            ssid = None
            passphrase = None
        else:
            if prompt_yes_no('Do you want to re-enter Wi-Fi credentials? [y/N]: '):
                ssid = None
                passphrase = None
                dynamic_credentials = True
        return True

    def wait_for_wifi_connection():
        while True:
            time.sleep(5)
            ret = esp_prov.get_wifi_config(obj_transport, obj_security)
            if ret == 'connected':
                return True, 'connected'
            if ret == 'connecting':
                continue
            return False, ret or 'failed'

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

    # WiFi provisioning with retry support
    while True:
        if not (ssid and passphrase):
            ssid, passphrase = get_wifi_creds_from_scanlist(transport_mode,
                                                            obj_transport,
                                                            obj_security,
                                                            userid,
                                                            secretkey)
            dynamic_credentials = True

        if not esp_prov.send_wifi_config(obj_transport,
                                         obj_security,
                                         ssid,
                                         passphrase):
            if handle_retry("Sending Wi-Fi credentials to node - Failed"):
                continue
            # Return tuple with prov_ctrl_succeeded flag
            return (None, False, prov_ctrl_succeeded)
        print("Sending Wi-Fi credentials to node - Successful")

        if not esp_prov.apply_wifi_config(obj_transport, obj_security):
            if handle_retry("Applying Wi-Fi config to node - Failed"):
                continue
            # Return tuple with prov_ctrl_succeeded flag
            return (None, False, prov_ctrl_succeeded)
        print("Applying Wi-Fi config to node - Successful")

        success, status = wait_for_wifi_connection()
        if success:
            print("Wi-Fi Provisioning Successful.")
            return (nodeid, challenge_response_performed)

        if status in ('disconnected', 'failed', 'unknown'):
            reason_msg = "Wi-Fi Provisioning Failed."
        else:
            reason_msg = f"Wi-Fi Provisioning Failed. Unexpected status: {status}"

        if not handle_retry(reason_msg):
            # Return tuple with prov_ctrl_succeeded flag
            return (None, False, prov_ctrl_succeeded)


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
