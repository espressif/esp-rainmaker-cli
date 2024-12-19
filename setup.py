#-!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import sys

def get_install_requires():
    with open(os.path.realpath('requirements.txt')) as f:
        required = f.read().splitlines()
        return required

try:
    from setuptools import find_packages, setup
except ImportError:
    print(
        "Package setuptools is missing from your Python installation. "
        "Please see the installation section in the esp-matter-mfg-tool "
        "documentation for instructions on how to install it."
    )
    exit(1)

VERSION = "1.1.3"

long_description = """
=================
esp-rainmaker-cli
=================
ESP RainMaker command-line interface (CLI) utility, python utility to perform host based claiming.

Source code for `esp-rainmaker-cli` is
`hosted on github <https://github.com/espressif/esp-rainmaker-cli>`_.

Documentation
-------------
Visit online `RainMaker CLI setup and usage guide <https://rainmaker.espressif.com/docs/cli-setup>`_.
Or run `esp-rainmaker-cli -h`.

License
-------
The License for the project can be found
`here <https://github.com/espressif/esp-rainmaker-cli/tree/master/LICENSE>`_
"""

setup(
    name = "esp-rainmaker-cli",
    version = VERSION,
    description = "A python utility to perform host based claiming",
    long_description = long_description,
    long_description_content_type = 'text/x-rst',
    url = "https://github.com/espressif/esp-rainmaker-cli",

    project_urls = {
        "Documentation": "https://rainmaker.espressif.com/docs/cli-setup",
        "Source": "https://github.com/espressif/esp-rainmaker-cli",
    },

    author = "Espressif Systems",
    author_email = "",
    license = "Apache-2.0",

    classifiers = [
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Topic :: Software Development :: Embedded Systems",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],

    python_requires = ">=3.9",
    setup_requires = (["wheel"] if "bdist_wheel" in sys.argv else []),
    install_requires = get_install_requires(),
    include_package_data = True,
    packages = find_packages(),
    package_data = {
        'server_cert':['server_cert.pem'],
        'rmaker_cmd':['html/*.html'],
    },
    entry_points={
        'console_scripts': [
            'esp-rainmaker-cli = rainmaker.rainmaker:main',
        ],
    },
)
