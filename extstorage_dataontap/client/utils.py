# Copyright 2011 OpenStack Foundation.
# Copyright 2012, Red Hat, Inc.
# Copyright (c) 2012 NetApp, Inc.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import logging
import six
import socket
import sys
import traceback
import datetime

import iso8601

from extstorage_dataontap.i18n import _LE

utcnow = datetime.datetime.utcnow


class Features(object):

    def __init__(self):
        self.defined_features = set()

    def add_feature(self, name, supported=True, min_version=None):
        if not isinstance(supported, bool):
            raise TypeError("Feature value must be a bool type.")
        self.defined_features.add(name)
        setattr(self, name, FeatureState(supported, min_version))

    def __getattr__(self, name):
        # NOTE(cknight): Needed to keep pylint happy.
        raise AttributeError


class FeatureState(object):

    def __init__(self, supported=True, minimum_version=None):
        """Represents the current state of enablement for a Feature

        :param supported: True if supported, false otherwise
        :param minimum_version: The minimum version that this feature is
        supported at
        """
        self.supported = supported
        self.minimum_version = minimum_version

    def __nonzero__(self):
        """Allow a FeatureState object to be tested for truth value

        :return True if the feature is supported, otherwise False
        """
        return self.supported


def resolve_hostname(hostname):
    """Resolves host name to IP address."""
    res = socket.getaddrinfo(hostname, None)[0]
    family, socktype, proto, canonname, sockaddr = res
    return sockaddr[0]


def parse_isotime(timestr):
    """Parse time from ISO 8601 format."""
    try:
        return iso8601.parse_date(timestr)
    except iso8601.ParseError as e:
        raise ValueError(six.text_type(e))
    except TypeError as e:
        raise ValueError(six.text_type(e))


def normalize_time(timestamp):
    """Normalize time in arbitrary timezone to UTC naive object."""
    offset = timestamp.utcoffset()
    if offset is None:
        return timestamp
    return timestamp.replace(tzinfo=None) - offset


def is_older_than(before, seconds):
    """Return True if before is older than seconds."""
    if isinstance(before, six.string_types):
        before = parse_isotime(before)

    before = normalize_time(before)

    return utcnow() - before > datetime.timedelta(seconds=seconds)


class save_and_reraise_exception(object):
    """Save current exception, run some code and then re-raise.

    In some cases the exception context can be cleared, resulting in None
    being attempted to be re-raised after an exception handler is run. This
    can happen when eventlet switches greenthreads or when running an
    exception handler, code raises and catches an exception. In both
    cases the exception context will be cleared.

    To work around this, we save the exception state, run handler code, and
    then re-raise the original exception. If another exception occurs, the
    saved exception is logged and the new exception is re-raised.

    In some cases the caller may not want to re-raise the exception, and
    for those circumstances this context provides a reraise flag that
    can be used to suppress the exception.  For example::

      except Exception:
          with save_and_reraise_exception() as ctxt:
              decide_if_need_reraise()
              if not should_be_reraised:
                  ctxt.reraise = False

    If another exception occurs and reraise flag is False,
    the saved exception will not be logged.

    If the caller wants to raise new exception during exception handling
    he/she sets reraise to False initially with an ability to set it back to
    True if needed::

      except Exception:
          with save_and_reraise_exception(reraise=False) as ctxt:
              [if statements to determine whether to raise a new exception]
              # Not raising a new exception, so reraise
              ctxt.reraise = True
    """
    def __init__(self, reraise=True, logger=None):
        self.reraise = reraise
        if logger is None:
            logger = logging.getLogger()
        self.logger = logger

    def __enter__(self):
        self.type_, self.value, self.tb, = sys.exc_info()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.reraise:
                self.logger.error(_LE('Original exception being dropped: %s'),
                                  traceback.format_exception(self.type_,
                                                             self.value,
                                                             self.tb))
            return False
        if self.reraise:
            six.reraise(self.type_, self.value, self.tb)
