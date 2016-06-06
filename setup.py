#!/usr/bin/env python
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

from setuptools import setup, find_packages
from setuptools.command.install import install as _install
from setuptools.command.easy_install import log
import sys
import os

from extstorage_dataontap import version

# Overload the install command to copy the parameters.list in the installation
# directory. We use this instead of adding scripts=['parameter.list'] in the
# setup to copy the file because this will not set the execution bit to the
# target file
class install(_install):
    def run(self):
        _install.run(self)

        src = os.path.join(os.path.dirname(sys.modules[__name__].__file__),
                           'parameters.list')
        target = os.path.join(self.install_scripts, 'parameters.list')
        log.info("Installing %s to %s" % (src, self.install_scripts))

        with open(src, 'r') as f:
            contents = f.read()

        with open(target, 'w') as f:
            f.write(contents)
            f.close()


setup(
    name='extstorage_dataontap',
    version=version,
    description="Ganeti ExtStorage Provider for NetApp's Data ONTAP",
    packages=find_packages(),
    include_package_data=True,
    install_requires=['six', 'iso8601', 'lxml'],
    cmdclass={'install': install},
    entry_points={
        'console_scripts': [
            'create = extstorage_dataontap.common:create',
            'attach = extstorage_dataontap.common:attach',
            'detach = extstorage_dataontap.common:detach',
            'remove = extstorage_dataontap.common:remove',
            'grow = extstorage_dataontap.common:grow',
            'setinfo = extstorage_dataontap.common:setinfo',
            'verify = extstorage_dataontap.common:verify',
            'snapshot = extstorage_dataontap.common:snapshot',
            'open = extstorage_dataontap.common:open',
            'close = extstorage_dataontap.common:close']},
    classifiers=[
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Topic :: System :: Systems Administration'],
    keywords='ganeti extstorage cloud IaaS OS volume'
)

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
