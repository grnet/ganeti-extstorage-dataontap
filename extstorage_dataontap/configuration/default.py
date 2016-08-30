# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 GRNET S.A.
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


# If set, debug info will be printed
DEBUG = False

# Log on this file. Ganeti will log everything that is printed to stderr for
# most of the commands, but not attach. This file will have a complete log of
# the provider. If you don't need this, then set it to None
LOGFILE = '/var/log/ganeti-extstorage-dataontap.log'

# The storage family type used on the storage system;
# valid values are ontap_7mode for using Data ONTAP operating in 7-Mode and
# ontap_cluster for using clustered Data ONTAP
STORAGE_FAMILY = "ontap_cluster"

# The storage protocol (iscsi or fc) to be used on the data path with the
# storage system.
STORAGE_PROTOCOL = 'iscsi'

# The hostname (or IP address) for the storage system or proxy server.
HOSTNAME = 'example.org'

# The TCP port to use for communication with the storage system or proxy
# server. If not specified, Data ONTAP drivers will use 80 for HTTP and 443 for
# HTTPS
PORT = None

# The transport protocol used when communicating with the storage system or
# proxy server.
TRANSPORT_TYPE = "https"

# Verify the SSL Certificate when TRANSPORT_TYPE is "https".
# WARNING: Turning this to False has security implications!
VERIFY_CERT = True

# Administrative user account name used to access the storage system or proxy
# server.
LOGIN = None

# Password for the administrative user account specified in the netapp_login
# option.
PASSWORD = None

# This option determines if storage space is reserved for LUN allocation. If
# enabled, LUNs are thick provisioned. If space reservation is disabled,
# storage space is allocated on demand.
LUN_SPACE_RESERVATION = True

# This option specifies the virtual storage server (Vserver) name on the
# storage cluster on which provisioning of block storage volumes should occur.
CLUSTER_MODE_VSERVER = None

# The vFiler unit on which provisioning of block storage volumes will be done.
# This option is only used by the driver when connecting to an instance with a
# storage family of Data ONTAP operating in 7-Mode. Only use this option when
# utilizing the MultiStore feature on the NetApp storage system.
SEVEN_MODE_VFILER = None

# The name of the config.conf stanza for a Data ONTAP (7-mode) HA partner.
# This option is only used by the driver when connecting to an instance with a
# storage family of Data ONTAP operating in 7-Mode, and it is required if the
# storage protocol selected is FC.
SEVEN_MODE_PARTNER_BACKEND_NAME = None

# This option defines the type of operating system that will access a LUN
# exported from Data ONTAP; it is assigned to the LUN at the time it is
# created. Valid values for this field are: 'solaris', 'windows', 'hpux',
# 'aix', 'linux', 'netware', 'vmware', 'windows_gpt', 'windows_2008', 'xen',
# 'hyper_v', 'solaris_efi', 'openvms'
LUN_OSTYPE = 'linux'

# This option is used to restrict provisioning to the specified pools. Specify
# the value of this option to be a regular expression which will be applied to
# the names of objects from the storage backend which represent pools in
# Cinder. This option is only utilized when the storage protocol is configured
# to use iSCSI or FC.
POOL_NAME_SEARCH_PATTERN = "(.+)"

# This options specifies the pool (volume in the Data ONTAP context) to create
# the LUNs on.
POOL = "vol0"

# Map the LUN to the specified initiator group upon creation.
IGROUP = None

# This pattern defines the path we expect a LUN to find under
LUN_DEVICE_PATH_FORMAT = "/dev/disk/{hostname}/{pool}/{name}"

# Commands to run to attach the LUN to a host when iSCSI protocol is used.
# Warning: This option is a tuple of tuples (or a list of lists). To create an
# empty tuple use (). To create a list with a single command with no args,
# specify it like this:(("cmd",),)
ISCSI_ATTACH_COMMANDS = (("iscsiadm", "-m", "node", "-R"), ("multipath", "-r"),
                         ("udevadm", 'settle'))

# Commands to run to detaching the LUN from a host when iSCSI protocol is used.
# Warning: This option is a tuple of tuples (or a list of lists). To create an
# empty tuple use (). To create a tuple with a single command with no args,
# specify it like this:(("cmd",),)
ISCSI_DETACH_COMMANDS = ()

# Commands to run to attach the LUN to a host when FC protocol is used.
# Warning: This option is a tuple of tuples (or a list of lists). To create an
# empty tuple use (). To create a list with a single command with no args,
# specify it like this:(("cmd",),)
FC_ATTACH_COMMANDS = (("rescan-scsi-bus.sh",), ("multipath", "-r"),
                      ("udevadm", 'settle'))

# Commands to run to detaching the LUN from a host when FC protocol is used.
# Warning: This option is a tuple of tuples (or a list of lists). To create an
# empty tuple use (). To create a tuple with a single command with no args,
# specify it like this:(("cmd",),)
FC_DETACH_COMMANDS = ()

# Command in the form of a tuple that returns the SCSI ID of a device. Use
# {device} as a placeholder for the actual device path
SCSI_ID_COMMAND = "/lib/udev/scsi_id", "-g", "-d", "{device}"

# Command in the form of a tuple that should be executed on each node after a
# LUN has been destroyed. Use {scsi_id} as a placeholder for the actual SCSI ID
# of the device of the LUN
DEVICE_CLEANUP_COMMAND = ()

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
