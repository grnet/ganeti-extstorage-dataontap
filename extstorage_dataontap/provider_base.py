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
import string
import glob
import sys
import subprocess
import time

from extstorage_dataontap import configuration
from extstorage_dataontap import exception

LOG = logging.getLogger(__name__)

# Time to wait before retrying in seconds
WAIT = 1
# Maximum number of retries
MAX_RETRIES = 5


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
        self._client = None
        self.pool_name = configuration.POOL
        self.ostype = configuration.LUN_OSTYPE
        self.space_reserved = \
            str(configuration.LUN_SPACE_RESERVATION).lower()
        self.pool_regexp = \
            re.compile(configuration.POOL_NAME_SEARCH_PATTERN)
        self.igroup = configuration.IGROUP

    @property
    def client(self):
        if not self._client:
            self._client = self._client_setup()
        return self._client

    def _client_setup(self):
        """Setup the Data ONTAP client"""
        raise NotImplementedError()

    def _create_lun_meta(self, lun):
        """Creates LUN metadata dictionary"""
        raise NotImplementedError()

    def _get_lun_by_name(self, name):
        """Fetch a lun by name"""

        lun_list = self.client.get_lun_by_args(path='/vol/*/%s' % name)

        assert len(lun_list) < 2, "Multiple LUNs found with name: `%s'" % name

        if len(lun_list) == 0:
            return None

        return NetAppLun(name,
                         int(lun_list[0].get_child_content('size')),
                         self._create_lun_meta(lun_list[0]))

    def _clone_lun(self, lun, new_name):
        """Clone an existing Lun"""
        raise NotImplementedError()

    def _run_cmds(self, commands, fatal=True):
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

    def _get_lun_device(self, name):
        """Returns the LUN's block device if mapped on the host"""
        f = string.Formatter()
        fields = [i[1] for i in f.parse(configuration.LUN_DEVICE_PATH_FORMAT)]

        LOG.info("Running device mapping commands")
        self._run_cmds(configuration.LUN_ATTACH_COMMANDS)

        # We use globbing to search for files. Replace all fields of the
        # LUN_DEVICE_PATH_FORMAT but the name with '*'
        d = dict.fromkeys(fields, '*')
        d["name"] = name
        pattern = configuration.LUN_DEVICE_PATH_FORMAT.format(**d)

        LOG.info("Scanning file system for %s", pattern)
        # If the file we are searching for is created by a udev rule triggered
        # by one of the mapping commands, then a race condition may occur. We
        # could use "udevadm settle" which watches the udev event queue, and
        # exits if all current events are handled to overcome this, but I've
        # seen this command block without respecting the timeout. It's better
        # if we don't use it here. The user should put it in the list of attach
        # commands if needed. Just to be on the safe side, better wait for a
        # while and retry the search if the file is not found.
        for i in xrange(MAX_RETRIES):
            files = glob.glob(pattern)
            LOG.debug("Device files found for LUN %s: %s", name,
                      ", ".join(files))
            if len(files) > 2:
                raise exception.Error("Multiple devices found with name %s",
                                      name)
            elif len(files) == 1:
                return files[0]

            if i < MAX_RETRIES - 1:
                LOG.warning("Device for LUN %s not found. Retrying after "
                            "sleeping for %d seconds", name, WAIT)
                time.sleep(WAIT)

        LOG.warning("Device for LUN %s not found after scanning", name)
        return None

    def create(self):
        """Driver's entry point for the create script"""
        lun_name = os.getenv('VOL_NAME')
        size = os.getenv('VOL_SIZE')

        assert lun_name is not None, "missing VOL_NAME parameter"
        assert size is not None, "missing VOL_SIZE parameter"
        assert self.igroup is not None, "igroup is not set"

        LOG.info("Creating volume %s with size %s mebibytes", lun_name, size)

        exists = self._get_lun_by_name(lun_name)
        if exists is not None:
            raise exception.VolumeExists(name=exists.name,
                                         pool=exists.metadata['Volume'])

        size = int(size) * (1024 ** 2)  # Size was in mebibytes

        metadata = {
            'OsType': self.ostype,
            'SpaceReserved': self.space_reserved,
            'Path': '/vol/%s/%s' % (self.pool_name, lun_name)}

        self.client.create_lun(self.pool_name, lun_name, size, metadata, None)

        LOG.info("create: Mapping volume %s to igroup %s",
                 lun_name, self.igroup)
        self.client.map_lun(metadata['Path'], self.igroup)

        return 0

    def attach(self):
        """Driver's entry point for the attach script"""
        lun_name = os.getenv('VOL_NAME')

        assert lun_name is not None, "missing VOL_NAME parameter"

        LOG.info("Attaching volume %s", lun_name)

        device = self._get_lun_device(lun_name)

        if device:
            LOG.debug("Outputing: %s", device)
            sys.stdout.write(device)
        else:
            LOG.error("Could not attach device for LUN %s", lun_name)
            return 1

        return 0

    def detach(self):
        """Driver's entry point for the detach script"""
        lun_name = os.getenv('VOL_NAME')

        assert lun_name is not None, "missing VOL_NAME parameter"

        LOG.info("Detaching volume %s", lun_name)

        self._run_cmds(configuration.LUN_DETACH_COMMANDS)

        return 0

    def remove(self):
        """Driver's entry point for the remove script"""
        lun_name = os.getenv('VOL_NAME')

        assert lun_name is not None, "missing VOL_NAME parameter"

        LOG.info("Removing volume %s", lun_name)

        lun = self._get_lun_by_name(lun_name)
        if lun is None:
            raise exception.VolumeNotFound(volume_id=lun_name)

        self.client.destroy_lun(lun.metadata['Path'])
        return 0

    def grow(self):
        """Driver's entry point for the grow script"""
        lun_name = os.getenv('VOL_NAME')
        size = os.getenv('VOL_NEW_SIZE')

        assert lun_name is not None, "missing VOL_NAME parameter"
        assert size is not None, "missing VOL_NEW_SIZE parameter"

        LOG.info("Growing volume %s to %s mebibytes", lun_name, size)

        size = int(size) * (1024 ** 2)  # Size was in mebibytes

        lun = self._get_lun_by_name(lun_name)
        if lun is None:
            raise exception.VolumeNotFound(volume_id=lun_name)

        self.client.do_direct_resize(lun.metadata['Path'], size)
        return 0

    def setinfo(self):
        """Driver's entry point for the setinfo script"""
        lun_name = os.getenv("VOL_NAME")
        metadata = os.getenv("VOL_METADATA")

        assert lun_name is not None, "missing VOL_NAME parameter"
        assert metadata is not None, "missing VOL_METADATA parameter"

        LOG.info("Setting metadata for volume %s: %s", lun_name,
                 metadata)
        LOG.warning("Metadata setting mechanism is not implemented")

        return 0

    def verify(self):
        """Driver's entry point for the verify script"""
        LOG.info("Verify script called")

        return 0

    def snapshot(self):
        """Driver's entry point for the grow script"""
        lun_name = os.getenv('VOL_NAME')
        new_name = os.getenv('VOL_SNAPSHOT_NAME')

        # The snapshot size is ignored by the driver
        # size = os.getenv('VOL_SNAPSHOT_SIZE')

        assert lun_name is not None, "missing VOL_NAME parameter"
        assert new_name is not None, "missing VOL_SNAPSHOT_NAME parameter"
        # assert size is not None, "missing VOL_SNAPSHOT_SIZE parameter"

        LOG.info("Snapshoting %s to %s", lun_name, new_name)

        # size = int(size) * (1024 ** 2)  # Size was in mebibytes

        lun = self._get_lun_by_name(lun_name)
        if lun is None:
            raise exception.VolumeNotFound(volume_id=lun_name)

        self._clone_lun(lun, new_name)
        return 0

    def open(self):
        """Driver's entry point for the open script"""
        lun_name = os.getenv('VOL_NAME')

        assert lun_name is not None, "missing VOL_NAME parameter"

        LOG.info("Opening volume %s", lun_name)

        return 0

    def close(self):
        """Driver's entry point for the close script"""
        lun_name = os.getenv('VOL_NAME')

        assert lun_name is not None, "missing VOL_NAME parameter"

        LOG.info("Closing volume %s", lun_name)

        return 0

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
