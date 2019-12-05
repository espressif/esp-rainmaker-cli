#!/usr/bin/env python
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

import os
import sys
from sys import exit
import time
import serial
import requests
import json
import argparse
import collections
if os.getenv('IDF_PATH'):
    sys.path.insert(0, os.path.join(os.getenv('IDF_PATH'), 'components', 'esptool_py', 'esptool'))
else:
    print("Please set the IDF_PATH environment variable.")
    exit(0)
import esptool
from datetime import datetime
from datetime import timedelta

# Claiming credentials
CLAIM_BASE_URL = "https://3u4klz774g.execute-api.us-east-2.amazonaws.com/Prod/"
CLAIM_INITIATE_URL = CLAIM_BASE_URL+"initiate"
CLAIM_VERIFY_URL = CLAIM_BASE_URL+"verify"

class cmd_interpreter:
    """
    This class is for is the command line interaction with the Init1 firmware for manufacturing.
    It executes the specified commands and returns its result.
    It is a stateless, does not maintain the current state of the firmware. 
    """
    def __init__(self, port):
        # Serial Port settings
        self.port = serial.Serial()
        self.port.baudrate = 115200
        self.port.dtr = 0
        self.port.rts = 0
        self.port.timeout = 2
        self.port.port = port
        self.port.open()

    def wait_for_init(self):
        retry_count = 0
        
        while True:
            line = self.port.readline()
            if line == b'':
                break
        
        self.port.write(b'\r')
        while True:
            line = self.port.readline()
            # if b'>>' in line or '>>' in line:
            if line.find(b">>"):
                print("- CLI Initialised")
                return True
            elif retry_count == 3:
                return False
            retry_count += 1

    def exec_cmd(self, command, args = None):
        ret = ""
        status = None
        self.port.write(command.encode())
        self.port.write(b'\r')

        if args:
            time.sleep(0.1)
            self.port.write(args.encode())
            self.port.write(b'\0')

        while True:
            line = self.port.readline()
            sys.stdout.flush()
            sys.stdout.write(line.decode(sys.stdout.encoding))
            if b'Status: Success' in line:
                status = True
            elif b'Status: Failure' in line:
                status = False
            if status == True or status == False:
                while True:
                    line = self.port.readline()
                    if b">>" in line:
                        if status == True:
                            print(line)
                        break
                    else:
                        ret += line.decode(sys.stdout.encoding)
                return [{"Status": status}, {"Return": ret}]

    def send_command(self, command, data = None):
            retval = self.exec_cmd(command, data)
            if retval[0]['Status'] != True:
                print("Error executing " + command)
                print(retval[1]['Return'])
                exit(0)
            return retval[1]['Return']

def read_mac(esp, port):
    esp.detect_chip(port)
    mac = esp.read_mac()
    return ''.join(map(lambda x: '%02X' % x, mac))

def load_app_stub(esp):
    arg_tuple = collections.namedtuple('ram_image', ['filename'])
    #args = arg_tuple('./cert_provision_stub.bin')
    args = arg_tuple(os.path.dirname(os.path.abspath(__file__)) + '/cert_provision_stub.bin')
    esp.change_baud( baud = 921600)
    try:
        esptool.load_ram(esp, args)
    except Exception as err:
        print(err)

def claim(args):

    start=time.time()
    try:
        esputils = esptool.ESP32ROM(port = args.port)
    except serial.serialutil.SerialException:
        print("Error. Please set the apt serial port.")
        exit(0)
    mac = read_mac(esputils, args.port)
    print(mac)

    print("Uploading application stub")
    result = load_app_stub(esputils)
    print(result)

    init_mfg = cmd_interpreter(port=args.port)
    err = "failed to execute"
    
    retval = init_mfg.wait_for_init()
    if retval != True:
        print("CMD prompt timed out.")
        exit(0)

    if args.verbose == True:
        init_mfg.send_command("verbose")

    # Generate Key
    init_mfg.send_command("generate-keys RSA 2048")
    
    # Generate CSR
    ret = init_mfg.send_command("generate-csr \"CN="+mac+"\"")
    csr = ret.strip('\r\n')
    print(csr)

    # Sign the CSR using the CA
    try:
        # Claim Initiate request
        claim_initiate_data = {"device-id":mac, "csr":csr}
        claim_initiate_encoded_data = str(claim_initiate_data).replace("'", '"')

        claim_initiate_response = requests.post(url = CLAIM_INITIATE_URL, data = claim_initiate_encoded_data)
        if claim_initiate_response.status_code != 200:
            print("Claim Initiate failed.\n" + claim_initiate_response.text)
            exit(0)
        claim_id = str(json.loads(claim_initiate_response.text)['claim-id'])
        hmac_challenge = str(json.loads(claim_initiate_response.text)['challenge'])
        
        ret = init_mfg.send_command("hmac-challenge "+ hmac_challenge)
        hmac_challenge_response = ret.strip('\n')
        print(hmac_challenge_response)

        # Claim verify request
        claim_verify_data = {"claim-id": claim_id, "challenge-response":hmac_challenge_response}
        claim_verify_encoded_data = str(claim_verify_data).replace("'", '"')

        claim_verify_reponse = requests.post(url = CLAIM_VERIFY_URL, data = claim_verify_encoded_data)
        if claim_verify_reponse.status_code != 200:
            print("Claim Verify failed.\n" + claim_verify_reponse.text)
            exit(0)
        device_cert = str(json.loads(claim_verify_reponse.text)['certificate']) + str(json.loads(claim_verify_reponse.text)['cacert'])
    except requests.ConnectionError:
        print("Error. Please check the Internet connection")
        exit(0)

    # Input Device Cert
    init_mfg.send_command("input-dev-cert", device_cert)

    # Input CA Cert
    ca_cert_data = str(json.loads(claim_verify_reponse.text)['cacert'])
    
    certAddr=str(int(args.certAddr, 0))
    init_mfg.send_command("cert_write " + certAddr)

    print("Time(s):"+str(time.time() - start))
