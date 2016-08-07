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
import time
import socket
import functools
import subprocess

from extstorage_dataontap import configuration
from extstorage_dataontap import exception

LOG = logging.getLogger(__name__)

# Time to wait before retrying in seconds
WAIT = 1
# Maximum number of retries
MAX_RETRIES = 5
# Cleanup files directory
DEVICE_CLEANUP_DIR = '/var/lib/extstorage-dataontap/device-cleanup'


def getenv(name):
    """Get environment variable value or raise error"""
    value = os.getenv(name)
    if value is None:
        raise exception.ExtStorageException(
            "Missing environment variable %s" % name)
    return value


def map_environ(**kwargs):
    """Map environment variables to method arguments"""
    def wrapper(m):
        @functools.wraps(m)
        def wrapped(self):
            args = {"self": self}
            for name, env in kwargs.items():
                env = env.split(":")
                assert len(env) == 1 or (len(env) == 2 and env[0] == "list"), \
                    "Invalid type of environment variable: %s" % ":".join(env)
                if len(env) == 1:
                    value = getenv(env[0])
                else:
                    # If list:VAR is defined we expect to have environment
                    # variables of this form present:
                    # DISK_COUNT = <int> and DISK%d_<value> = ....
                    # where %d = range(DISK_COUNT)
                    count = int(getenv("%s_COUNT" % env[1]))
                    value = []
                    for i in xrange(count):
                        value.append({})
                        prefix = "%s%d_" % (env[1], i)
                        for j in [x for x in os.environ.keys()
                                  if x.startswith(prefix)]:
                            key = j[len(prefix):].lower()
                            value[i][key] = getenv(j)
                args[name] = value
            return m(**args)
        return wrapped
    return wrapper


def run_hook_on_node(name, descr):
    """Run the decorated function only if this is a specific node"""
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            current = socket.getfqdn()
            LOG.debug("Current node: %s", current)
            target = getenv(name)
            LOG.debug("%s node: %s", descr.capitalize(), target)

            if current == target:
                return func(*args, **kwargs)
            else:
                LOG.warn("Not running this hook here because this is not the "
                         "%s node: %s", descr, target)
                return 0
        return wrapped
    return wrapper


class NetAppLun(object):
    """Represents a LUN on NetApp storage."""

    def __init__(self, name, size, metadata):
        self.name = name
        self.size = size
        self.metadata = metadata or {}
        LOG.debug(str(self))

    def get_metadata_property(self, prop):
        """Get the metadata property of a LUN."""
        if prop in self.metadata:
            return self.metadata[prop]
        name = self.name
        LOG.debug("No metadata property %(prop)s defined for the LUN %(name)s",
                  {'prop': prop, 'name': name})

    def __str__(self, *args, **kwargs):
        return 'NetApp LUN [name:%s, size:%s, metadata:%s]' % (
            self.name, self.size, self.metadata)


