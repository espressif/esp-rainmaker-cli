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

import os
import logging as log
from datetime import datetime

if not os.path.exists('logs'):
    os.makedirs('logs')

dateTimeObj = datetime.now()
log_filename = "logs/log_" + dateTimeObj.strftime("%d-%m-%Y_%H:%M:%S") +".log"
log.basicConfig(
    filename=log_filename,
    level=log.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s"
    )