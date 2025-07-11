# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import json
import requests
import getpass
from rmaker_lib import configmanager, session
from rmaker_lib.exceptions import HttpErrorResponse, NetworkError, AuthenticationError, SSLError
from rmaker_lib.logger import log


class User:
    """
    User class used to instantiate instances of user to perform various
    user signup/login operations.

    :param username: Name of User
    :type username: str
    """
    def __init__(self, username, config=None):
        """
        Instantiate user with username.

        :param username: Name of User
        :type username: str
        :param config: Configuration object to use, defaults to None
        :type config: configmanager.Config
        """
        log.info("Initialising user " + username)
        self.__username = username
        self.__passwd_change_token = ''
        self.config = config if config is not None else configmanager.Config()
        self.__request_header = {'content-type': 'application/json'}

    def signup_request(self, password):
        """
        Sign up request of new User for ESP Rainmaker.

        :param password: Password to set for new user
        :type password: str

        :raises NetworkError: If there is a network connection issue
                              during signup request
        :raises Exception: If there is an HTTP issue during signup request

        :return: True on Success
        :rtype: bool
        """
        log.info("Creating new user with username : " + self.__username)
        path = 'user2'
        signup_info = {
            'user_name': self.__username,
            "password": password
            }
        signup_url = self.config.get_host() + path

        try:
            log.debug("Signup request url : " + signup_url)
            response = requests.post(url=signup_url,
                                     data=json.dumps(signup_info),
                                     headers=self.__request_header,
                                     verify=configmanager.CERT_FILE)
            log.debug("Signup request response : " + response.text)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Exception:
            raise Exception(response.text)
        log.info("Signup request sent successfully.")
        return True

    def signup(self, code):
        """
        Sign up of new User for ESP Rainmaker.

        :param code: Verification code received in signup request for user
        :type code: int

        :raises NetworkError: If there is a network connection issue
                              during signup
        :raises Exception: If there is an HTTP issue during signup

        :return: True on Success
        :rtype: bool
        """
        log.info("Confirming user with username : " + self.__username)
        path = 'user2'
        signup_info = {
            'user_name': self.__username,
            "verification_code": code
            }
        signup_url = self.config.get_host() + path

        try:
            log.debug("Confirm user request url : " + signup_url)
            response = requests.post(url=signup_url,
                                     data=json.dumps(signup_info),
                                     headers=self.__request_header,
                                     verify=configmanager.CERT_FILE)
            log.debug("Confirm user response : " + response.text)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Exception:
            raise Exception(response.text)
        log.info("Signup successful.")
        return True

    def login(self, password=None):
        """
        User login to the ESP Rainmaker.

        :param password: Password of user, defaults to `None`
        :type password: str

        :raises NetworkError: If there is a network connection issue
                              during login
        :raises Exception: If there is an HTTP issue during login or
                           JSON format issue in HTTP response
        :raises AuthenticationError: If login failed with the given parameters

        :return: :class:`rmaker_lib.session.Session` on Success
        :rtype: object
        """
        log.info("User login with username : " + self.__username)
        if password is None:
            password = getpass.getpass()
        path = 'login2'
        login_info = {
            'user_name': self.__username,
            'password': password
            }
        login_url = self.config.get_host() + path

        try:
            log.debug("Login request url : " + login_url)
            response = requests.post(url=login_url,
                                     data=json.dumps(login_info),
                                     headers=self.__request_header,
                                     verify=configmanager.CERT_FILE)
            log.debug("Login response : " + response.text)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Exception:
            raise Exception(response.text)

        try:
            result = json.loads(response.text)
        except Exception as json_decode_err:
            raise json_decode_err

        try:
            if 'status' in result and result['status'] == 'success':
                if result.get('session'):
                    otp_login_result = self.handle_otp_based_login(result['session'],)
                    if otp_login_result.get('status') == 'success':
                        result = otp_login_result
                log.info("Login successful.")
                config_data = {}
                config_data['idtoken'] = result['idtoken']
                config_data['refreshtoken'] = result['refreshtoken']
                config_data['accesstoken'] = result['accesstoken']
                configmanager.Config().set_config(config_data)
                return session.Session()
        except Exception as err:
            log.error(err)
            raise err
        raise AuthenticationError

    def handle_otp_based_login(self, login_session=None):
        """
       OTP based login for ESP RainMaker.

       :param login_session: Session param received in first login request
       :type login_session: str

       :raises NetworkError: If there is a network connection issue
                             during login
       :raises Exception: If there is an HTTP issue during login or
                          JSON format issue in HTTP response
       :raises AuthenticationError: If login failed with the given parameters

       :return: :class:`rmaker_lib.session.Session` on Success
       :rtype: Dict
        """
        # prompt for verification_code
        print("Sent OTP to your registered phone number/email ID: "+self.__username)
        verification_code = input("Enter verification code: ")
        path = 'login2'
        login_info = {
            'user_name': self.__username,
            'session': login_session,
            'verification_code': verification_code
        }
        login_url = self.config.get_host() + path

        try:
            log.debug("Login request url : " + login_url)
            response = requests.post(url=login_url,
                                     data=json.dumps(login_info),
                                     headers=self.__request_header,
                                     verify=configmanager.CERT_FILE)
            log.debug(login_info)
            log.debug("Login response : " + response.text)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(http_err)
        except requests.exceptions.SSLError as err:
            raise SSLError
        except requests.exceptions.ConnectionError as err:
            raise NetworkError
        except Exception as err:
            raise Exception(err)
        try:
            result = json.loads(response.text)
            if 'status' in result and result['status'] == 'success':
                return result
        except Exception as json_decode_err:
            raise json_decode_err
        raise AuthenticationError

    # User has to call forgot_password two times
    # First call without arguments to request forgot password
    # Second call to reset the password
    # with arguments password and verification_code

    def forgot_password(self, password=None, verification_code=None):
        """
        Forgot password request to reset the password.

        :param password: Password of user, defaults to `None`
        :type password: str

        :param verification_code: Verification code received during
                                  forgot password request, defaults to `None`
        :type verification_code: int

        :raises NetworkError: If there is a network connection issue
                              during password reset
        :raises Exception: If there is an HTTP issue during forgot password

        :return: True on Success
        :rtype: bool
        """
        log.info("Forgot password request for user : " + self.__username)
        path = 'forgotpassword2'
        forgot_password_info = {
            'user_name': self.__username,
            "password": password,
            "verification_code": verification_code
            }
        forgot_password_url = self.config.get_host() + path
        try:
            log.debug("Forgot password request url : " + forgot_password_url)
            response = requests.put(url=forgot_password_url,
                                    data=json.dumps(forgot_password_info),
                                    headers=self.__request_header,
                                    verify=configmanager.CERT_FILE)
            log.debug("Forgot password response : " + response.text)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Exception:
            raise Exception(response.text)
        log.info("Changed password successfully.")
        return True
