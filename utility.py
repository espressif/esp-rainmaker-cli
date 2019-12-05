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

import sys, os, base64, datetime, hashlib, hmac, json 
import requests
from constants import *
from config import *
from pathlib import Path
from configparser import *
from os import path
from logger import log
import errno

def getProfileCredentials(profile_name=DEFAULT):
    """
        Method to get the credentials for the given profile
        :param args:
        a) profile_name  - Profile name for wchich the access keys are required
        :return:
        pass - Credentials
        fail - Prints error message and exit
    """
    config = ConfigParser()
    file = Path(path.expanduser(HOME_DIRECTORY) + CONFIG_FILE)
    if not file.exists():
        print("User session is expired. Please login again")
        sys.exit(1)
        
    config.read([path.join(path.expanduser(HOME_DIRECTORY), CONFIG_FILE)])
    try:
        access_key = config.get(profile_name, 'accessKey')
        secret_access_key = config.get(profile_name, 'secretAccessKey')
    except ParsingError:
        print('Unable to find valid AWS credentials')
        sys.exit(1)
    return access_key, secret_access_key        

def setProfileCredentials(access_key, secret_access_key):
    """
        Method to set the credentials for the given profile
        :param args:
        a) profile_name  - Profile name for wchich the access keys are required
        :return:
        fail - Prints error message and exit
    """
    log.info("Setting configuration file for Rainmaker")
    
    config = ConfigParser()
    file = Path(path.expanduser(HOME_DIRECTORY) + CONFIG_FILE)
    if not file.exists():
        log.info("Config file does not exists. Creating new config file")
        try:
            os.makedirs(path.expanduser(HOME_DIRECTORY) + CONFIG_DIRECTORY)
        except OSError as err:
            if err.errno != errno.EEXIST:
                print("Creating config file failed ", err)
                return None

    with open(path.join(path.expanduser(HOME_DIRECTORY), CONFIG_FILE), 'w') as configfile:
        config.read([path.join(path.expanduser(HOME_DIRECTORY), CONFIG_FILE)])
        try:
            if not config.has_section(DEFAULT):
                config.add_section(DEFAULT)
        except Exception as err:
            print('Invalid section name: %r' % DEFAULT)
            return
        
        config[DEFAULT]['accessKey'] = access_key
        config[DEFAULT]['secretAccessKey'] = secret_access_key
        config.write(configfile) 
    return

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, AWS_REQUEST)
    return kSigning


def getHeader(method, path, query_parameters, request_payload=EMPTY_STRING):
    """
        Method to get the authorization header for the http request
        :param args:
        a) method           - HTTP method for the request (GET, PUT, POST)
        b) path             - Path parameters for the request
        c) query_parameters - Query parameters for the request
        d) request_payload  - Data to be sent for the request
        :return:
        pass - Request header
        fail - Prints error message and exit
    """
    # Read AWS access key from configuration file.
    access_key, secret_key = getProfileCredentials()
    if access_key is None or secret_key is None:
        print('No access key is available.')
        sys.exit(1)

    # Create a date for headers and the credential string
    t = datetime.datetime.utcnow()
    amzdate = t.strftime('%Y%m%dT%H%M%SZ')
    datestamp = t.strftime('%Y%m%d')

    canonical_uri = path
    canonical_querystring = query_parameters
    content_type = CONTENT_TYPE_JSON

    canonical_headers = 'content-type:' + content_type + NEWLINE + 'host:' + HOST + NEWLINE + 'x-amz-date:' + amzdate + NEWLINE
    signed_headers = 'content-type;host;x-amz-date'
    payload_hash = hashlib.sha256(request_payload.encode('utf-8')).hexdigest()
        
    # Combine elements to create canonical request
    canonical_request = method + NEWLINE + canonical_uri + NEWLINE + canonical_querystring + NEWLINE + canonical_headers + NEWLINE + signed_headers + NEWLINE + payload_hash

    algorithm = SHA256_ALGORITHM
    credential_scope = datestamp + FORWORD_SLASH + REGION + FORWORD_SLASH + SERVICE_NAME + FORWORD_SLASH + AWS_REQUEST
    string_to_sign = algorithm + NEWLINE +  amzdate + NEWLINE +  credential_scope + NEWLINE +  hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

    # Create the signing key using the function defined above.
    signing_key = getSignatureKey(secret_key, datestamp, REGION, SERVICE_NAME)

    # Sign the string_to_sign using the signing_key
    signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()

    authorization_header = algorithm + ' ' + 'Credential=' + access_key + FORWORD_SLASH + credential_scope + ', ' +  'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature

    headers = {'Content-Type':content_type,
           'X-Amz-Date':amzdate,
           'Authorization':authorization_header}

    return headers
