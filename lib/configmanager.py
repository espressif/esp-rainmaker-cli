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

import json, errno, os, base64, time, requests
from pathlib import Path
from os import path

from lib import projectconfig
from lib.exceptions import *
from lib.logger import log

CONFIG_DIRECTORY = '.espressif/rainmaker'
CONFIG_FILE = CONFIG_DIRECTORY +'/rainmaker_config.json'
HOME_DIRECTORY = '~/'

class Config:

    def set_config(self, data):
        """
        Set the configuration file.
        """
        log.info("Configuring config file.")
        file = Path(path.expanduser(HOME_DIRECTORY) + CONFIG_FILE)
        if not file.exists():
            try:
                log.debug("Config directory does not exist, creating new directory.")
                os.makedirs(path.expanduser(HOME_DIRECTORY) + CONFIG_DIRECTORY)
            except OSError as setConfigError:
                log.error(setConfigError)
                if setConfigError.errno != errno.EEXIST:
                    raise setConfigError
        try:
            with open(path.join(path.expanduser(HOME_DIRECTORY), CONFIG_FILE), 'w') as configFile:
                json.dump(data, configFile)
        except Exception as setConfigError:
            raise setConfigError
        log.info("Configured config file successfully.")

    def get_config(self):
        """
        Get the configuration details from config file.
        """
        file = Path(path.expanduser(HOME_DIRECTORY) + CONFIG_FILE)
        if not file.exists():
            raise InvalidUserError
        try:
            with open(path.join(path.expanduser(HOME_DIRECTORY), CONFIG_FILE), 'r') as configFile:
                data = json.load(configFile)
                idtoken = data['idtoken']
                refresh_token = data['refreshtoken']
        except Exception as getConfigError:
            raise getConfigError    
        return idtoken, refresh_token

    def update_config(self, id_token):
        """
        Update the configuration file.
        """
        file = Path(path.expanduser(HOME_DIRECTORY) + CONFIG_FILE)
        if not file.exists():
            try:
                os.makedirs(path.expanduser(HOME_DIRECTORY) + CONFIG_DIRECTORY)
            except OSError as setConfigError:
                if setConfigError.errno != errno.EEXIST:
                    raise setConfigError
        try:
            with open(path.join(path.expanduser(HOME_DIRECTORY), CONFIG_FILE), 'r') as configFile:
                config_data = json.load(configFile)
                config_data['idtoken'] = id_token
            with open(path.join(path.expanduser(HOME_DIRECTORY), CONFIG_FILE), 'w') as configFile:
                json.dump(config_data, configFile)
        except Exception as setConfigError:
            raise setConfigError

    def get_token_attribute(self, attribute_name):
        """
        Get token attributes.
        """
        id_token, _ = self.get_config()
        token_payload = id_token.split('.')[1]
        if len(token_payload) % 4:
            token_payload += '=' * (4 - len(token_payload) % 4)
        try:
            str_token_payload = base64.b64decode(token_payload).decode("utf-8")
            # If user is logged in through github then to extend session we need 'cognito:username' (Github generated username) as email
            if attribute_name == 'email':
                if 'identities' in json.loads(str_token_payload):
                    return json.loads(str_token_payload)['cognito:username']
            attribute_value = json.loads(str_token_payload)[attribute_name]
        except:
            raise InvalidConfigError
        if attribute_value is None:
            raise InvalidConfigError
        return attribute_value

    def get_id_token(self):
        id_token, _ = self.get_config()
        if id_token is None:
            raise InvalidConfigError
        if self.__is_valid_idtoken(id_token) == False:
            username = self.get_token_attribute('email')
            refresh_token = self.get_refresh_token()
            id_token = self.__get_new_token(username, refresh_token)
            self.update_config(id_token)
        return id_token
       
    def get_user_id(self):
        return self.get_token_attribute('custom:user_id')

    def get_refresh_token(self):
        if self.__is_valid_version() == False:
            raise InvalidApiVersionError
        _, refresh_token = self.get_config()
        return refresh_token

    def __is_valid_idtoken(self, idtoken):
        token_payload = idtoken.split('.')[1]
        exp_timestamp = self.get_token_attribute('exp')
        current_timestamp = int(time.time())
        if exp_timestamp > current_timestamp:
            return True
        return False

    def __is_valid_version(self):
        log.info("Checking for supported version.")
        path = 'apiversions'
        request_url = projectconfig.HOST.split(projectconfig.VERSION)[0] + path
        try:
            log.debug("Version check request url : " + request_url)
            response = requests.get(url = request_url)
            log.debug("Version check response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except Exception as isValidVersionError:
            raise isValidVersionError

        try:
            response = json.loads(response.text)
        except Exception as jsonDecodeError:
            raise jsonDecodeError

        if 'supported_versions' in response:
            supported_versions = response['supported_versions']
            if projectconfig.VERSION in supported_versions:
                supported_versions.sort()
                latest_version = supported_versions[len(supported_versions) - 1]
                if projectconfig.VERSION < latest_version:
                    print("Please check the updates on GitHub for newer functionality enabled by " + latest_version + " APIs.")
                return True
        return False

    def __get_new_token(self, username, refresh_token):
        log.info("Extending user login session.")
        path = 'login'
        request_payload = { 
            'user_name'    :  username,
            'refreshtoken' : refresh_token
            }

        request_url = projectconfig.HOST + path
        try:
            log.debug("Extend session url : " + request_url)
            response = requests.post(url = request_url, data = json.dumps(request_payload))
            log.debug("Extend session response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except Exception as getNewTokenError:
            raise ExpiredSessionError

        try:
            response = json.loads(response.text)
        except Exception as getNewTokenError:
            raise ExpiredSessionError

        if 'idtoken' in response:
            log.info("User session extended successfully.")
            return response['idtoken']
        return None