class DataOnTapProviderBase(object):
    """ExtStorage provider class for NetApp's Data ONTAP"""

    def __init__(self):
        """Initializes the provider"""
        self._client = None
        self.pool_name = configuration.POOL
        self.ostype = configuration.LUN_OSTYPE
        self.space_reserved = str(configuration.LUN_SPACE_RESERVATION).lower()
        self.pool_regexp = re.compile(configuration.POOL_NAME_SEARCH_PATTERN)
        self.igroup = configuration.IGROUP

    @property
    def client(self):
        """Initializes the NetApp client"""
        if not self._client:
            LOG.info("Initializing NetApp client")
            self._client = self._client_setup()
            LOG.info("NetApp initialization finished")
        return self._client

    def _client_setup(self):
        """Setup the Data ONTAP client"""
        raise NotImplementedError()

    def _create_lun_meta(self, lun):
        """Creates LUN metadata dictionary"""
        raise NotImplementedError()

    def _get_lun_by_name(self, name):
        """Fetch a lun by name"""

        LOG.debug("Calling get_lun_by_args(path='/vol/*/%s')", name)
        lun_list = self.client.get_lun_by_args(path='/vol/*/%s' % name)
        LOG.debug("LUNs returned: %r", lun_list)

        assert len(lun_list) < 2, "Multiple LUNs found with name: `%s'" % name

        if len(lun_list) == 0:
            return None

        return NetAppLun(name,
                         int(lun_list[0].get_child_content('size')),
                         self._create_lun_meta(lun_list[0]))

    def _clone_lun(self, lun, new_name):
        """Clone an existing Lun"""
        raise NotImplementedError()

    def _search_lun_device(self, name):
        """Find device path of a LUN if mapped on the host"""
        f = string.Formatter()
        fields = [i[1] for i in f.parse(configuration.LUN_DEVICE_PATH_FORMAT)]

        # We use globing to search for files. Replace all fields of the
        # LUN_DEVICE_PATH_FORMAT but the name with '*'
        d = dict.fromkeys(fields, '*')
        d["name"] = name
        pattern = configuration.LUN_DEVICE_PATH_FORMAT.format(**d)

        LOG.debug("Scanning file system for %s", pattern)
        files = glob.glob(pattern)
        LOG.debug("Device files found for LUN %s: %s", name, ", ".join(files))
        if len(files) > 2:
            raise exception.Error("Multiple devices found with name %s", name)
        elif len(files) == 1:
            return files[0]

        # Not found
        return None

    def _get_lun_device(self, name):
        """Returns the LUN's block device if mapped on the host. Run the attach
        commands if the device is not present."""
        device = self._search_lun_device(name)
        if device:
            # If the device is present, there is no need to run the attach
            # commands
            return device
        else:
            LOG.info("Device not found. Running device mapping commands")
            configuration.run_cmds(configuration.LUN_ATTACH_COMMANDS)

        # If the file we are searching for is created by a udev rule triggered
        # by one of the mapping commands, then a race condition may occur. We
        # could use "udevadm settle" which watches the udev event queue, and
        # exits if all current events are handled to overcome this, but I've
        # seen this command block without respecting the timeout. It's better
        # if we don't use it here. The user should put it in the list of attach
        # commands if needed. Just to be on the safe side, better wait for a
        # while and retry the search if the file is not found.
        for i in xrange(MAX_RETRIES):
            device = self._search_lun_device(name)
            if device:
                return device

            if i < MAX_RETRIES - 1:
                LOG.warning("Device for LUN %s not found. Retrying after "
                            "sleeping for %d seconds", name, WAIT)
                time.sleep(WAIT)

        LOG.warning("Device for LUN %s not found after scanning", name)
        return None

    @map_environ(lun_name="VOL_NAME", size="VOL_SIZE")
    def create(self, lun_name, size):
        """Driver's entry point for the create script"""
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

        LOG.debug("Calling create_lun(%s, %s, %d, %r, None)",
                  self.pool_name, lun_name, size, metadata)
        self.client.create_lun(self.pool_name, lun_name, size, metadata, None)

        LOG.info("Mapping volume %s to igroup %s", lun_name, self.igroup)
        LOG.debug("Calling map_lun(%s, %s)", metadata['Path'], self.igroup)
        self.client.map_lun(metadata['Path'], self.igroup)

        return 0

    @map_environ(lun_name="VOL_NAME")
    def attach(self, lun_name):
        """Driver's entry point for the attach script"""
        LOG.info("Attaching volume %s", lun_name)

        device = self._get_lun_device(lun_name)
        if device:
            LOG.debug("Outputing: %s", device)
            sys.stdout.write(device)
        else:
            LOG.error("Could not attach device for LUN %s", lun_name)
            return 1

        return 0

    @map_environ(lun_name="VOL_NAME")
    def detach(self, lun_name):
        """Driver's entry point for the detach script"""
        LOG.info("Detaching volume %s", lun_name)

        configuration.run_cmds(configuration.LUN_DETACH_COMMANDS)

        return 0

    @map_environ(lun_name="VOL_NAME", uuid="VOL_UUID")
    def remove(self, lun_name, uuid):
        """Driver's entry point for the remove script"""
        LOG.info("Removing volume %s", lun_name)

        # Well, this is a hack but we need to do it. Before removing the LUN,
        # we need to save the SCSI ID of the device in a file, so the ganeti
        # cluster node can fetch it to perform a global cluster cleanup.
        # Theoretically, the node has already removed the device during
        # detach, but in our case the detach is a NOOP. Since the node has
        # definitely performed attach in the past before remove, the device
        # should be there.
        device = self._search_lun_device(lun_name)
        if device:
            scsi = configuration.get_scsi_id(device)
            with open('%s/%s' % (DEVICE_CLEANUP_DIR, uuid), "w") as f:
                f.write(scsi)
        else:
            LOG.warn("Device for LUN: %s not found on the node!")

        lun = self._get_lun_by_name(lun_name)
        if lun is None:
            raise exception.VolumeNotFound(volume_id=lun_name)

        LOG.debug("Calling destroy_lun(%s)", lun.metadata['Path'])
        self.client.destroy_lun(lun.metadata['Path'])
        return 0

    @map_environ(lun_name="VOL_NAME", size="VOL_NEW_SIZE")
    def grow(self, lun_name, size):
        """Driver's entry point for the grow script"""
        LOG.info("Growing volume %s to %s mebibytes", lun_name, size)

        size = int(size) * (1024 ** 2)  # Size was in mebibytes

        lun = self._get_lun_by_name(lun_name)
        if lun is None:
            raise exception.VolumeNotFound(volume_id=lun_name)

        LOG.debug("Calling do_direct_resize(%s, %d)",
                  lun.metadata['Path'], size)
        self.client.do_direct_resize(lun.metadata['Path'], size)

        # Rerun the attach commands. This is needed because attach will run the
        # commands only if the device is not present. After growing, the device
        # may be present and have wrong size.
        configuration.run_cmds(configuration.LUN_ATTACH_COMMANDS)
        return 0

    @map_environ(lun_name="VOL_NAME", metadata="VOL_METADATA")
    def setinfo(self, lun_name, metadata):
        """Driver's entry point for the setinfo script"""
        LOG.info("Setting metadata for volume %s: %s", lun_name,
                 metadata)
        LOG.warning("Metadata setting mechanism is not implemented")

        return 0

    def verify(self):
        """Driver's entry point for the verify script"""
        LOG.info("Verify script called")

        return 0

    @map_environ(lun_name="VOL_NAME", new_name="VOL_SNAPSHOT_NAME",
                 size="VOL_SNAPSHOT_SIZE")
    def snapshot(self, lun_name, new_name, size):
        """Driver's entry point for the grow script"""
        LOG.info("Snapshoting %s to %s", lun_name, new_name)

        # The snapshot size is ignored by the driver
        # size = int(size) * (1024 ** 2)  # Size was in mebibytes

        lun = self._get_lun_by_name(lun_name)
        if lun is None:
            raise exception.VolumeNotFound(volume_id=lun_name)

        self._clone_lun(lun, new_name)
        return 0

    @map_environ(lun_name="VOL_NAME")
    def open(self, lun_name):
        """Driver's entry point for the open script"""
        LOG.info("Opening volume %s", lun_name)

        return 0

    @map_environ(lun_name="VOL_NAME")
    def close(self, lun_name):
        """Driver's entry point for the close script"""
        LOG.info("Closing volume %s", lun_name)

        return 0

    @run_hook_on_node(name="GANETI_NEW_PRIMARY", descr="migration target")
    @map_environ(instance="GANETI_INSTANCE_NAME",
                 disk_template="GANETI_INSTANCE_DISK_TEMPLATE")
    def pre_migrate(self, instance, disk_template):
        """Driver's entry point for the pre migration hook"""
        LOG.debug("Storage type for instance %s: %s", instance, disk_template)

        # Run the hook only if the disk template of the instance is ext.
        if disk_template != 'ext':
            LOG.warn("Not running this hook for instance %s. Not using an ext"
                     "(%s) storage type", instance, disk_template)
            return 0

        configuration.run_cmds(configuration.LUN_ATTACH_COMMANDS)
        return 0

    @run_hook_on_node(name="GANETI_MASTER", descr="Ganeti master")
    @map_environ(node="GANETI_INSTANCE_PRIMARY",
                 disk_template="GANETI_INSTANCE_DISK_TEMPLATE",
                 disks="list:GANETI_INSTANCE_DISK")
    def post_remove(self, node, disk_template, disks):
        """Driver's entry point for the post remove hook"""

        if disk_template != 'ext':
            return 0

        def run(*args):
            """wrapper function for subprocess.check_output()"""
            LOG.debug("Executing: %s", args)
            out = subprocess.check_output(args)
            LOG.debug("Output: %s", out)
            return out

        for i in range(len(disks)):
            assert 'uuid' in disks[i]
            scsi_id_file = "%s/%s" % (DEVICE_CLEANUP_DIR, disks[i]['uuid'])
            # Get the file hosting the SCSI ID of the device that has been
            # removed. This file should have been created by the destroy
            # command
            out = run('gnt-cluster', 'command', '-M', '--node', node, 'cat',
                      scsi_id_file)
            try:
                rc = int(re.search(r'return code = (\d+)', out).group(1))
            except AttributeError:
                LOG.error("Can't find the return code in output: %s", out)
                return 1

            if rc != 0:
                LOG.error("Command failed with rc=%d", rc)
                return 2

            try:
                scsi_id = re.search(r'%s: (\w+)' % node, out).group(1)
            except AttributeError:
                LOG.error("Can't find SCSI ID in output: %s", out)
                return 3

            # Remove the file after processing
            run('gnt-cluster', 'command', '-M', '--node', node, 'rm', '-f',
                scsi_id_file)

            dev_cleanup = configuration.get_dev_cleanup_cmd(scsi_id=scsi_id)
            if len(dev_cleanup) == 0:
                continue

            run('gnt-cluster', 'command', " ".join(dev_cleanup))

        return 0


# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
