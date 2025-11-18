#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import sys
import argparse
from rmaker_cmd.node import *
from rmaker_cmd.user import signup, login, forgot_password,\
                            get_user_details, logout, set_region_configuration, \
                            profile_list, profile_current, profile_switch, profile_add, profile_remove, delete_user
from rmaker_cmd.cmd_response import get_cmd_requests, create_cmd_request
from rmaker_cmd.provision import provision
from rmaker_cmd.test import test
from rmaker_lib.logger import log
from rmaker_cmd.group import group_add, group_remove, group_edit, group_list, group_show, group_add_nodes, group_remove_nodes, group_list_nodes

# Import the version
from rainmaker.version import VERSION

def display_version(vars=None):
    """
    Display the current version of ESP RainMaker CLI.

    :param vars: No parameters passed, defaults to `None`
    :type vars: dict | None

    :return: None
    :rtype: None
    """
    print(f"ESP RainMaker CLI v{VERSION}")

def add_profile_argument(parser):
    """
    Add --profile argument to a parser.

    :param parser: The argument parser to add the profile argument to
    :type parser: argparse.ArgumentParser
    """
    parser.add_argument('--profile',
                       type=str,
                       metavar='<profile_name>',
                       help='Use specified profile instead of current active profile')

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers(help='Functions')

    # Version command
    version_parser = subparsers.add_parser("version",
                                          help="Display ESP RainMaker CLI version")
    version_parser.set_defaults(func=display_version)

    # Configure ESP RainMaker settings
    configure_parser = subparsers.add_parser("configure",
                                             help="Configure ESP RainMaker")

    # Region configuration
    configure_parser.add_argument('--region',
                                  type=str,
                                  metavar='<region>',
                                  help='Region for ESP RainMaker, Valid Values: china, global. Default: global')

    configure_parser.set_defaults(func=set_region_configuration)

    # New dedicated profile command with subcommands
    profile_parser = subparsers.add_parser("profile",
                                          help="Manage ESP RainMaker profiles")
    profile_subparsers = profile_parser.add_subparsers(dest='profile_command', help='Profile operations')

    # profile list
    profile_list_parser = profile_subparsers.add_parser('list', help='List all available profiles')
    profile_list_parser.set_defaults(func=profile_list)

    # profile current
    profile_current_parser = profile_subparsers.add_parser('current', help='Show current profile information')
    profile_current_parser.set_defaults(func=profile_current)

    # profile switch
    profile_switch_parser = profile_subparsers.add_parser('switch', help='Switch to a different profile')
    profile_switch_parser.add_argument('profile_name',
                                       type=str,
                                       metavar='<profile_name>',
                                       help='Name of the profile to switch to')
    profile_switch_parser.set_defaults(func=profile_switch)

    # profile add
    profile_add_parser = profile_subparsers.add_parser('add', help='Add a new custom profile')
    profile_add_parser.add_argument('profile_name',
                                    type=str,
                                    metavar='<profile_name>',
                                    help='Name of the profile to create')
    profile_add_parser.add_argument('--base-url',
                                    type=str,
                                    metavar='<base_url>',
                                    required=True,
                                    help='Base URL for the custom profile')
    profile_add_parser.add_argument('--description',
                                    type=str,
                                    metavar='<description>',
                                    help='Description for the custom profile (optional)')
    profile_add_parser.set_defaults(func=profile_add)

    # profile remove
    profile_remove_parser = profile_subparsers.add_parser('remove', help='Remove a custom profile')
    profile_remove_parser.add_argument('profile_name',
                                       type=str,
                                       metavar='<profile_name>',
                                       help='Name of the profile to remove')
    profile_remove_parser.set_defaults(func=profile_remove)

    signup_parser = subparsers.add_parser("signup",
                                          help="Sign up for ESP RainMaker")
    signup_parser.add_argument('user_name',
                               type=str,
                               metavar='<user_name>',
                               help='Email address or phone number of the user')
    add_profile_argument(signup_parser)
    signup_parser.set_defaults(func=signup)

    login_parser = subparsers.add_parser("login",
                                         help="Login to ESP RainMaker")
    login_parser.add_argument('--user_name',
                              type=str,
                              metavar='<user_name>',
                              help='Email address/Phone number of the user')
    login_parser.add_argument('--email',
                              type=str,
                              metavar='<email>',
                              help='Email address of the user')
    login_parser.add_argument('--password',
                              type=str,
                              metavar='<password>',
                              help='Password of the user (for CI integration)')
    add_profile_argument(login_parser)
    login_parser.set_defaults(func=login)


    logout_parser = subparsers.add_parser("logout",
                                         help="Logout current (logged-in) user")
    add_profile_argument(logout_parser)
    logout_parser.set_defaults(func=logout)


    forgot_password_parser = subparsers.add_parser("forgotpassword",
                                                   help="Reset the password")
    forgot_password_parser.add_argument('user_name',
                                        type=str,
                                        metavar='<user_name>',
                                        help='Email address/Phone number of the user')
    add_profile_argument(forgot_password_parser)
    forgot_password_parser.set_defaults(func=forgot_password)

    getnodes_parser = subparsers.add_parser('getnodes',
                                            help='List all nodes associated'
                                                  ' with the user')
    add_profile_argument(getnodes_parser)
    getnodes_parser.set_defaults(func=get_nodes)

    getnodedetails_parser = subparsers.add_parser('getnodedetails',
                                               help='Get detailed information for all nodes'
                                                    ' including config, status, and params')
    getnodedetails_parser.add_argument('nodeid',
                                    type=str,
                                    metavar='<nodeid>',
                                    nargs='?',  # Make it optional
                                    help='Node ID for the node (if not provided, details for all nodes will be fetched)')
    getnodedetails_parser.add_argument('--raw',
                                    action='store_true',
                                    help='Print raw JSON output')
    add_profile_argument(getnodedetails_parser)
    getnodedetails_parser.set_defaults(func=get_node_details)

    getschedules_parser = subparsers.add_parser('getschedules',
                                               help='Get schedule information for a specific node')
    getschedules_parser.add_argument('nodeid',
                                      type=str,
                                      metavar='<nodeid>',
                                      help='Node ID for the node')
    add_profile_argument(getschedules_parser)
    getschedules_parser.set_defaults(func=get_schedules)

    setschedule_parser = subparsers.add_parser('setschedule',
                                             help='Manage schedules for a specific node',
                                             description='Manage schedules for a specific node.\nSee docs/schedule_examples.md for detailed examples of trigger and action configurations.',
                                             epilog='Example to add a schedule that turns on a light at 6:30 PM on weekdays:\n'
                                                   'esp-rainmaker-cli setschedule <nodeid> --operation add --name "Evening Light" \\\n'
                                                   '  --trigger \'{"m": 1110, "d": 31}\' --action \'{"Light": {"Power": true}}\'')
    setschedule_parser.add_argument('nodeid',
                                  type=str,
                                  metavar='<nodeid>',
                                  help='Node ID for the node (or comma-separated list of node IDs)')
    setschedule_parser.add_argument('--operation',
                                  type=str,
                                  required=True,
                                  choices=['add', 'edit', 'remove', 'enable', 'disable'],
                                  help='Operation to perform on the schedule')
    setschedule_parser.add_argument('--id',
                                  type=str,
                                  help='Schedule ID (required for edit, remove, enable, disable operations, not needed for add as IDs are auto-generated)')
    setschedule_parser.add_argument('--name',
                                  type=str,
                                  help='Schedule name (required for add operation, optional for edit)')
    setschedule_parser.add_argument('--trigger',
                                  type=str,
                                  help='JSON string defining the trigger configuration (required for add, optional for edit)')
    setschedule_parser.add_argument('--action',
                                  type=str,
                                  help='JSON string defining the action configuration (required for add, optional for edit)')
    setschedule_parser.add_argument('--info',
                                  type=str,
                                  help='Additional information for the schedule (optional)')
    setschedule_parser.add_argument('--flags',
                                  type=str,
                                  help='General purpose flags for the schedule (optional)')
    add_profile_argument(setschedule_parser)
    setschedule_parser.set_defaults(func=set_schedule)

    # Node Config
    getnodeconfig_parser = subparsers.add_parser('getnodeconfig',
                                                 help='Get node configuration')
    getnodeconfig_parser.add_argument('nodeid',
                                      type=str,
                                      metavar='<nodeid>',
                                      help='Node ID for the node')
    getnodeconfig_parser.add_argument('--local',
                                     action='store_true',
                                     help='Use local control instead of cloud')
    getnodeconfig_parser.add_argument('--pop',
                                     type=str,
                                     default='',
                                     help='Proof of possession for local control')
    getnodeconfig_parser.add_argument('--transport',
                                     type=str,
                                     choices=['http', 'https', 'ble'],
                                     default='http',
                                     help='Transport protocol for local control')
    getnodeconfig_parser.add_argument('--port',
                                     type=int,
                                     default=8080,
                                     help='Port for local control (default: 8080)')
    getnodeconfig_parser.add_argument('--sec_ver',
                                     type=int,
                                     choices=[0, 1, 2],
                                     default=1,
                                     help='Security version for local control')
    add_profile_argument(getnodeconfig_parser)
    getnodeconfig_parser.set_defaults(func=get_node_config)

    getnodestatus_parser = subparsers.add_parser('getnodestatus',
                                                 help='Get online/offline'
                                                       ' status of the node')
    getnodestatus_parser.add_argument('nodeid',
                                      type=str,
                                      metavar='<nodeid>',
                                      help='Node ID for the node')
    add_profile_argument(getnodestatus_parser)
    getnodestatus_parser.set_defaults(func=get_node_status)

    setparams_parser = subparsers.add_parser('setparams',
                                             help='Set node parameters'
                                                   ' \nNote: Enter JSON data in'
                                                   ' single quotes')
    setparams_parser.add_argument('nodeid',
                                  metavar='<nodeid>',
                                  help='Node ID for the node (or comma-separated list of node IDs)')
    setparams_data_group = setparams_parser.add_mutually_exclusive_group(
        required=True)

    setparams_data_group.add_argument('--filepath',
                                      help='Path of the JSON file\
                                            containing parameters to be set')
    setparams_data_group.add_argument('--data',
                                      help='JSON data to be set')
    
    # Add local control options
    setparams_parser.add_argument('--local',
                                 action='store_true',
                                 help='Use local control instead of cloud')
    setparams_parser.add_argument('--pop',
                                 type=str,
                                 default='',
                                 help='Proof of possession for local control')
    setparams_parser.add_argument('--transport',
                                 type=str,
                                 choices=['http', 'https', 'ble'],
                                 default='http',
                                 help='Transport protocol for local control')
    setparams_parser.add_argument('--port',
                                 type=int,
                                 default=8080,
                                 help='Port for local control (default: 8080)')
    setparams_parser.add_argument('--sec_ver',
                                 type=int,
                                 choices=[0, 1, 2],
                                 default=1,
                                 help='Security version for local control')
    
    # Note: setparams_data_group is mutually exclusive group, so we add profile to the parent
    add_profile_argument(setparams_parser)
    setparams_parser.set_defaults(func=set_params)

    getparams_parser = subparsers.add_parser('getparams',
                                             help='Get node parameters')
    getparams_parser.add_argument('nodeid',
                                  metavar='<nodeid>',
                                  help='Node ID for the node')
    getparams_parser.add_argument('--local',
                                 action='store_true',
                                 help='Use local control instead of cloud')
    getparams_parser.add_argument('--pop',
                                 type=str,
                                 default='',
                                 help='Proof of possession for local control')
    getparams_parser.add_argument('--transport',
                                 type=str,
                                 choices=['http', 'https', 'ble'],
                                 default='http',
                                 help='Transport protocol for local control')
    getparams_parser.add_argument('--port',
                                 type=int,
                                 default=8080,
                                 help='Port for local control (default: 8080)')
    getparams_parser.add_argument('--sec_ver',
                                 type=int,
                                 choices=[0, 1, 2],
                                 default=1,
                                 help='Security version for local control')
    add_profile_argument(getparams_parser)
    getparams_parser.set_defaults(func=get_params)

    remove_node_parser = subparsers.add_parser('removenode',
                                               help='Remove user node mapping')
    remove_node_parser.add_argument('nodeid',
                                    type=str,
                                    metavar='<nodeid>',
                                    help='Node ID for the node')
    add_profile_argument(remove_node_parser)
    remove_node_parser.set_defaults(func=remove_node)

    provision_parser = subparsers.add_parser('provision',
                                             help='Provision the node to join Wi-Fi network',
                                             formatter_class=argparse.RawTextHelpFormatter)
    
    provision_parser.add_argument('pop',
                                  type=str,
                                  nargs='?',
                                  metavar='<pop>',
                                  help=argparse.SUPPRESS)  # Hide deprecated positional argument
    
    provision_parser.add_argument('--pop',
                                  type=str,
                                  dest='pop_flag',
                                  required=False,
                                  help='Proof of possession for the node')
    
    provision_parser.add_argument('--transport',
                                  type=str,
                                  choices=['softap', 'ble', 'console'],
                                  default='softap',
                                  help='Transport mode for provisioning:\n'
                                       '  softap  - SoftAP + HTTP (default)\n'
                                       '  ble     - Bluetooth Low Energy\n'
                                       '  console - Serial console')
    
    provision_parser.add_argument('--sec_ver',
                                  type=int,
                                  choices=[0, 1, 2],
                                  help='Security scheme:\n'
                                       '  0 - No security\n'
                                       '  1 - Security 1 (X25519 + AES-CTR + PoP)\n'
                                       '  2 - Security 2 (SRP6a + AES-GCM)\n'
                                       'If not specified, auto-detected from device')
    
    provision_parser.add_argument('--sec2_username',
                                  type=str,
                                  help='Username for Security 2 (SRP6a)')
    
    provision_parser.add_argument('--sec2_password',
                                  type=str,
                                  help='Password for Security 2 (SRP6a)')
    
    provision_parser.add_argument('--device_name',
                                  type=str,
                                  help='Device name for BLE transport\n'
                                       '(e.g., PROV_d76c30)')
    
    provision_parser.add_argument('--ssid',
                                  type=str,
                                  help='WiFi SSID (if not provided, shows scan list)')
    
    provision_parser.add_argument('--passphrase',
                                  type=str,
                                  help='WiFi password')
    
    add_profile_argument(provision_parser)
    provision_parser.set_defaults(func=provision)

    getmqtthost_parser = subparsers.add_parser('getmqtthost',
                                               help='Get the MQTT Host URL'
                                                     ' to be used in the'
                                                     ' firmware')
    add_profile_argument(getmqtthost_parser)
    getmqtthost_parser.set_defaults(func=get_mqtt_host)

    claim_parser = subparsers.add_parser('claim',
                                         help='Claim the node connected to the given serial port'
                                              ' \n(Get cloud credentials)')

    claim_parser.add_argument("port", metavar='<port>',
                              default=None,
                              help='Serial Port connected to the device.'
                                   '\nUsage: ./rainmaker.py claim <port> [<optional arguments>]',
                              nargs='?')

    claim_parser.add_argument("--matter",
                              action='store_true',
                              help='Use Matter Claiming')

    claim_parser.add_argument("--platform",
                              type=str,
                              help='Node platform.')

    claim_parser.add_argument("--mac", metavar='<mac>',
                              type=str,
                              help='Node MAC address in the format AABBCC112233.')

    claim_parser.add_argument("--addr", metavar='<flash-address>',
                              help='Address in the flash memory where the claim data will be written.\nDefault: 0x340000')

    claim_parser.add_argument("--outdir", metavar='<outdir>',
                              type=str,
                              help='Directory to store the claim files.\nThe outdir can be specified using the environment variable RM_CLI_OUT_DIR as well.\nDefault: ~/.espressif/rainmaker/claim_data/')

    claim_parser.add_argument("--type", metavar='<type>',
                              type=str,
                              help='Special RainMaker Node type (e.g., "camera").')

    add_profile_argument(claim_parser)
    claim_parser.set_defaults(func=claim_node, parser=claim_parser)

    test_parser = subparsers.add_parser('test',
                                        help='Test commands to check'
                                              ' user node mapping')
    test_parser.add_argument('--addnode',
                             metavar='<nodeid>',
                             help='Add user node mapping')
    add_profile_argument(test_parser)
    test_parser.set_defaults(func=test)

    upload_ota_image_parser = subparsers.add_parser('otaupgrade',
                                                    help='Upload OTA Firmware image and start OTA Upgrade')
    upload_ota_image_parser.add_argument('nodeid',
                                         type=str,
                                         metavar='<nodeid>',
                                         help='Node ID for the node')
    upload_ota_image_parser.add_argument('otaimagepath',
                                        type=str,
                                        metavar='<ota_image_path>',
                                        help='OTA Firmware image path')
    add_profile_argument(upload_ota_image_parser)
    upload_ota_image_parser.set_defaults(func=ota_upgrade)

    user_info_parser = subparsers.add_parser("getuserinfo",
                                         help="Get details of current (logged-in) user")
    add_profile_argument(user_info_parser)
    user_info_parser.set_defaults(func=get_user_details)

    delete_user_parser = subparsers.add_parser("deleteuser",
                                              help="Delete current user account permanently",
                                              description="Delete current user account from ESP RainMaker.\n"
                                                        "⚠️  WARNING: This action will permanently delete your account\n"
                                                        "and ALL associated data including devices, groups, and settings.\n"
                                                        "This action cannot be undone!")
    add_profile_argument(delete_user_parser)
    delete_user_parser.set_defaults(func=delete_user)

    # Node Sharing
    sharing_parser = subparsers.add_parser('sharing',
                                            help='Node Sharing Operations',
                                            formatter_class=argparse.RawTextHelpFormatter,
                                            epilog="\nUser Login: \n\tCurrent (logged-in) user must be "
                                                 "a primary or secondary user to the node(s)\n\t"
                                                 "while performing the sharing operations")

    sharing_parser.set_defaults(func=node_sharing_ops, parser=sharing_parser)

    sharing_subparser = sharing_parser.add_subparsers(dest="sharing_ops")

    # Share node with user
    add_op_parser = sharing_subparser.add_parser('add_user',
                                                 help='Request to add user for sharing the node(s)',
                                                 formatter_class=argparse.RawTextHelpFormatter,
                                                 description="Send request to add user for the node(s)")

    add_op_parser.add_argument('--user',
                               type=str,
                               metavar='<user_name>',
                               help='User Name (Email) of secondary user',
                               required=True)

    add_op_parser.add_argument('--nodes',
                               type=str,
                               metavar='<node_ids>',
                               help="Node Id's of node(s)\n"
                               "format: <nodeid1>,<nodeid2>,...",
                               required=True)

    add_profile_argument(add_op_parser)
    add_op_parser.set_defaults(func=node_sharing_ops, parser=add_op_parser)


    # Remove shared nodes with user
    remove_user_op_parser = sharing_subparser.add_parser('remove_user',
                                                            help='Remove user from shared node(s)',
                                                            formatter_class=argparse.RawTextHelpFormatter,
                                                            description='Remove user from shared node(s)')

    remove_user_op_parser.add_argument('--user',
                                       type=str,
                                       metavar='<user_name>',
                                       help='User Name (Email) of secondary user',
                                       required=True)

    remove_user_op_parser.add_argument('--nodes',
                                       type=str,
                                       metavar='<node_ids>',
                                       help="Node Id's of shared node(s)\n"
                                       "format: <nodeid1>,<nodeid2>,...",
                                       required=True)

    add_profile_argument(remove_user_op_parser)
    remove_user_op_parser.set_defaults(func=node_sharing_ops, parser=remove_user_op_parser)


    # Accept sharing request
    add_accept_op_parser = sharing_subparser.add_parser('accept',
                                                         help='Accept sharing request(s)',
                                                         formatter_class=argparse.RawTextHelpFormatter,
                                                         description="Accept request for sharing node(s) received by "
                                                         "current (logged-in) user")

    add_accept_op_parser.add_argument('--id',
                                       type=str,
                                       metavar='<request_id>',
                                       required=True,
                                       help='Id of the sharing request'
                                       '\nYou can use {list_requests} command to list pending request(s)')

    add_profile_argument(add_accept_op_parser)
    add_accept_op_parser.set_defaults(func=node_sharing_ops, parser=add_accept_op_parser)

    # Decline sharing request
    add_decline_op_parser = sharing_subparser.add_parser('decline',
                                                         help='Decline sharing request(s)',
                                                         formatter_class=argparse.RawTextHelpFormatter,
                                                         description="Decline request to share node(s) received by "
                                                         "current (logged-in) user")

    add_decline_op_parser.add_argument('--id',
                                       type=str,
                                       metavar='<request_id>',
                                       required=True,
                                       help='Id of the sharing request'
                                       '\nYou can use {list_requests} command to list pending request(s)')

    add_profile_argument(add_decline_op_parser)
    add_decline_op_parser.set_defaults(func=node_sharing_ops, parser=add_decline_op_parser)

    # Cancel pending requests
    cancel_request_op_parser = sharing_subparser.add_parser('cancel',
                                                            help='Cancel sharing request(s)',
                                                            formatter_class=argparse.RawTextHelpFormatter,
                                                            description='Cancel request to share node(s) '
                                                            'sent by current (logged-in) user')

    cancel_request_op_parser.add_argument('--id',
                                            type=str,
                                            metavar='<request_id>',
                                            help='Id of the sharing request\nYou can use {list_requests} command to list pending request(s)',
                                            required=True)

    add_profile_argument(cancel_request_op_parser)
    cancel_request_op_parser.set_defaults(func=node_sharing_ops, parser=cancel_request_op_parser)

    # List sharing details for node(s) associated with user
    list_nodes_op_parser = sharing_subparser.add_parser('list_nodes',
                                                        help='List node(s) sharing details',
                                                        formatter_class=argparse.RawTextHelpFormatter,
                                                        description='Get sharing details of node(s) associated with current (logged-in) user'
                                                        )

    list_nodes_op_parser.add_argument('--node',
                                     type=str,
                                     metavar='<node_id>',
                                     help='Node Id of the node.\nIf provided, will list sharing details of a particular node'
                                     '\nDefault: List details of all node(s)')

    add_profile_argument(list_nodes_op_parser)
    list_nodes_op_parser.set_defaults(func=node_sharing_ops, parser=list_nodes_op_parser)

    # List details of sharing request(s)
    list_request_op_parser = sharing_subparser.add_parser('list_requests',
                                                          help='List pending request(s)',
                                                          formatter_class=argparse.RawTextHelpFormatter,
                                                          description='Get details of pending request(s) ',
                                                          epilog="primary user:\n\tGet details of pending request(s) "
                                                          "sent by current (logged-in) user"
                                                          "\nsecondary user:\n\tGet details of pending request(s) "
                                                          "received by current (logged-in) user"
                                                          )

    list_request_op_parser.add_argument('--primary_user',
                                       action='store_true',
                                       help='If provided, current (logged-in) user is set as primary user\n'
                                            'Default: User is set as secondary user')

    list_request_op_parser.add_argument('--id',
                                       type=str,
                                       metavar='<request_id>',
                                       help='Id of the sharing request\nIf provided, will list details of a particular request'
                                       '\nDefault: List details of all request(s)')

    add_profile_argument(list_request_op_parser)
    list_request_op_parser.set_defaults(func=node_sharing_ops, parser=list_request_op_parser)

    # POST command response
    create_cmd_resp_parser = subparsers.add_parser("create_cmd_request",
                                                    help="Create a Command Response Request (Beta)",
                                                    description='Create command response requests for the node(s) associated with the current (logged-in) user. The format of this command might change in future.')
    create_cmd_resp_parser.usage = create_cmd_resp_parser.format_usage().strip() + ' (Beta)'
    create_cmd_resp_parser.add_argument("nodes",
                                       type=str,
                                       help="Node Ids of the node(s)\n"
                                       "format: <nodeid1>,<nodeid2>,...,<nodeid25>")
    create_cmd_resp_parser.add_argument("cmd",
                                        type=int,
                                        help="ID of the command response request")
    create_cmd_resp_parser.add_argument("data",
                                        help="JSON data containing parameters to be sent to the node(s). Note: Enter JSON data in single quotes")
    create_cmd_resp_parser.add_argument("--timeout",
                                        type=int,
                                        help="Time in seconds till which the command response request will be valid",
                                        default=30)
    add_profile_argument(create_cmd_resp_parser)
    create_cmd_resp_parser.set_defaults(func=create_cmd_request)


    # GET command response
    get_cmd_resp_parser = subparsers.add_parser("get_cmd_requests",
                                                help="Get Command Response Requests (Beta)",
                                                description='Get command response requests created by current (logged-in) user. The format of this command might change in future.')
    get_cmd_resp_parser.usage = get_cmd_resp_parser.format_usage().strip() + ' (Beta)'
    get_cmd_resp_parser.add_argument("request_id",
                                    type=str,
                                    help="ID of the command response request")
    get_cmd_resp_parser.add_argument("--node_id",
                                    type=str,
                                    help="Node Id of the node")
    get_cmd_resp_parser.add_argument("--start_id",
                                    type=str,
                                    help="Start Id used for pagination. This should be the Next Id received in the previous batch")
    get_cmd_resp_parser.add_argument("--num_records",
                                    type=int,
                                    help="Number of requests to get")
    add_profile_argument(get_cmd_resp_parser)
    get_cmd_resp_parser.set_defaults(func=get_cmd_requests)

    # Set parsers to print help for associated commands
    PARSER_HELP_PRINT = {
        'sharing_ops': sharing_parser,
        'add_user': add_op_parser,
        'accept': add_accept_op_parser,
        'decline': add_decline_op_parser,
        'cancel': cancel_request_op_parser,
        'remove_user': remove_user_op_parser,
        'list_nodes': list_nodes_op_parser,
        'list_requests': list_request_op_parser
        }

    # Group Management
    group_parser = subparsers.add_parser('group',
                                         help='Manage device groups')
    group_subparsers = group_parser.add_subparsers(dest='group_command', help='Group operations')

    # group add
    group_add_parser = group_subparsers.add_parser('add', help='Create a new group')
    group_add_parser.add_argument('--name', type=str, required=True, help='Name of the group')
    group_add_parser.add_argument('--description', type=str, help='Description of the group')
    group_add_parser.add_argument('--mutually-exclusive', action='store_true', help='Set mutually exclusive flag')
    group_add_parser.add_argument('--custom-data', type=str, help='Custom data as JSON string')
    group_add_parser.add_argument('--nodes', type=str, help='Comma separated list of node IDs')
    group_add_parser.add_argument('--type', type=str, help='Type of the group')
    group_add_parser.add_argument('--parent-group-id', type=str, help='Parent group ID')
    add_profile_argument(group_add_parser)
    group_add_parser.set_defaults(func=group_add)

    # group remove
    group_remove_parser = group_subparsers.add_parser('remove', help='Delete a group')
    group_remove_parser.add_argument('--group-id', type=str, required=True, help='ID of the group to delete')
    add_profile_argument(group_remove_parser)
    group_remove_parser.set_defaults(func=group_remove)

    # group edit
    group_edit_parser = group_subparsers.add_parser('edit', help='Edit a group')
    group_edit_parser.add_argument('--group-id', type=str, required=True, help='ID of the group to edit')
    group_edit_parser.add_argument('--name', type=str, help='New name for the group')
    group_edit_parser.add_argument('--description', type=str, help='New description for the group')
    group_edit_parser.add_argument('--mutually-exclusive', type=str, choices=['true', 'false', '1', '0'], help='Set mutually exclusive flag (true/false or 1/0)')
    group_edit_parser.add_argument('--custom-data', type=str, help='Custom data as JSON string')
    group_edit_parser.add_argument('--type', type=str, help='Type of the group')
    group_edit_parser.add_argument('--parent-group-id', type=str, help='Parent group ID')
    add_profile_argument(group_edit_parser)
    group_edit_parser.set_defaults(func=group_edit)

    # group list
    group_list_parser = group_subparsers.add_parser('list', help='List all groups')
    group_list_parser.add_argument('--sub-groups', action='store_true', help='Include sub-groups in the output to view hierarchy')
    add_profile_argument(group_list_parser)
    group_list_parser.set_defaults(func=group_list)

    # group show
    group_show_parser = group_subparsers.add_parser('show', help='Show group details')
    group_show_parser.add_argument('--group-id', type=str, required=True, help='ID of the group to show')
    group_show_parser.add_argument('--sub-groups', action='store_true', help='Include sub-groups in the output')
    add_profile_argument(group_show_parser)
    group_show_parser.set_defaults(func=group_show)

    # group add-nodes
    group_add_nodes_parser = group_subparsers.add_parser('add-nodes', help='Add nodes to a group')
    group_add_nodes_parser.add_argument('--group-id', type=str, required=True, help='ID of the group')
    group_add_nodes_parser.add_argument('--nodes', type=str, required=True, help='Comma separated list of node IDs to add')
    add_profile_argument(group_add_nodes_parser)
    group_add_nodes_parser.set_defaults(func=group_add_nodes)

    # group remove-nodes
    group_remove_nodes_parser = group_subparsers.add_parser('remove-nodes', help='Remove nodes from a group')
    group_remove_nodes_parser.add_argument('--group-id', type=str, required=True, help='ID of the group')
    group_remove_nodes_parser.add_argument('--nodes', type=str, required=True, help='Comma separated list of node IDs to remove')
    add_profile_argument(group_remove_nodes_parser)
    group_remove_nodes_parser.set_defaults(func=group_remove_nodes)

    # group list-nodes
    group_list_nodes_parser = group_subparsers.add_parser('list-nodes', help='List nodes in a group')
    group_list_nodes_parser.add_argument('--group-id', type=str, required=True, help='ID of the group')
    group_list_nodes_parser.add_argument('--node-details', action='store_true', help='Show detailed node info')
    group_list_nodes_parser.add_argument('--sub-groups', action='store_true', help='Include sub-groups in the output')
    group_list_nodes_parser.add_argument('--raw', action='store_true', help='Print raw JSON output (only with --node-details)')
    add_profile_argument(group_list_nodes_parser)
    group_list_nodes_parser.set_defaults(func=group_list_nodes)

    args = parser.parse_args()

    if args.func is not None:
        try:
            args.func(vars=vars(args))
        except KeyboardInterrupt:
            log.debug('KeyboardInterrupt occurred. Login session is aborted.')
            print("\nExiting...")
        except Exception as err:
            log.error(err)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
