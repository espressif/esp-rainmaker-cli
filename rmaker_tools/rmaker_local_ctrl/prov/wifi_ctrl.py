# SPDX-FileCopyrightText: 2018-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

"""Wi-Fi control helpers reused from the shared provisioning module."""

try:
    from ...common.prov.wifi_ctrl import *  # noqa: F401,F403
except ImportError:  # pragma: no cover - pip package fallback
    from rmaker_tools.common.prov.wifi_ctrl import *  # noqa: F401,F403
