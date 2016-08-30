# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 GRNET S.A.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import logging

from functools import partial

from extstorage_dataontap import configuration, version

LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG if configuration.DEBUG else logging.INFO)

if configuration.STORAGE_FAMILY == 'ontap_cluster':
    from extstorage_dataontap.provider_cmode import DataOnTapProvider
else:
    from extstorage_dataontap.provider_7mode import DataOnTapProvider


def main(action):
    """Entry point"""

    # This is logged directly by the client
    if configuration.LOG:
        fh = logging.FileHandler(configuration.LOGFILE)
        formatter = logging.Formatter("%(asctime)-15s [%(levelname)s][" +
                                      action.upper() + "] %(message)s")
        fh.setFormatter(formatter)
        LOG.addHandler(fh)

    # Ganeti will log what goes to stdout/stderr unless we are calling the
    # attach script. If this is the case, then we will have to mute the logger
    # because ganeti does not distinguish stdout and stderr and the expected
    # result is printed in the output.
    if action != 'attach':
        sh = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        sh.setFormatter(formatter)
        LOG.addHandler(sh)

    LOG.info("Running Data ONTAP ExtStorage Provider v%s", version)
    try:
        provider = DataOnTapProvider()
        return getattr(provider, action)()
    except Exception:
        LOG.exception("action: %s failed", action)
        return 2


# Available ExtStorage actions
actions = ['create', 'attach', 'detach', 'remove', 'grow', 'setinfo', 'verify',
           'snapshot', 'open', 'close']

# Hooks that need to be added to Ganeti
hooks = ['pre_move', 'post_remove']

for action in actions + hooks:
    setattr(sys.modules[__name__], action, partial(main, action=action))

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
