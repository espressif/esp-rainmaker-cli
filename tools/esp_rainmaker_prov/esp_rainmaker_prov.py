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
from getpass import getpass

try:
    if "IDF_PATH" in os.environ and os.getenv("IDF_PATH") != "":
        idf_path = os.environ['IDF_PATH']
    else:
        print("Please set the IDF_PATH environment variable.")
        sys.exit(1)
    prov_path = os.path.dirname(__file__)
    sys.path.insert(0, prov_path + "/prov")
    sys.path.insert(1, prov_path)
    sys.path.insert(2, idf_path + "/components/protocomm/python")
    import user_mapping as cloud_config_prov
    import prov_util as esp_prov
    import security
    import transport
    import prov
except ImportError as err:
    print("Cannot import: ", err)
    sys.exit(1)

# Set this to true to allow exceptions to be thrown
config_throw_except = True

def on_except(err):
    if config_throw_except:
        raise RuntimeError(err)
    else:
        print(err)

def custom_config(tp, sec, custom_id, custom_key):
    try:
        message = cloud_config_prov.custom_cloud_config_request(sec, custom_id, custom_key)
        response = tp.send_data('cloud_user_assoc', message) 
        return cloud_config_prov.custom_cloud_config_response(sec, response)
    except RuntimeError as e:
        on_except(e)
        return None

def desc_format(*args):
    desc = ''
    for arg in args:
        desc += textwrap.fill(replace_whitespace=False, text=arg) + "\n"
    return desc


def get_wifi_creds_from_scanlist(transport_mode, obj_transport, obj_security, userid, secretkey):
    if not esp_prov.has_capability(obj_transport, 'wifi_scan'):
        print("Wi-Fi Scan List is not supported by provisioning service")
        print("Rerun esp_prov with SSID and Passphrase as argument")
        exit(3)

    while True:
        print("Scanning Wi-Fi APs...")
        APs = esp_prov.scan_wifi_APs(transport_mode, obj_transport, obj_security)
        len_APs = len(APs)
        end_time = time.time()
        if APs is None:
            print("Scanning Wi-Fi APs - Failed")
            exit(8)

        if len_APs == 0:
            print("No APs found")
            exit(9)

        print("Select the Wi-Fi network from the following list:")
        print("{0: >4} {1: <33} {2: <12} {3: >4} {4: <4} {5: <16}".format(
            "S.N.", "SSID", "BSSID", "CHN", "RSSI", "AUTH"))
        for i in range(len_APs):
            print("[{0: >2}] {1: <33} {2: <12} {3: >4} {4: <4} {5: <16}".format(
                 i + 1, APs[i]["ssid"], APs[i]["bssid"], APs[i]["channel"], APs[i]["rssi"], APs[i]["auth"]))

        # Add option to join a new network which is not part of scan list
        print("[{0: >2}] {1: <33}".format(len_APs + 1, "Join another network"))
        while True:
            try:
                select = int(input("Select AP by number (0 to rescan) : "))
                if select < 0 or select > len_APs + 1:
                    raise ValueError
                break
            except ValueError:
                print("Invalid selection! Retry")

        if select != 0:
            break

    if select == len_APs + 1:
        ssid = input("Enter ssid :")
    else:
        ssid = APs[select - 1]["ssid"]
    prompt_str = "Enter passphrase for {0} : ".format(ssid)
    passphrase = getpass(prompt_str)

    return ssid, passphrase


def provision_device(transport_mode, pop, userid, secretkey, ssid=None, passphrase=None):
    security_version = 1  # this utility should run with Security1
    service_name = None # will use default (192.168.4.1:80)

    obj_transport = esp_prov.get_transport(transport_mode, service_name)
    if obj_transport is None:
        print("Establishing connection to node - Failed")
        return None

    # First check if capabilities are supported or not
    if not esp_prov.has_capability(obj_transport):
        print('Security capabilities could not be determined.')
        return None

    # Ensure no_pop capability is not supported for Security Version1
    if not esp_prov.has_capability(obj_transport, 'no_pop'):
        if len(pop) == 0:
            print("Proof of Possession argument not provided")
            return None
    else:
        print("Invalid: no_pop capability is supported for Security Version 1")
        return None

    obj_security = esp_prov.get_security(security_version, pop)
    if obj_security is None:
        print("Invalid Security Version")
        return None

    if not esp_prov.establish_session(obj_transport, obj_security):
        print("Establishing session - Failed")
        print("Ensure that security scheme and proof of possession are correct")
        return None
    print("Establishing session - Successful")

    if not (ssid and passphrase):
        ssid, passphrase = get_wifi_creds_from_scanlist(transport_mode, obj_transport, obj_security, userid, secretkey)
      
    status, nodeId = custom_config(obj_transport, obj_security, userid, secretkey)
    if status != 0:
        print("Sending user information to node - Failed")
        return None
    print("Sending user information to node - Successful")

    if not esp_prov.send_wifi_config(obj_transport, obj_security, ssid, passphrase):
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
        if (ret == 1):
            continue
        elif (ret == 0):
            print("Wi-Fi Provisioning Successful.")
            return nodeId
        else:
            print("Wi-Fi Provisioning Failed.")
            return None
        break
    print("Exiting Wi-Fi Provisioning.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=desc_format(
                                     'ESP RainMaker Provisioning tool for configuring node '
                                     'running protocomm based provisioning service.'),
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("--transport", required=True, dest='mode', type=str,
                        help=desc_format(
                            'Mode of transport over which provisioning is to be performed.',
                            'This should be one of "softap" or "ble"'))

    parser.add_argument("--pop", required=True, dest='pop', type=str, default='',
                        help=desc_format(
                            'This specifies the Proof of possession (PoP)'))

    parser.add_argument("--userid", dest='userid', required=True, type=str, default='',
                        help=desc_format(
                             'Custom config data to be sent to device: UserID'))

    parser.add_argument("--secretkey", dest='secretkey', required=True, type=str, default='',
                        help=desc_format(
                            'Custom config data to be sent to device: SecretKey'))

    parser.add_argument("--ssid", dest='ssid', type=str, default='',
                        help=desc_format(
                            'This configures the device to use SSID of the Wi-Fi network to which '
                            'we would like it to connect to permanently, once provisioning is complete. '
                            'If would prefer to use Wi-Fi scanning if supported by the provisioning service, this need not '
                            'be specified.')) # Eg. --ssid "MySSID" (double quotes needed if ssid has special characters)

    parser.add_argument("--passphrase", dest='passphrase', type=str, default='',
                        help=desc_format(
                            'This configures the device to use Passphrase for the Wi-Fi network to which '
                            'we would like it to connect to permanently, once provisioning is complete. '
                            'If would prefer to use Wi-Fi scanning if supported by the provisioning service, this need not '
                            'be specified'))

    args = parser.parse_args()
    print(args.ssid)
    print(args.passphrase)
    print(args.ssid and args.passphrase)

    if not (args.userid and args.secretkey):
        parser.error("Error. --userid and --secretkey are required.")

    if (args.ssid or args.passphrase) and not (args.ssid and args.passphrase):
        parser.error("Error. --ssid and --passphrase are required.")

    provision_device(args.mode, args.pop, args.userid, args.secretkey, args.ssid, args.passphrase)
