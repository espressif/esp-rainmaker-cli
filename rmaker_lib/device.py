# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

from rmaker_lib.logger import log


class Device:
    """
    Device class used to instantiate instances of device
    to perform various device operations.
    """
    def __init__(self, node, device):
        """
        Instantiate device object.
        """
        log.info("Initialising device " + device['name'])
        self.__node = node
        self.__name = device['name']
        self.__params = {}
        for param in device['params']:
            self.__params[param["name"]] = ''

    def get_device_name(self):
        """
        Get the device name.
        """
        return self.__name

    def get_params(self):
        """
        Get parameters of the device.
        """
        params = {}
        node_params = self.__node.get_node_params()
        if node_params is None:
            return params
        for key in self.__params.keys():
            params[key] = node_params[self.__name + '.' + key]
        return params

    def set_params(self, data):

        """
        Set parameters of the device.
        Input data contains the dictionary of device parameters.
        """
        request_payload = {}
        for key in data:
            request_payload[self.__name + '.' + key] = data[key]
        return self.__node.set_node_params(request_payload)
