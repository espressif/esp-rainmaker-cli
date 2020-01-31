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

import os
import platform
from io import StringIO
import sys
from sys import exit
import time
import serial
import requests
import json
import argparse
import collections
from lib.logger import log
from datetime import datetime
from datetime import timedelta
from tools.esp_rainmaker_claim.claim_config import *

class cmd_interpreter:
    """
    This class is for the command line interaction with the Init1 firmware for manufacturing.
    It executes the specified commands and returns its result.
    It is a stateless, does not maintain the current state of the firmware. 
    """
    def __init__(self, port):
        # Serial Port settings
        self.port = serial.Serial()
        self.port.baudrate = 115200
        self.port.timeout = 2
        if platform.system() == 'Windows':
            self.port.dtr = False
            self.port.rts = False
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
                log.error("Executing " + command + " failed")
                print(retval[1]['Return'])
                exit(0)
            return retval[1]['Return']

def read_mac(port, esptool):
    sys.stdout = mystdout = StringIO()
    command=['--port', port, 'read_mac']
    esptool.main(command)
    sys.stdout = sys.__stdout__
    # Finds the first occurence of the line with the MAC Address from read_mac's output.
    mac = next(filter(lambda line: 'MAC: ' in line ,mystdout.getvalue().splitlines()))
    return mac.split('MAC: ')[1].replace(':','').upper()
 
def load_app_stub(port, esptool):
    arg_tuple = collections.namedtuple('ram_image', ['filename'])
    args = arg_tuple(os.path.dirname(os.path.abspath(__file__)) + '/bin/cert_provision_stub.bin')
    try:
        bin_path=os.path.dirname(os.path.abspath(__file__)) + '/bin/cert_provision_stub.bin'
        command=['--baud','921600','--port', port,'load_ram', bin_path]
        esptool.main(command)
    except Exception as err:
        log.error(err)
        sys.exit(1)

def claim(port, certAddr='0xd000'):

    if os.getenv('IDF_PATH'):
        sys.path.insert(0, os.path.join(os.getenv('IDF_PATH'), 'components', 'esptool_py', 'esptool'))
    else:
        log.error("Please set the IDF_PATH environment variable.")
        exit(0)
    import esptool

    start=time.time()
    mac = read_mac(port, esptool)

    print("Uploading application stub")
    rresult = load_app_stub(port, esptool)

    init_mfg = cmd_interpreter(port=port)
    err = "failed to execute"
    
    retval = init_mfg.wait_for_init()
    if retval != True:
        log.error("Command prompt timed out.")
        exit(0)

    # Generate Key
    init_mfg.send_command("generate-keys RSA 2048")
    
    # Generate CSR
    ret = init_mfg.send_command("generate-csr \"CN="+mac+"\"")
    csr = ret.strip('\r\n')
    print(csr)

    # Sign the CSR using the CA
    try:
        # Claim initiate request
        claim_initiate_data = {"device-id":mac, "csr":csr}
        claim_initiate_encoded_data = str(claim_initiate_data).replace("'", '"')

        claim_initiate_response = requests.post(url = CLAIM_INITIATE_URL, data = claim_initiate_encoded_data)
        if claim_initiate_response.status_code != 200:
            log.error("Claim initiate failed.\n" + claim_initiate_response.text)
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
            log.error("Claim verification failed.\n" + claim_verify_reponse.text)
            exit(0)
        device_cert = str(json.loads(claim_verify_reponse.text)['certificate']) + str(json.loads(claim_verify_reponse.text)['cacert'])
    except requests.ConnectionError:
        log.error("Please check the Internet connection.")
        exit(0)

    # Input Device Cert
    init_mfg.send_command("input-dev-cert", device_cert)

    # Input CA Cert
    ca_cert_data = str(json.loads(claim_verify_reponse.text)['cacert'])
    
    certAddr=str(int(certAddr, 0))
    init_mfg.send_command("cert_write " + certAddr)

    print("Time(s):"+str(time.time() - start))
