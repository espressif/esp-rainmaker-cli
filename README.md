# ESP RainMaker Command Line utility

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

Please check the [CLI Usage guide](https://rainmaker.espressif.com/docs/cli-usage.html) for more information.

For more help, you can also run the following command:

```
esp-rainmaker-cli --help
```

## Development Guide

Development mode allows you to run the latest version of esp-rainmaker-cli from the repository.
If you are making any changes to the tool then in order to test the changes please follow the below steps.

```
python3 -m pip install -e .
```

This will install esp-rainmaker-cli's dependencies and create an executable script wrappers in the user’s bin
directory. The wrappers will run the scripts found in the git working directory directly, so any time the working
directory contents change it will pick up the new versions.
