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

import json, sys, re
import getpass
import time
try:
    from lib import user
    from lib.exceptions import *
    from lib.logger import log
except Exception as importError:
    print("Failed to import ESP Rainmaker library. " + importError)
    sys.exit(1)
    
from cmd.browserlogin import browser_login

MAX_PASSWORD_CHANGE_ATTEMPTS = 3

def signup(args):
    """
    User signup to the ESP Rainmaker.
    :param args:
    a) username  - Email address of the user
    """
    log.info('Signing up the user ' + args.email)
    u = user.User(args.email)
    password = get_password()
    try:
        status = u.signup_request(password)
    except Exception as signupError:
        log.error(signupError)
    else:
        if status is True:
            verification_code = input('Enter verification code sent on your Email.\nVerification Code : ')
            try:
                status = u.signup(verification_code)
            except Exception as signupError:
                log.error(signupError)
                return
            print('Signup Successful\nPlease login to continue with ESP Rainmaker CLI')
        else:
            log.error('Signup failed. Please try again.')
    return

def login(args):
    """
    First time login of the user to reset the password.
    :param args:
    a) username  - Email address of the user
    """
    log.info('Signing in the user. Username  ' + str(args.email))
    if args.email is None :
        browser_login()
        return
    u = user.User(args.email)
    try:
        status = u.login()
    except Exception as loginError:
        log.error(loginError)
    else:
        print('Login Successful')

def forgot_password(args):
    """
    Forgot password request to reset the password.
    :param args:
    a) username  - Email address of the user
    """
    log.info('Changing user password. Username ' + args.email)
    u = user.User(args.email)
    status = False
    try:
        status = u.forgot_password()
    except Exception as forgotPasswdError:
        log.error(forgotPasswdError)
    else:
        verification_code = input('Enter verification code sent on your Email.\nVerification Code : ')
        password = get_password()
        if status is True:
            try:
                log.debug('Received verification code on email ' + args.email)
                status = u.forgot_password(password, verification_code)
            except Exception as forgotPasswdError:
                log.error(forgotPasswdError)
            else:
                print('Password changed successfully. Please login with the new password.')
        else:
            log.error('Failed to reset password. Please try again.')
    return

def get_password():
    """
    Does basic password validation checks.
    """
    log.info('Doing basic password confirmation checks.')
    password_policy = '8 characters, 1 digit, 1 uppercase and 1 lowercase.'
    password_change_attempt = 0

    print('Choose a password')
    while password_change_attempt < MAX_PASSWORD_CHANGE_ATTEMPTS:
        log.debug('Password change attempt number ' + str(password_change_attempt+1))
        password = getpass.getpass('Password : ')
        if len(password) < 8 or re.search(r"\d", password) is None or re.search(r"[A-Z]", password) is None or re.search(r"[a-z]", password) is None:
            print('Password should contain at least', password_policy)
            password_change_attempt += 1
            continue
        confirm_password = getpass.getpass('Confirm Password : ')
        if password == confirm_password:
            return password
        else:
            print('Passwords do not match!\nPlease enter the password again ..')
        password_change_attempt += 1
    
    log.error('Maximum attempts to change password over. Please try again.')
    sys.exit(1)