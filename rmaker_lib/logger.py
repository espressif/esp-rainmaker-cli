# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import os
import logging
from logging import handlers
from datetime import datetime

log_base_path = os.path.dirname(os.path.dirname(__file__))
# Use environment variable for log directory if available (for Lambda compatibility)
log_dir_path = os.environ.get('RMAKER_CLI_LOG_DIR', os.path.join(log_base_path, 'logs'))

if not os.path.exists(log_dir_path):
    os.makedirs(log_dir_path, exist_ok=True)

date_time_obj = datetime.now()
log_filename = os.path.join(log_dir_path, "rmaker_cli_" + date_time_obj.strftime("%Y-%m-%d") + ".log")

log = logging.getLogger("CLI_LOGS")
file_formatter = logging.Formatter('%(asctime)s:[%(funcName)s]:\
[%(levelname)s]:%(message)s')
console_formatter = logging.Formatter('[%(levelname)s]:%(message)s')
log.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_handler.setFormatter(console_formatter)

file_handler = handlers.RotatingFileHandler(log_filename,
                                            maxBytes=1024 * 1024,
                                            backupCount=300)
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)

log.addHandler(file_handler)
log.addHandler(console_handler)
