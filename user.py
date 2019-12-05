#!/usr/bin/env python3
#
# Copyright 2019 Espressif Systems (Shanghai) PTE LTD
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
#

import json, sys
import requests
import getpass
import time
from requests.exceptions import HTTPError
from logger import log
from constants import *
from config import *
from utility import getHeader
from githublogin import login_github, setConfigFile

def signup(args):
    """
        User signup to the ESP Rainmaker
        :param args:
        a) username  - Email address of the user
        :return:
        pass - Calls another function to reset password
        fail - None
    """
    username = args.email
    log.info("Inside signup function, username : " + username)

    path = PATH_PREFIX + 'users'
    request_parameters = ''
    signup_info = {
        'user_name' : username
        }

    request_header = {'content-type': 'application/json'}
    signup_url = HTTPS_PREFIX + HOST + path

    try:
        response = requests.post(url = signup_url, data = json.dumps(signup_info), headers=request_header)
        response.raise_for_status()

    except HTTPError as http_err:
        log.error(f'Signup failed \n {http_err}')
        print(response.text)
        return
    
    except requests.ConnectionError:
        print("Please check the internet connectivity. No internet connection available")
        sys.exit(1)

    except Exception as err:
        log.error(f'Signup failed : {err}')
        print(response.text)
        return

    try:
        response = json.loads(response.text)
        log.info("Signup response : " + json.dumps(response, indent=4))

    except Exception as err:
        log.error(f'Decoding Signup response failed : {err}')
        print(response.text)
        return None

    if 'status' in response:
        if response['status'] == 'failure':
            print(json.dumps(response, indent=4))
    elif 'user_id' in response and 'user_name' in response:
        print('Enter the temporary password sent on your mail')
        login(args)
        print("Signup successful..!!")
        print("Please login to start using Rainmaker CLI")
    return

def login(args):
    """
        First time login of the user to reset the password
        :param args:
        a) username  - Email address of the user
        :return:
        pass - Calls another function to reset password
        fail - None
    """
    if args.email is None :
        login_github()
        return

    username = args.email
    log.info("Inside login function, username : " + username)

    password = getpass.getpass()

    path = PATH_PREFIX + 'login/'
    request_parameters = ''
    login_info = {
        'username' : username,
        'password' : password
        }

    request_header = {'content-type': 'application/json'}
    login_url = HTTPS_PREFIX + HOST + path

    try:
        response = requests.post(url = login_url, data = json.dumps(login_info), headers=request_header)
        response.raise_for_status()

    except HTTPError as http_err:
        log.error(f'Login failed \n {http_err}')
        # HTTP error response is handled below, that is why program does not exit
        pass
   
    except requests.ConnectionError:
        print("Please check the internet connectivity. No internet connection available")
        sys.exit(1)

    except Exception as err:
        log.error(f'Login failed : {err}')
        print(response.text)
        sys.exit(1)

    try:
        response = json.loads(response.text)
        log.info("Login response : " + json.dumps(response, indent=4))

    except Exception as err:
        print(ERROR_JSON_DECODE)
        log.error(f'Decoding Login response failed : {err}')
        return None

    if 'status' in response:
        if response['status'] == NEW_PASSWORD_REQUIRED :
            session = response['session']
            changePassword(username, session)

        elif response['status'] == 'success' and 'idtoken' in response:
            setConfigFile(response['idtoken'])
            # waiting for 5 seconds to set the config file, otherwise next immediate API call will fail
            time.sleep(5)
            print("Login successful..!!")
            return None

        elif response['status'] == 'failure' and 'description' in response:
            print(response['description'])
            print("Please login again")
            sys.exit(1)


def changePassword(username, session):
    """
        Reset the password and confirms the user
        :param args:
        a) username  - Email address of the user
        b) session   - Session token required to change the passowrd
        :return:
        pass - Acknowledges for the successful signup
        fail - None
    """
    log.info("Inside changePassword function")

    print("Please change your password")
    new_password = getpass.getpass("New-Password : ")
    confirm_password = getpass.getpass("Confirm-Password : ")
    password_change_attempt = 0

    while new_password != confirm_password :
        print("Passwords does not match\nPlease enter the password again ..")
        new_password = getpass.getpass("New-Password : ")
        confirm_password = getpass.getpass("Confirm-Password : ")
        password_change_attempt += 1
        if password_change_attempt == MAX_PASSWORD_CHANGE_ATTEMPT :
            print("Maximum attempts to change password over")
            log.error("Password change failed. Maximum attempts to change password over")
            return

    path = PATH_PREFIX + 'password'
    request_parameters = 'forcechange=true'
    data ={
        "username" : username,
        "newpassword" : new_password,
        "session" : session
    }

    request_header = {'content-type': 'application/json'}
    password_change_url = HTTPS_PREFIX + HOST + path + QUESTION_MARK + request_parameters

    try:
        response = requests.put(url = password_change_url, data = json.dumps(data), headers=request_header)
        response.raise_for_status()                 # If the response was successful, no Exception will be raised

    except HTTPError as http_err:
        print(response.text)
        log.error(f'Password change failed \n {http_err}')
        return None
   
    except requests.ConnectionError:
        print("Please check the internet connectivity. No internet connection available")
        sys.exit(1)

    except Exception as err:
        print(response.text)
        log.error(f'Password change failed : {err}')
        return None
    try:
        response = json.loads(response.text)
        log.info("Password change response : " + json.dumps(response, indent=4))

    except Exception as err:
        log.error(f'Decoding Password change response failed : {err}')

