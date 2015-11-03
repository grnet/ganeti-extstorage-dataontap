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

"""Module hosting the configuration options of the driver. All other modules
access the settings by importing this one."""

import os
import sys
import re

from functools import partial

# import the default options
from extstorage_dataontap.configuration.default import *  # noqa

from extstorage_dataontap import exception

CONFIG = os.environ.get('EXTP_CONFIG', '/etc/extstorage_dataontap.conf')
OSTYPES = ('solaris', 'windows', 'hpux', 'aix', 'linux', 'netware', 'vmware',
           'windows_gpt', 'windows_2008', 'xen', 'hyper_v', 'solaris_efi',
           'openvms')

if os.path.exists(CONFIG):
    try:
        execfile(CONFIG)
    except Exception as e:
        raise exception.InvalidConfigurationFile(filename=CONFIG,
                                                 reason=str(e))


def _check_val(key, check):
    val = getattr(sys.modules[__name__], key)
    try:
        check(val)
    except ValueError as e:
        raise exception.InvalidConfigurationValue(option=key, value=val,
                                                  reason=e.message)


def _is_in(val_set):
    def inner(val, val_set):
        if val not in val_set:
            if isinstance(val_set, xrange):
                acceptable = "[%d-%d]" % (val_set[0], val_set[-1])
            else:
                acceptable = "{%s}" % ", ".join(val_set)
            raise ValueError("Acceptable values are: %s" % acceptable)
    return partial(inner, val_set=val_set)


def _is_none_or_in(val_set):
    def inner(val, val_set):
        if val is not None and val not in val_set:
            if isinstance(val_set, xrange):
                acceptable = "[%d-%d]" % (val_set[0], val_set[-1])
            else:
                acceptable = "{%s}" % ", ".join(val_set)
            raise ValueError("Acceptable values are: %s" % acceptable)
    return partial(inner, val_set=val_set)


def _is_nonempty_string(val):
    if not (isinstance(val, str) or isinstance(val, unicode)):
        raise ValueError("Not a string (%s)" % type(val))
    elif len(val) == 0:
        raise ValueError("String is empty")


def _is_float(val):
    if not (isinstance(val, float) or isinstance(val, int)):
        raise ValueError("Not a number (%s)" % type(val))


def _is_bool(val):
    if not isinstance(val, bool):
        raise ValueError("Not a boolean value (%s)" % type(val))


def _is_regexp(val):
    try:
        re.compile(val)
    except Exception as e:
        raise ValueError("Not a valid regular expression: %s" % e.message)


# Validate the configuration
_check_val('PROXY_STORAGE_FAMILY', _is_in(('ontap_cluster', 'ontap_7mode')))
_check_val('PROXY_STORAGE_PROTOCOL', _is_in(('iscsi', 'fc')))
_check_val('CONNECTION_PORT', _is_none_or_in(xrange(2**16)))
_check_val('CONNECTION_TRANSPORT_TYPE', _is_in(('http', 'https')))
_check_val('AUTH_LOGIN', _is_nonempty_string)
_check_val('AUTH_PASSWORD', _is_nonempty_string)
_check_val('PROVISIONING_SIZE_MULTIPLIER', _is_float)
_check_val('PROVISIONING_LUN_SPACE_RESERVATION', _is_bool)
_check_val('SAN_POOL_NAME_SEARCH_PATTERN', _is_regexp)
_check_val('SAN_LUN_OSTYPE', _is_in((OSTYPES)))