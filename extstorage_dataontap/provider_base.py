# -*- coding: utf-8 -*-
#
# Copyright (c) 2014 Clinton Knight. All rights reserved.
# Copyright (c) 2015 Tom Barron.  All rights reserved.
# Copyright (c) 2015 GRNET S.A. All rights reserved.
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

import os
import logging
import re

from extstorage_dataontap import configuration
from extstorage_dataontap import exception

LOG = logging.getLogger(__name__)


class NetAppLun(object):
    """Represents a LUN on NetApp storage."""

    def __init__(self, name, size, metadata):
        self.name = name
        self.size = size
        self.metadata = metadata or {}
        print metadata

    def get_metadata_property(self, prop):
        """Get the metadata property of a LUN."""
        if prop in self.metadata:
            return self.metadata[prop]
        name = self.name
        LOG.debug("No metadata property %(prop)s defined for the LUN %(name)s",
                  {'prop': prop, 'name': name})

    def __str__(self, *args, **kwargs):
        return 'NetApp LUN [handle:%s, name:%s, size:%s, metadata:%s]' % (
               self.handle, self.name, self.size, self.metadata)


class DataOnTapProviderBase(object):
    """ExtStorage provider class for NetApp's Data ONTAP"""
    def __init__(self):
        """Initializes the provider"""
        self.client = self.client_setup()
        self.pool_name = configuration.SAN_POOL_NAME
        self.ostype = configuration.SAN_LUN_OSTYPE
        self.space_reserved = \
            str(configuration.PROVISIONING_LUN_SPACE_RESERVATION).lower()
        self.pool_regexp = \
            re.compile(configuration.SAN_POOL_NAME_SEARCH_PATTERN)

    def client_setup(self):
        """Setup the Data ONTAP client"""
        raise NotImplementedError()

    def _create_lun_meta(self, lun):
        """Creates LUN metadata dictionary"""
        raise NotImplementedError()

    def get_lun_by_name(self, key):
        """Fetch a lun by name"""

        lun_list = self.client.get_lun_list()
        for lun in lun_list:
            (_, _, pool, name) = lun.get_child_content('path').split('/')
            if key == name:
                if not re.match(self.pool_regexp, pool):
                    LOG.warning("Not returning lun %s because pool %s is "
                                "outside the search scope.")
                    continue
                size = int(lun.get_child_content('size'))
                return NetAppLun(name, size, self._create_lun_meta(lun))
        return None

    def create(self):
        """Create a new volume inside the external storage"""
        lun_name = os.getenv('VOL_NAME')
        size = os.getenv('VOL_SIZE')

        assert lun_name is not None, "missing VOL_NAME parameter"
        assert size is not None, "missing VOL_SIZE parameter"

        exists = self.get_lun_by_name(lun_name)
        if exists is not None:
            raise exception.VolumeExists(name=exists.name,
                                         pool=exists.metadata['Volume'])

        size = int(size) * (1024 ** 2)  # Size was in mebibytes

        metadata = {
            'OsType': self.ostype,
            'SpaceReserved': self.space_reserved,
            'Path': '/vol/%s/%s' % (self.pool_name, lun_name)}

        self.client.create_lun(self.pool_name, lun_name, size, metadata, None)
        return 0

    def remove(self):
        """Remove an existing volume from the external storage"""
        lun_name = os.getenv('VOL_NAME')

        assert lun_name is not None, "missing VOL_NAME parameter"

        lun = self.get_lun_by_name(lun_name)
        if lun is None:
            raise exception.VolumeNotFound(volume_id=lun_name)

        self.client.destroy_lun(lun.metadata['Path'])
        return 0

    def grow(self):
        """Grow and existing volume"""
        lun_name = os.getenv('VOL_NAME')
        size = os.getenv('VOL_NEW_SIZE')

        assert lun_name is not None, "missing VOL_NAME parameter"
        assert size is not None, "missing VOL_NEW_SIZE parameter"

        size = int(size) * (1024 ** 2)  # Size was in mebibytes

        lun = self.get_lun_by_name(lun_name)
        if lun is None:
            raise exception.VolumeNotFound(volume_id=lun_name)

        self.client.do_direct_resize(lun.metadata['Path'], size)
        return 0

    def _clone_lun(self, lun, new_name):
        """Clone an existing Lun"""
        raise NotImplementedError()

    def snapshot(self):
        """Take a snapshot of a given volume"""
        lun_name = os.getenv('VOL_NAME')
        new_name = os.getenv('VOL_SNAPSHOT_NAME')

        # The snapshot size is ignored by the driver
        # size = os.getenv('VOL_SNAPSHOT_SIZE')

        assert lun_name is not None, "missing VOL_NAME parameter"
        assert new_name is not None, "missing VOL_SNAPSHOT_NAME parameter"
        # assert size is not None, "missing VOL_SNAPSHOT_SIZE parameter"

        # size = int(size) * (1024 ** 2)  # Size was in mebibytes

        lun = self.get_lun_by_name(lun_name)
        if lun is None:
            raise exception.VolumeNotFound(volume_id=lun_name)

        self._clone_lun(lun, new_name)
        return 0
