# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#

# Import shared transport modules from common
try:
    from ...common.transport.transport_ble import *  # noqa: F403, F401
    from ...common.transport.transport_console import *  # noqa: F403, F401
    from ...common.transport.transport_http import *  # noqa: F403, F401
except ImportError:
    # Fallback for pip-installed packages
    from rmaker_tools.common.transport.transport_ble import *  # noqa: F403, F401
    from rmaker_tools.common.transport.transport_console import *  # noqa: F403, F401
    from rmaker_tools.common.transport.transport_http import *  # noqa: F403, F401
