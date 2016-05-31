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
import string

from functools import partial
from extstorage_dataontap import exception

# import the default options
from extstorage_dataontap.configuration.default import *  # noqa


CONFIG = '/etc/extstorage_dataontap.conf'
OSTYPES = ('solaris', 'windows', 'hpux', 'aix', 'linux', 'netware', 'vmware',
           'windows_gpt', 'windows_2008', 'xen', 'hyper_v', 'solaris_efi',
           'openvms')

for var in [i for i in os.environ if i.startswith('EXTP_')]:
    value = os.environ[var] if len(os.environ[var]) else None
    setattr(sys.modules[__name__], var[5:], value)

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


def _match(pattern):
    def inner(val, pattern):
        regexp = re.compile(pattern)
        if not regexp.match(val):
            raise ValueError("Does not comply with pattern: %s" % pattern)
    return partial(inner, pattern=pattern)


def _is_format_string(val):
    fields = [i[1] for i in string.Formatter().parse(val)]
    if 'name' not in fields:
        raise ValueError("Field: `name' missing from format string: %s" % val)


def _is_list(val):
    if not (isinstance(val, tuple) or isinstance(val, list)):
        raise ValueError("Not a list or tuple (%s)" % type(val))


def _is_list_of_string_lists(val):
    _is_list(val)
    for i in val:
        try:
            _is_list(i)
        except ValueError as e:
            raise ValueError("Error in item %r: %s" % (i, e.message))
        if len(i) == 0:
            raise ValueError("Error in item %r: List is empty" % (i,))
        for j in i:
            try:
                _is_nonempty_string(j)
            except ValueError as e:
                raise ValueError("Error in item %r: %s" % (i, e.message))


# Validate the configuration
if STORAGE_FAMILY == 'ontap_cluster':
    # Not usable in cluster mode
    del SEVEN_MODE_VFILER  # noqa
    del SEVEN_MODE_PARTNER_BACKEND_NAME  # noqa
elif STORAGE_FAMILY == 'ontap_7mode':
    # Not usable in cluster mode
    del CLUSTER_MODE_VSERVER  # noqa
_check_val('STORAGE_FAMILY', _is_in(('ontap_cluster', 'ontap_7mode')))
_check_val('STORAGE_PROTOCOL', _is_in(('iscsi', 'fc')))
_check_val('PORT', _is_none_or_in(xrange(2**16)))
_check_val('TRANSPORT_TYPE', _is_in(('http', 'https')))
_check_val('VERIFY_CERT', _is_bool)
_check_val('LOGIN', _is_nonempty_string)
_check_val('PASSWORD', _is_nonempty_string)
_check_val('LUN_SPACE_RESERVATION', _is_bool)
_check_val('POOL_NAME_SEARCH_PATTERN', _is_regexp)
_check_val('LUN_OSTYPE', _is_in((OSTYPES)))
_check_val('POOL', _match(POOL_NAME_SEARCH_PATTERN))
_check_val('LUN_DEVICE_PATH_FORMAT', _is_format_string)
_check_val('LUN_ATTACH_COMMANDS', _is_list_of_string_lists)
_check_val('LUN_DETACH_COMMANDS', _is_list_of_string_lists)
