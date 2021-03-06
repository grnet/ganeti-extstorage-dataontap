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

import logging

from extstorage_dataontap import configuration
from extstorage_dataontap.provider_base import DataOnTapProviderBase
from extstorage_dataontap.client.client_7mode import Client

LOG = logging.getLogger(__name__)


class DataOnTapProvider(DataOnTapProviderBase):
    """ExtStorage provider class for NetApp's Data ONTAP working in 7-mode"""

    def _client_setup(self):
        """Setup the Data ONTAP client"""
        return Client(hostname=configuration.HOSTNAME,
                      transport_type=configuration.TRANSPORT_TYPE,
                      port=configuration.PORT,
                      username=configuration.LOGIN,
                      password=configuration.PASSWORD,
                      vfiler=configuration.SEVEN_MODE_VFILER,
                      verify_cert=configuration.VERIFY_CERT)

    def _create_lun_meta(self, lun):
        """Creates LUN metadata dictionary."""
        LOG.debug("Calling check_is_naelement(%s)", lun)
        self.client.check_is_naelement(lun)
        meta_dict = {}
        meta_dict['Path'] = lun.get_child_content('path')
        meta_dict['Volume'] = lun.get_child_content('path').split('/')[2]
        meta_dict['OsType'] = lun.get_child_content('multiprotocol-type')
        meta_dict['SpaceReserved'] = lun.get_child_content(
            'is-space-reservation-enabled')
        meta_dict['UUID'] = lun.get_child_content('uuid')
        return meta_dict

    def _clone_lun(self, lun, new_name):
        """Clone an existing Lun"""

        path = lun.metadata['Path']
        clone_path = "%s/%s" % (path.rpartition('/')[0], new_name)

        LOG.debug("Calling clone_lun(%s, %s, %s, %s, %s)", path, clone_path,
                  lun.name, new_name, self.space_reserved)
        self.client.clone_lun(path, clone_path, lun.name, new_name,
                              self.space_reserved)

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
