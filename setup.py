#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import re

# Read version from version.py
with open(os.path.join('rainmaker', 'version.py'), 'r') as f:
    version_file = f.read()
    version_match = re.search(r'VERSION = "(.*?)"', version_file)
    VERSION = version_match.group(1)

def get_install_requires():
    with open(os.path.realpath('requirements.txt')) as f:
        required = f.read().splitlines()
        return required

def get_long_description():
    with open('README.md', 'r', encoding='utf-8') as f:
        readme = f.read()

    try:
        with open('CHANGELOG.md', 'r', encoding='utf-8') as f:
            changelog = f.read()
    except FileNotFoundError:
        changelog = ""

    return f"""{readme}

Changelog
---------
{changelog}
"""

try:
    from setuptools import find_packages, setup
except ImportError:
    print(
        "Package setuptools is missing from your Python installation. "
        "Please see the installation section in the esp-matter-mfg-tool "
        "documentation for instructions on how to install it."
    )
    exit(1)

setup(
    name = "esp-rainmaker-cli",
    version = VERSION,
    description = "A python utility to perform host based claiming",
    long_description = get_long_description(),
    long_description_content_type = 'text/markdown',
    url = "https://github.com/espressif/esp-rainmaker-cli",

    project_urls = {
        "Documentation": "https://rainmaker.espressif.com/docs/cli-setup",
        "Source": "https://github.com/espressif/esp-rainmaker-cli",
        "Changelog": "https://github.com/espressif/esp-rainmaker-cli/blob/master/CHANGELOG.md",
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
        '': ['CHANGELOG.md'],  # Include CHANGELOG.md in the package root
    },
    entry_points={
        'console_scripts': [
            'esp-rainmaker-cli = rainmaker.rainmaker:main',
        ],
    },
)
