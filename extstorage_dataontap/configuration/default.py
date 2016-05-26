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
# created.
LUN_OSTYPE = None

# This option is used to restrict provisioning to the specified pools. Specify
# the value of this option to be a regular expression which will be applied to
# the names of objects from the storage backend which represent pools in
# Cinder. This option is only utilized when the storage protocol is configured
# to use iSCSI or FC.
POOL_NAME_SEARCH_PATTERN = "(.+)"

# This options specifies the pool (volume in the Data ONTAP context) to create
# the LUNs on.
POOL = "vol0"

# If this option is set, the LUN will be mapped to the specified initiator
# group upon creation.
IGROUP = None
