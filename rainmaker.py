#!/usr/bin/env python3
#
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
 
import argparse
from cmd.node import *
from cmd.user import *
from cmd.provision import provision
from cmd.test import test
from lib.logger import log

def main():

    parser = argparse.ArgumentParser()
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers(help='Functions')

    signup_parser = subparsers.add_parser("signup", help="Sign up for ESP Rainmaker")
    signup_parser.add_argument('email', type=str, metavar='<email>', help='Email address of the user')
    signup_parser.set_defaults(func=signup)

    login_parser = subparsers.add_parser("login", help="Login to ESP Rainmaker")
    login_parser.add_argument('--email', type=str, help='Email address of the user')
    login_parser.set_defaults(func=login)

    forgot_password_parser = subparsers.add_parser("forgotpassword", help="Reset the password")
    forgot_password_parser.add_argument('email', type=str, metavar='<email>', help='Email address of the user')
    forgot_password_parser.set_defaults(func=forgot_password)

    getnodes_parser = subparsers.add_parser('getnodes', help='List all nodes associated with the user')
    getnodes_parser.set_defaults(func=get_nodes)

    getnodeconfig_parser = subparsers.add_parser('getnodeconfig', help='Get node configuration')
    getnodeconfig_parser.add_argument('nodeId', type=str, metavar='<nodeId>', help='Node ID for the node')
    getnodeconfig_parser.set_defaults(func=get_node_config)

    setparams_parser = subparsers.add_parser('setparams', help='Set node parameters. Note: Enter JSON data in single quotes')
    setparams_parser.add_argument('nodeId', metavar='<nodeId>', help='Node ID for the node')
    setparams_parser = setparams_parser.add_mutually_exclusive_group(required=True)
    setparams_parser.add_argument('--filepath', help='Path of the JSON file containing parameters to be set')
    setparams_parser.add_argument('--data', help='JSON data containing parameters to be set. Note: Enter JSON data in single quotes')
    setparams_parser.set_defaults(func=set_params)
    
    getparams_parser = subparsers.add_parser('getparams', help='Get node parameters')
    getparams_parser.add_argument('nodeId', type=str, metavar='<nodeId>', help='Node ID for the node')
    getparams_parser.set_defaults(func=get_params)
    
    remove_node_parser = subparsers.add_parser('removenode', help='Remove user node mapping')
    remove_node_parser.add_argument('nodeId', type=str, metavar='<nodeId>', help='Node ID for the node')
    remove_node_parser.set_defaults(func=remove_node)

    provision_parser = subparsers.add_parser('provision', help='Provision the node to join Wi-Fi network')
    provision_parser.add_argument('pop', type=str, metavar='<pop>', help='Proof of possesion for the node')
    provision_parser.set_defaults(func=provision)

    claim_parser = subparsers.add_parser('claim', help='Claim the ESP32-S2 (Get Cloud credentials)')
    claim_parser.add_argument("port", metavar='<port>', help='Serial Port connected to the device.')
    claim_parser.set_defaults(func=claim_node)

    getmqtthost_parser = subparsers.add_parser('getmqtthost', help='Get the MQTT Host URL to be used in the firmware')
    getmqtthost_parser.set_defaults(func=get_mqtt_host)

    test_parser = subparsers.add_parser('test', help='Test commands to check user node mapping')
    test_parser.add_argument('--addnode', metavar='<nodeId>', help='Add user node mapping')
    test_parser.set_defaults(func=test)

    args = parser.parse_args()
    
    if args.func is not None:
        try:
            args.func(args)
        except KeyboardInterrupt:
            log.debug('KeyboardInterrupt occurred. Login session is aborted.')
            print("\nExiting...")
        except Exception as err:
            log.error(err)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
