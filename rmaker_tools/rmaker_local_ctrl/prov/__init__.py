# SPDX-FileCopyrightText: 2018-2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#

# Import shared prov modules from common
try:
    from ...common.prov.wifi_prov import *  # noqa F403
    from ...common.prov.wifi_scan import *  # noqa F403
except ImportError:
    # Fallback for pip-installed packages
    from rmaker_tools.common.prov.wifi_prov import *  # noqa F403
    from rmaker_tools.common.prov.wifi_scan import *  # noqa F403
# Import module-specific files locally
from .custom_prov import *  # noqa F403
from .wifi_ctrl import *  # noqa F403
