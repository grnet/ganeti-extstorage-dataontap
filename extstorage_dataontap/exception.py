# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
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

"""Cinder base exception handling.

Includes decorator for re-raising Cinder-type exceptions.

SHOULD include dedicated exception logging.

"""

import logging
import six

from extstorage_dataontap.i18n import _, _LE


LOG = logging.getLogger(__name__)


class Error(Exception):
    pass


class CinderException(Exception):
    """Base Cinder Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")
    code = 500
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs
        self.kwargs['message'] = message

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        for k, v in self.kwargs.items():
            if isinstance(v, Exception):
                self.kwargs[k] = six.text_type(v)

        if self._should_format():
            try:
                message = self.message % kwargs

            except Exception:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_LE('Exception in string format operation'))
                for name, value in kwargs.items():
                    LOG.error(_LE("%(name)s: %(value)s"),
                              {'name': name, 'value': value})
                # at least get the core message out if something happened
                message = self.message
        elif isinstance(message, Exception):
            message = six.text_type(message)

        # NOTE(luisg): We put the actual message in 'msg' so that we can access
        # it, because if we try to access the message via 'message' it will be
        # overshadowed by the class' message attribute
        self.msg = message
        super(CinderException, self).__init__(message)

    def _should_format(self):
        return self.kwargs['message'] is None or '%(message)' in self.message

    def __unicode__(self):
        return six.text_type(self.msg)


class VolumeBackendAPIException(CinderException):
    message = _("Bad or unexpected response from the storage volume "
                "backend API: %(data)s")


class VolumeDriverException(CinderException):
    message = _("Volume driver reported an error: %(message)s")


class NotAuthorized(CinderException):
    message = _("Not authorized.")
    code = 403


class Invalid(CinderException):
    message = _("Unacceptable parameters.")
    code = 400


class InvalidInput(Invalid):
    message = _("Invalid input received: %(reason)s")


class InvalidHost(Invalid):
    message = _("Invalid host: %(reason)s")


class InvalidConfigurationValue(Invalid):
    message = _('Value "%(value)s" is not valid for '
                'configuration option "%(option)s"')


class NotFound(CinderException):
    message = _("Resource could not be found.")
    code = 404
    safe = True


class VolumeNotFound(NotFound):
    message = _("Volume %(volume_id)s could not be found.")


class ManageExistingInvalidReference(CinderException):
    message = _("Manage existing volume failed due to invalid backend "
                "reference %(existing_ref)s: %(reason)s")


class ManageExistingVolumeTypeMismatch(CinderException):
    message = _("Manage existing volume failed due to volume type mismatch: "
                "%(reason)s")


class NetAppDriverException(VolumeDriverException):
    message = _("NetApp Cinder Driver exception.")
