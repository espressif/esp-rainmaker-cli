# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import json
import errno
import os
import base64
import time
import requests
import socket
from pathlib import Path
from os import path
from rmaker_lib.logger import log
from rmaker_lib import serverconfig
from rmaker_lib.exceptions import NetworkError, \
    InvalidConfigError, \
    InvalidUserError, \
    InvalidApiVersionError, \
    ExpiredSessionError, \
    SSLError, \
    RequestTimeoutError
from rmaker_lib.constants import RM_CONFIG_FILE

# Import the new ProfileManager
from rmaker_lib.profile_manager import ProfileManager

# Default config directory - same as ProfileManager for consistency
DEFAULT_CONFIG_DIR = os.path.expanduser('~/.espressif/rainmaker')

CURR_DIR = os.path.dirname(__file__)
CERT_FILE = CURR_DIR + '/../server_cert/server_cert.pem'


class Config:
    """
    Config class used to set/get configuration for ESP Rainmaker.
    Now with profile-aware support for multi-profile management.
    """

    def __init__(self, config_dir=None, profile_override=None):
        """
        Initialize Config with ProfileManager integration.
        
        :param config_dir: Optional custom config directory. For testing purposes.
        :param profile_override: Optional profile name to use instead of current profile.
        """
        self.profile_manager = ProfileManager(config_dir)
        self.profile_override = profile_override
        
        if profile_override:
            # Validate that the override profile exists
            if not self.profile_manager.profile_exists(profile_override):
                raise ValueError(f"Profile '{profile_override}' does not exist")
            self.current_profile = profile_override
        else:
            self.current_profile = self.profile_manager.get_current_profile()
        
        # For backward compatibility, compute the legacy config file path
        self.config_dir = self.profile_manager.config_dir
        self.legacy_config_file = os.path.join(self.config_dir, RM_CONFIG_FILE)

    def get_current_profile_name(self):
        """Get the name of the currently active profile."""
        return self.current_profile

    def switch_profile(self, profile_name):
        """Switch to a different profile."""
        if self.profile_override:
            raise ValueError("Cannot switch profile when using profile override")
        self.profile_manager.set_current_profile(profile_name)
        self.current_profile = profile_name

    def get_profile_config_for_current(self):
        """Get the profile configuration for the current profile."""
        return self.profile_manager.get_profile_config(self.current_profile)

    def set_config(self, data: dict, config_file=None):
        """
        Set the configuration details to config file.
        Now profile-aware - handles both profile config and token storage.

        :params data: Config data to be stored to config file
        :type data: dict

        :params config_file: Config filename to write config data to (for compatibility)
        :type config_file: str

        :raises OSError: If there is an OS issue while creating new directory
                         for config file
        :raises Exception: If there is a FILE Handling error while writing
                           config to file

        :return: None on Success and Failure
        :rtype: None
        """
        # Use default config file if none specified
        if config_file is None:
            config_file = self.legacy_config_file
            
        # Extract token data if present
        idtoken = data.get('idtoken')
        refreshtoken = data.get('refreshtoken')
        accesstoken = data.get('accesstoken')
        
        # Save tokens to current profile if they exist
        if any([idtoken, refreshtoken, accesstoken]):
            self.profile_manager.set_profile_tokens(
                self.current_profile,
                idtoken=idtoken,
                refreshtoken=refreshtoken,
                accesstoken=accesstoken
            )
        
        # Handle profile configuration updates (for region switching)
        profile_config_keys = {
            'login_url', 'host', 'client_id', 'token_url', 
            'redirect_url', 'external_url', 'claim_base_url'
        }
        
        profile_config_data = {k: v for k, v in data.items() if k in profile_config_keys}
        
        if profile_config_data:
            # For backward compatibility, still save to legacy config file
            # This supports the existing region switching logic
            file = Path(config_file)
            if not file.exists():
                try:
                    os.makedirs(self.config_dir, exist_ok=True)
                except OSError as set_config_err:
                    if set_config_err.errno != errno.EEXIST:
                        raise set_config_err
            
            existing_data = {}
            if file.exists():
                try:
                    with open(config_file, 'r') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass  # Start with empty if file is corrupted
            
            existing_data.update(profile_config_data)
            
            try:
                with open(config_file, 'w') as f:
                    json.dump(existing_data, f)
            except Exception as set_config_err:
                raise set_config_err

    def unset_config(self, keys, curr_creds_file=None):
        """
        Unset the configuration file.

        :params keys: Keys to remove from config
        :type keys: set or list

        :params curr_creds_file: Config filename to delete config data from
        :type curr_creds_file: str

        :raises Exception: If there is a File Handling error while deleting
                           config file

        :return: None on Success and Failure
        :rtype: None
        """
        if not curr_creds_file:
            curr_creds_file = self.legacy_config_file
        try:
            # Read the JSON file
            with open(curr_creds_file, 'r') as file:
                data = json.load(file)
            # Delete specified keys if they exist
            for key in keys:
                if key in data:
                    del data[key]
            with open(curr_creds_file, 'w') as file:
                json.dump(data, file)
            log.info("...Success...")
            return True
        except Exception as e:
            log.debug("Removing keys from path {}. Failed: {}".format(
                curr_creds_file, e))
        return None

    def get_config(self, config_file=None):
        """
        Get the configuration details from config file.
        Now profile-aware - gets tokens for the current profile.

        :params config_file: Config filename to read config data from (kept for compatibility)
        :type data: str

        :raises Exception: If there is a File Handling error while reading
                           from config file

        :return:
            idtoken - Id Token from config saved\n
            refreshtoken - Refresh Token from config saved\n
            accesstoken - Access Token from config saved\n
        :rtype: str
        """
        # Use default config file if none specified
        if config_file is None:
            config_file = self.legacy_config_file
            
        # Use profile-based token storage
        idtoken, refresh_token, access_token = self.profile_manager.get_profile_tokens(self.current_profile)
        
        # If no profile tokens and we have legacy config, try migration
        if access_token is None and config_file == self.legacy_config_file:
            file = Path(config_file)
            if file.exists():
                try:
                    with open(config_file, 'r') as config_file_handle:
                        data = json.load(config_file_handle)
                        legacy_idtoken = data.get('idtoken')
                        legacy_refresh_token = data.get('refreshtoken')
                        legacy_access_token = data.get('accesstoken')
                        
                        if legacy_access_token:
                            # Migrate legacy tokens to current profile
                            self.profile_manager.set_profile_tokens(
                                self.current_profile,
                                idtoken=legacy_idtoken,
                                refreshtoken=legacy_refresh_token,
                                accesstoken=legacy_access_token
                            )
                            return legacy_idtoken, legacy_refresh_token, legacy_access_token
                except Exception as get_config_err:
                    log.debug(f"Failed to read legacy config: {get_config_err}")
        
        if access_token is None:
            raise InvalidUserError
            
        return idtoken, refresh_token, access_token

    def get_binary_config(self, config_file=None):
        """
        Get the configuration details from binary config file.

        :params config_file: Config filename to read config data from
        :type data: str

        :raises Exception: If there is a File Handling error while reading
                           from config file

        :return: Config data read from file on Success, None on Failure
        :rtype: str | None
        """
        # Use default config file if none specified
        if config_file is None:
            config_file = self.legacy_config_file
        
        file = Path(config_file)
        if not file.exists():
            return None
        try:
            with open(file, 'rb') as cfg_file:
                data = cfg_file.read()
                return data
        except Exception as get_config_err:
            raise get_config_err
        return

    def update_config(self, access_token, id_token):
        """
        Update the configuration file.
        Now profile-aware - updates tokens for the current profile.

        :params access_token: Access Token to update in config file
        :type access_token: str

        :params id_token: Id Token to update in config file
        :type id_token: str

        :raises OSError: If there is an OS issue while creating new directory
                         for config file
        :raises Exception: If there is a FILE Handling error while reading
                           from/writing config to file

        :return: None on Success and Failure
        :rtype: None
        """
        # Use profile-based token storage
        self.profile_manager.set_profile_tokens(
            self.current_profile,
            idtoken=id_token,
            accesstoken=access_token
        )

    def get_token_attribute(self, attribute_name, is_access_token=False):
        """
        Get access token attributes.

        :params attribute_name: Attribute Name
        :type attribute_name: str

        :params is_access_token: Is Access Token
        :type is_access_token: bool

        :raises InvalidConfigError: If there is an error in the config
        :raises Exception: If there is a File Handling error while reading
                           from/writing config to file

        :return: Attribute Value on Success, None on Failure
        :rtype: int | str | None
        """
        if is_access_token:
            log.debug('Getting access token for attribute ' + attribute_name)
            _, _, token = self.get_config()
        else:
            log.debug('Getting idtoken for attribute ' + attribute_name)
            token, _, _ = self.get_config()
        token_payload = token.split('.')[1]
        if len(token_payload) % 4:
            token_payload += '=' * (4 - len(token_payload) % 4)
        try:
            str_token_payload = base64.b64decode(token_payload).decode("utf-8")
            attribute_value = json.loads(str_token_payload)[attribute_name]
        except Exception:
            raise InvalidConfigError
        if attribute_value is None:
            raise InvalidConfigError
        return attribute_value

    def get_access_token(self):
        """
        Get Access Token for User

        :raises InvalidConfigError: If there is an issue in getting config
                                    from file

        :return: Access Token on Success
        :rtype: str
        """
        _, _, access_token = self.get_config()
        if access_token is None:
            raise InvalidConfigError
        if self.__is_valid_token() is False:
            print('Previous Session expired. Initialising new session...')
            log.info('Previous Session expired. Initialising new session...')
            refresh_token = self.get_refresh_token()
            access_token, id_token = self.__get_new_token(refresh_token)
            self.update_config(access_token, id_token)
            print('Previous Session expired. Initialising new session...'
                  'Success')
            log.info('Previous Session expired. Initialising new session...'
                     'Success')
        return access_token


    def get_user_name(self):
        """
       Get User Name(email or phone number) for user

       :raises InvalidConfigError: If there is an issue in getting config
                                from file

       :return: User name on Success
       :rtype: str
       """
        try:
            user_name = self.get_token_attribute('email')
        except InvalidConfigError:
            try:
                user_name = self.get_token_attribute('phone_number')
            except Exception as err:
                log.warn(
                    "Error occurred while getting user name from token, " + str(err))
                raise err
        except Exception as err:
            log.warn("Error occurred while getting user name from token, "+str(err))
            raise err
        return user_name

    def get_user_id(self):
        """
        Get User Id

        :return: Attribute value for attribute name passed
        :rtype: str
        """
        return self.get_token_attribute('custom:user_id')

    def get_refresh_token(self):
        """
        Get Refresh Token

        :raises InvalidApiVersionError: If current API version is not supported

        :return: Refresh Token
        :rtype: str
        """
        if self.__is_valid_version() is False:
            raise InvalidApiVersionError
        _, refresh_token, _ = self.get_config()
        return refresh_token

    def __is_valid_token(self):
        """
        Check if access token is valid i.e. login session is still active
        or session is expired

        :return True on Success and False on Failure
        :rtype: bool
        """
        log.info("Checking for session timeout.")
        exp_timestamp = self.get_token_attribute('exp', is_access_token=True)
        current_timestamp = int(time.time())
        if exp_timestamp > current_timestamp:
            return True
        return False

    def __is_valid_version(self):
        """
        Check if API Version is valid

        :raises NetworkError: If there is a network connection issue during
                              HTTP request for getting version
        :raises Exception: If there is an HTTP issue or JSON format issue in
                           HTTP response

        :return: True on Success, False on Failure
        :rtype: bool
        """
        socket.setdefaulttimeout(10)
        log.info("Checking for supported version.")
        path = 'apiversions'
        request_url = self.get_host().split(serverconfig.VERSION)[0] + path
        try:
            log.debug("Version check request url : " + request_url)
            response = requests.get(url=request_url, verify=CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Version check response : " + response.text)
            response.raise_for_status()
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.Timeout:
            raise RequestTimeoutError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Exception as ver_err:
            raise ver_err

        try:
            response = json.loads(response.text)
        except Exception as json_decode_err:
            raise json_decode_err

        if 'supported_versions' in response:
            supported_versions = response['supported_versions']
            if serverconfig.VERSION in supported_versions:
                supported_versions.sort()
                latest_version = supported_versions[len(supported_versions)
                                                    - 1]
                if serverconfig.VERSION < latest_version:
                    print('Please check the updates on GitHub for newer'
                          'functionality enabled by ' + latest_version +
                          ' APIs.')
                return True
        return False

    def __get_new_token(self, refresh_token):
        """
        Get new token for User Login Session

        :raises NetworkError: If there is a network connection issue during
                              HTTP request for getting token
        :raises Exception: If there is an HTTP issue or JSON format issue in
                           HTTP response

        :return: accesstoken and idtoken on Success, None on Failure
        :rtype: str | None

        """
        socket.setdefaulttimeout(10)
        log.info("Extending user login session.")
        path = 'login2'
        request_payload = {
            'refreshtoken': refresh_token
        }

        request_url = self.get_host() + path
        try:
            log.debug("Extend session url : " + request_url)
            response = requests.post(url=request_url,
                                     data=json.dumps(request_payload),
                                     verify=CERT_FILE,
                                     headers={'content-type': 'application/json'},
                                     timeout=(5.0, 5.0))
            response.raise_for_status()
            log.debug("Extend session response : " + response.text)
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except requests.exceptions.Timeout:
            raise RequestTimeoutError
        except Exception:
            raise ExpiredSessionError

        try:
            response = json.loads(response.text)
        except Exception:
            raise ExpiredSessionError

        if 'accesstoken' in response and 'idtoken' in response:
            log.info("User session extended successfully.")
            return response['accesstoken'], response['idtoken']
        return None

    def check_user_creds_exists(self):
        '''
        Check if user creds exist - now profile-aware
        '''
        return self.profile_manager.has_profile_tokens(self.current_profile)

    def get_input_to_end_session(self, email_id):
        '''
        Get input(y/n) from user to end current session
        '''
        while True:
            user_input = input(
                "This will end your current session for {}. Do you want to continue (Y/N)? :".format(email_id))
            if user_input not in ["Y", "y", "N", "n"]:
                print("Please provide Y/N only")
                continue
            elif user_input in ["N", "n"]:
                return False
            else:
                break
        return True

    def remove_curr_login_creds(self, curr_creds_file=None):
        '''
        Remove current login creds - now profile-aware
        '''
        log.info("Removing current login creds")
        try:
            self.profile_manager.clear_profile_tokens(self.current_profile)
            log.info("Previous login session ended. Removing current login creds...Success...")
            return True
        except Exception as e:
            log.debug("Removing current login creds for profile {}. Failed: {}".format(
                self.current_profile, e))
        return None

    def get_environment_config(self):
        """
        Get the configuration details from config file.

        :params config_file: Config filename to read config data from
        :type data: str

        :raises Exception: If there is a File Handling error while reading
                           from config file

        :return:
            login_url - Login URL
            host - Host URL
            client - Client ID
            token_url - Token URL
            redirect_url - Redirect URL
            external_url - External URL
            claim_base_url - Claim Base URL
        :rtype: str
        """
        config_file=self.legacy_config_file
        file = Path(config_file)

        if not file.exists():
            return None, None, None, None, None, None, None
        try:
            with open(config_file, 'r') as config_file:
                data = json.load(config_file)
                login_url = data.get('login_url')
                host = data.get('host')
                client = data.get('client_id')
                token_url = data.get('token_url')
                redirect_url = data.get('redirect_url')
                external_url = data.get('external_url')
                claim_base_url = data.get('claim_base_url')
        except Exception as get_config_err:
            raise get_config_err
        return login_url, host, client, token_url, redirect_url, external_url, claim_base_url
    
    def is_china_region(self):
        """
        Check if user is in china region - now profile-aware
        """
        return self.get_host() == serverconfig.HOST_CN
    
    def get_region(self):
        """
        Get the region - now profile-aware

        :return: Region
        :rtype: str
        """
        if self.current_profile == 'china':
            return 'china'
        elif self.current_profile == 'global':
            return 'global'
        else:
            # For custom profiles, just return the profile name
            return self.current_profile

    def get_login_url(self):
        """
        Get the login URL - now profile-aware

        :return: Login URL
        :rtype: str
        """
        # First try to get from current profile configuration
        try:
            profile_config = self.profile_manager.get_profile_config(self.current_profile)
            if 'login_url' in profile_config:
                return profile_config['login_url']
        except Exception:
            pass
        
        # Fall back to legacy environment config
        login_url, _, _, _, _, _, _ = self.get_environment_config()
        if login_url is None:
            return serverconfig.LOGIN_URL
        return login_url
    
    def get_host(self):
        """
        Get the host URL - now profile-aware

        :return: Host URL
        :rtype: str
        """
        # First try to get from current profile configuration
        try:
            profile_config = self.profile_manager.get_profile_config(self.current_profile)
            if 'host' in profile_config:
                return profile_config['host']
        except Exception:
            pass
        
        # Fall back to legacy environment config
        _, host, _, _, _, _, _ = self.get_environment_config()
        if host is None:
            return serverconfig.HOST
        return host

    def get_client(self):
        """
        Get the client ID - now profile-aware

        :return: Client ID
        :rtype: str
        """
        # First try to get from current profile configuration
        try:
            profile_config = self.profile_manager.get_profile_config(self.current_profile)
            if 'client_id' in profile_config:
                return profile_config['client_id']
        except Exception:
            pass
        
        # Fall back to legacy environment config
        _, _, client, _, _, _, _ = self.get_environment_config()
        if client is None:
            return serverconfig.CLIENT_ID
        return client

    def get_token_url(self):
        """
        Get the token URL - now profile-aware

        :return: Token URL
        :rtype: str
        """
        # First try to get from current profile configuration
        try:
            profile_config = self.profile_manager.get_profile_config(self.current_profile)
            if 'token_url' in profile_config:
                return profile_config['token_url']
        except Exception:
            pass
        
        # Fall back to legacy environment config
        _, _, _, token_url, _, _, _ = self.get_environment_config()
        if token_url is None:
            return serverconfig.TOKEN_URL
        return token_url
    
    def get_redirect_url(self):
        """
        Get the redirect URL - now profile-aware

        :return: Redirect URL
        :rtype: str
        """
        # First try to get from current profile configuration
        try:
            profile_config = self.profile_manager.get_profile_config(self.current_profile)
            if 'redirect_url' in profile_config:
                return profile_config['redirect_url']
        except Exception:
            pass
        
        # Fall back to legacy environment config
        _, _, _, _, redirect_url, _, _ = self.get_environment_config()
        if redirect_url is None:
            return serverconfig.REDIRECT_URL
        return redirect_url
    
    def get_external_url(self):
        """
        Get the external URL - now profile-aware

        :return: External URL
        :rtype: str
        """
        # First try to get from current profile configuration
        try:
            profile_config = self.profile_manager.get_profile_config(self.current_profile)
            if 'external_url' in profile_config:
                return profile_config['external_url']
        except Exception:
            pass
        
        # Fall back to legacy environment config
        _, _, _, _, _, external_url, _ = self.get_environment_config()
        if external_url is None:
            return serverconfig.EXTERNAL_LOGIN_URL
        return external_url
    
    def get_claim_base_url(self):
        """
        Get the claim base URL - now profile-aware

        :return: Claim base URL
        :rtype: str
        """
        # First try to get from current profile configuration
        try:
            profile_config = self.profile_manager.get_profile_config(self.current_profile)
            if 'claim_base_url' in profile_config:
                return profile_config['claim_base_url']
        except Exception:
            pass
        
        # Fall back to legacy environment config
        _, _, _, _, _, _, claim_base_url = self.get_environment_config()
        return claim_base_url