# ESP RainMaker CLI

[![PyPI version](https://img.shields.io/pypi/v/esp-rainmaker-cli)](https://pypi.org/project/esp-rainmaker-cli/)

Welcome to the `esp-rainmaker-cli` repository!

This repository contains the source of ESP RainMaker Command Line utility.

## About RainMaker

[ESP RainMaker](https://github.com/espressif/esp-rainmaker)
is an end-to-end solution offered by Espressif to enable remote control and
monitoring for ESP32 based products without any configuration required in the Cloud.

## How to install

[esp-rainmaker-cli](https://pypi.org/project/esp-rainmaker-cli) is available on Python Package Index (PyPI).
It can be installed using pip.

```
python3 -m pip install esp-rainmaker-cli
```

## Usage

Please check the [CLI Usage guide](docs/README.md) for more information.

For more help, you can also run the following command:

```
esp-rainmaker-cli --help
```

## Key Features

### 🔧 Enhanced Device Provisioning
Support for BLE, SoftAP, and Console transport modes with Security 0/1/2 schemes. Use the new `--pop` flag for cleaner syntax.
```bash
esp-rainmaker-cli provision --pop abcd1234 --transport ble --device_name PROV_device
```

### ⚡ ESP Local Control
Direct device communication on your local network with 5-10x faster response times using the `--local` flag.

For detailed documentation, see [Provisioning Guide](docs/commands/provisioning.md) and [ESP Local Control Guide](docs/commands/local_control.md).

## Development Guide

Development mode allows you to run the latest version of esp-rainmaker-cli from the repository.
If you are making any changes to the tool then in order to test the changes please follow the below steps.

```
python3 -m pip install -e .
```

This will install esp-rainmaker-cli's dependencies and create an executable script wrappers in the user's bin
directory. The wrappers will run the scripts found in the git working directory directly, so any time the working
directory contents change it will pick up the new versions.
