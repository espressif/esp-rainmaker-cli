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
                            profile_list, profile_current, profile_switch, profile_add, profile_remove
from rmaker_cmd.cmd_response import get_cmd_requests, create_cmd_request
from rmaker_cmd.provision import provision
from rmaker_cmd.test import test
from rmaker_lib.logger import log

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
                                  help='Node ID for the node')
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
                                  help='Node ID for the node')
    setparams_parser = setparams_parser.add_mutually_exclusive_group(
        required=True)

    setparams_parser.add_argument('--filepath',
                                  help='Path of the JSON file\
                                        containing parameters to be set')
    setparams_parser.add_argument('--data',
                                  help='JSON data containing parameters\
                                        to be set. Note: Enter JSON data\
                                        in single quotes')
    # Note: setparams_parser is mutually exclusive group, so we add profile to the parent
    setparams_main_parser = subparsers._name_parser_map['setparams']
    add_profile_argument(setparams_main_parser)
    setparams_parser.set_defaults(func=set_params)

    getparams_parser = subparsers.add_parser('getparams',
                                             help='Get node parameters')
    getparams_parser.add_argument('nodeid',
                                  type=str,
                                  metavar='<nodeid>',
                                  help='Node ID for the node')
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
                                             help='Provision the node'
                                                   ' to join Wi-Fi network')
    provision_parser.add_argument('pop',
                                  type=str,
                                  metavar='<pop>',
                                  help='Proof of possesion for the node')
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
