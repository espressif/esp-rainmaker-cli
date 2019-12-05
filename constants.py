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
from config import VERSION, STAGE

GET_METHOD = 'GET'
POST_METHOD = 'POST'
PUT_METHOD = 'PUT'
QUESTION_MARK = '?'
FORWORD_SLASH = '/'
NEWLINE = '\n'
EMPTY_STRING = ''
SERVICE_NAME = 'execute-api'
INDEX_PAGE = 'welcome.html'
HTTPS_PREFIX = 'https://'
PATH_PREFIX = FORWORD_SLASH + STAGE + FORWORD_SLASH + VERSION + FORWORD_SLASH
CLI_PATH_PREFIX = PATH_PREFIX + 'cli/'
CONTENT_TYPE_JSON = 'application/json'
ERROR_JSON_DECODE = 'Decoding data failed. Please enter valid data'
CONFIG_DIRECTORY = '.espressif/rainmaker'
CONFIG_FILE = CONFIG_DIRECTORY +'/rainmaker_config'
HOME_DIRECTORY = '~/'
DEFAULT = 'default'
SHA256_ALGORITHM = 'AWS4-HMAC-SHA256'
AWS_REQUEST = 'aws4_request'
NEW_PASSWORD_REQUIRED = 'NEW_PASSWORD_REQUIRED'
MAX_PASSWORD_CHANGE_ATTEMPT = 3
TRANSPORT_MODE_SOFTAP = "softap"
MAX_CONNECTION_RETRIES = 5
ADD_OPERATION = 'add'
ACCESS_KEY = 'accessKey'
SECRET_ACCESS_KEY = 'secretAccessKey'
MINIMUM_PROTOBUF_VERSION = '3.10.0'