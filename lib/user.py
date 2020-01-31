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

import json, requests, getpass
from lib import projectconfig, configmanager, session
from lib.exceptions import *
from lib.logger import log

class User:
    """
    User class used to instantiate instances of user to perform various user operations.
    """
    def __init__(self, username):
        """
        Instantiate user with username.
        """
        log.info("Initialising user " + username)
        self.__username = username
        self.__passwd_change_token = ''
        self.__request_header = {'content-type': 'application/json'}

    def signup_request(self, password):
        """
        Sign up request for ESP Rainmaker.
        """
        log.info("Creating new user with username : " + self.__username)
        path = 'user'
        signup_info = {
            'user_name' : self.__username,
            "password" : password
            }
        signup_url = projectconfig.HOST + path

        try:
            log.debug("Signup request url : " + signup_url)
            response = requests.post(url = signup_url, data = json.dumps(signup_info), headers=self.__request_header)
            log.debug("Signup request response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except:
            raise Exception(response.text)
        log.info("Signup request sent successfully.")
        return True

    def signup(self, code):
        """
        Sign up for ESP Rainmaker.
        """
        log.info("Confirming user with username : " + self.__username)
        path = 'user'
        signup_info = {
            'user_name' : self.__username,
            "verification_code" : code
            }
        signup_url = projectconfig.HOST + path

        try:
            log.debug("Confirm user request url : " + signup_url)
            response = requests.post(url = signup_url, data = json.dumps(signup_info), headers=self.__request_header)
            log.debug("Confirm user response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except:
            raise Exception(response.text)
        log.info("Signup successful.")
        return True

    def login(self, password=None):
        """
        User login to the ESP Rainmaker.
        """
        log.info("User login with username : " + self.__username)
        if password is None:
            password = getpass.getpass()
        path = 'login/'
        login_info = {
            'user_name' : self.__username,
            'password' : password
            }
        login_url = projectconfig.HOST + path

        try:
            log.debug("Login request url : " + login_url)
            response = requests.post(url = login_url, data = json.dumps(login_info), headers=self.__request_header)
            log.debug("Login response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except:
            raise Exception(response.text)

        try:
            result = json.loads(response.text)
        except Exception as jsonDecodeError:
            raise jsonDecodeError

        if 'status' in result and result['status'] == 'success':
            log.info("Login successful.")
            configData = {}
            configData['idtoken'] = result['idtoken']
            configData['refreshtoken'] = result['refreshtoken']
            configmanager.Config().set_config(configData)
            return session.Session()
        raise AuthenticationError

    # User has to call forgot_password two times
    # First call without arguments to request forgot password
    # Second call to reset the password with arguments password and verification_code
    def forgot_password(self, password=None, verification_code=None):
        """
        Forgot password request to reset the password.
        """
        log.info("Forgot password request for user : " + self.__username)
        path = 'forgotpassword'
        forgot_password_info = {
            'user_name' : self.__username,
            "password" : password,
            "verification_code" : verification_code
            }
        forgot_password_url = projectconfig.HOST + path
        try:
            log.debug("Forgot password request url : " + forgot_password_url)
            response = requests.put(url = forgot_password_url, data = json.dumps(forgot_password_info), headers=self.__request_header)
            log.debug("Forgot password response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except:
            raise Exception(response.text)
        log.info("Changed password successfully.")
        return True
