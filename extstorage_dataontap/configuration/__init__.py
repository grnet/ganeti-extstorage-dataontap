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
import logging
import subprocess

from functools import partial
from extstorage_dataontap import exception

# import the default options
from extstorage_dataontap.configuration.default import *  # noqa

LOG = logging.getLogger(__name__)

CONFIG = '/etc/ganeti/extstorage-dataontap.conf'
OSTYPES = ('solaris', 'windows', 'hpux', 'aix', 'linux', 'netware', 'vmware',
           'windows_gpt', 'windows_2008', 'xen', 'hyper_v', 'solaris_efi',
           'openvms')

TRUE_REGEXP = re.compile("^(yes|true|on|1|set)$", re.IGNORECASE)
FALSE_REGEXP = re.compile("^(no|false|off|0|unset)$", re.IGNORECASE)
BOOL_REGEXP = re.compile("%s|%s" % (TRUE_REGEXP.pattern[:-2],
                                    FALSE_REGEXP.pattern[2:]), re.IGNORECASE)

if os.path.exists(CONFIG):
    try:
        execfile(CONFIG)
    except Exception as e:
        raise exception.InvalidConfigurationFile(filename=CONFIG,
                                                 reason=str(e))

for var in [i for i in os.environ if i.startswith('EXTP_')]:
    value = os.environ[var] if len(os.environ[var]) else None
    setattr(sys.modules[__name__], var[5:], value)


def _check_val(key, check):
    """Check a configuration option against a check function"""
    val = getattr(sys.modules[__name__], key)
    try:
        check(val)
    except ValueError as e:
        raise exception.InvalidConfigurationValue(option=key, value=val,
                                                  reason=e.message)

    def set_bool(val):
        if isinstance(val, bool):
            return val
        return True if TRUE_REGEXP.match(val) else False

    # Fix boolean values
    if check == _is_bool:
        setattr(sys.modules[__name__], key, set_bool(val))


def _is_in(val_set):
    """Check if a value is included in a set of values"""
    def inner(val, val_set):
        if val not in val_set:
            if isinstance(val_set, xrange):
                acceptable = "[%d-%d]" % (val_set[0], val_set[-1])
            else:
                acceptable = "{%s}" % ", ".join(val_set)
            raise ValueError("Acceptable values are: %s" % acceptable)
    return partial(inner, val_set=val_set)


def _is_none_or_in(val_set):
    """Check if a value is None or is included in a set of values"""
    def inner(val, val_set):
        if val is not None and val not in val_set:
            if isinstance(val_set, xrange):
                acceptable = "[%d-%d]" % (val_set[0], val_set[-1])
            else:
                acceptable = "{%s}" % ", ".join(val_set)
            raise ValueError("Acceptable values are: %s" % acceptable)
    return partial(inner, val_set=val_set)


def _is_nonempty_string(val):
    """Check if value is a non-empty string"""
    if not (isinstance(val, str) or isinstance(val, unicode)):
        raise ValueError("Not a string (%s)" % type(val))
    elif len(val) == 0:
        raise ValueError("String is empty")


def _is_float(val):
    """Check if value is a floating point number"""
    if not (isinstance(val, float) or isinstance(val, int)):
        raise ValueError("Not a number (%s)" % type(val))


def _is_bool(val):
    """Check if a value is Boolean"""
    if not (isinstance(val, bool) or
            isinstance(val, str) or isinstance(val, unicode)):
        raise ValueError("Not a boolean value (%s)" % type(val))

    # Since some boolean values may be provided by environment variables, we
    # need to allow some strings like yes, no, true, set...
    if (isinstance(val, str) or isinstance(val, unicode)):
        if not BOOL_REGEXP.match(val):
            raise ValueError("Allowed values are %s" %
                             BOOL_REGEXP.pattern[1:-1])


def _is_regexp(val):
    """Check if a value is a regular exception"""
    try:
        re.compile(val)
    except Exception as e:
        raise ValueError("Not a valid regular expression: %s" % e.message)


def _match(pattern):
    """Check if a value matches a regular expresion"""
    def inner(val, pattern):
        regexp = re.compile(pattern)
        if not regexp.match(val):
            raise ValueError("Does not comply with pattern: %s" % pattern)
    return partial(inner, pattern=pattern)


def _is_format_string(val):
    """Check if the value is a python format string"""
    fields = [i[1] for i in string.Formatter().parse(val)]
    if 'name' not in fields:
        raise ValueError("Field: `name' missing from format string: %s" % val)


def _is_list(val):
    """Check if the value is a list or tupple"""
    if not (isinstance(val, tuple) or isinstance(val, list)):
        raise ValueError("Not a list or tuple (%s)" % type(val))


def _is_list_of_string_lists(val):
    """Check if the value is a list of string lists"""
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


def run_cmds(commands, fatal=True):
    """Run commands"""

    for cmd in commands:
        LOG.info('Running command: "%s"', '" "'.join(cmd))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        output, error = process.communicate()
        if process.returncode != 0:
            LOG.error("Command: %s failed!.\nSTDOUT: %s\nSTDERR: %s",
                      " ".join(cmd), output, error)
            if fatal:
                raise exception.Error("Command: %s failed", " ".join(cmd))
        LOG.debug('STDOUT: %s\nSTDERR: %s', output, error)


def get_scsi_id(device, fatal=True):
    """Returns the SCSI ID of a device by executing SCSI_ID_COMMAND as defined
    in the configuration.
    """
    cmd = [x.format(device=device) for x in SCSI_ID_COMMAND]
    try:
        scsi_id = subprocess.check_output(cmd)
        LOG.debug("SCSI ID for %s: %s" % (device, scsi_id))
    except subprocess.CalledProcessError as e:
        if fatal:
            raise e
        else:
            LOG.error("Unable to retrieve SCSI ID for device %s" % device)
            return None
    return scsi_id


def get_dev_cleanup_cmd(**kwargs):
    """Returns the command that should run on each node to cleanup the devices
    """
    return [x.format(**kwargs) for x in DEVICE_CLEANUP_COMMAND]

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
