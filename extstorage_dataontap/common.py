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

from extstorage_dataontap import configuration

ch = logging.StreamHandler(sys.stderr)
formatter = logging.Formatter("%(asctime)-15s [%(levelname)s] %(message)s")
ch.setFormatter(formatter)
LOG = logging.getLogger()
LOG.addHandler(ch)
LOG.setLevel(logging.DEBUG if configuration.DEBUG else logging.INFO)

if configuration.PROXY_STORAGE_FAMILY == 'ontap_cluster':
    from extstorage_dataontap.provider_cmode import DataOnTapProvider
else:
    from extstorage_dataontap.provider_7mode import DataOnTapProvider


def main(action):
    """Entry point"""
    provider = DataOnTapProvider()
    return getattr(provider, action)()


# Available ExtStorage actions
actions = ['create', 'attach', 'detach', 'remove', 'grow', 'setinfo', 'verify',
           'snapshot', 'open', 'close']

for action in actions:
    setattr(sys.modules[__name__], action, partial(main, action=action))
