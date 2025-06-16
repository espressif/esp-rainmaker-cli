# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

try:
    from rmaker_lib import session
    from rmaker_lib.logger import log
    from rmaker_lib import cmd_response
    from rmaker_lib.profile_utils import get_session_with_profile
except ImportError as err:
    print("Failed to import ESP Rainmaker library. " + str(err))
    raise err


def get_cmd_requests(vars=None):
    """
    Get command response requests and print the response

    :param vars: A dictionary of all parameters that the user has specified, 
                 including 'profile' for profile override, defaults to None
    :type vars: dict, optional
    """    
    try:
        curr_session = get_session_with_profile(vars or {})
        cmd = cmd_response.CommandResponseRequest(curr_session, vars["request_id"], vars["node_id"], vars["start_id"], vars["num_records"], None, None, None, None)
        cmd_resp = cmd.get_cmd_requests()
    except Exception as get_cmd_err:
        log.error(get_cmd_err)
    else:
        for key, val in cmd_resp.items():
            title = key.replace("_", " ").title()
            print("{}: {}".format(title, val))
        print("(This is in Beta)")


def create_cmd_request(vars=None):
    """
    Create a command response request and print the response

    :param vars: A dictionary of all parameters that the user has specified,
                 including 'profile' for profile override, defaults to None
    :type vars: dict, optional
    """    
    try:
        curr_session = get_session_with_profile(vars or {})
        cmd = cmd_response.CommandResponseRequest(curr_session, None, None, None, None, vars["nodes"], vars["cmd"], vars["data"], vars["timeout"])
        cmd_resp = cmd.create_cmd_request()
    except Exception as create_cmd_err:
        log.error(create_cmd_err)
    else:
        for key, val in cmd_resp.items():
            title = key.replace("_", " ").title()
            print("{}: {}".format(title, val))
        print("(This is in Beta)")
