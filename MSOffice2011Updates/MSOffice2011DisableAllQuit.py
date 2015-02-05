#!/usr/bin/python
#
# Copyright 2015 Shea G. Craig
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""See docstring for MSOffice2011DisableAllQuit class"""

import os

from autopkglib import Processor, ProcessorError


__all__ = ["MSOffice2011DisableAllQuit"]

# Based off the excellent work of Rich Trouton:
# https://derflounder.wordpress.com/2012/09/26/removing-the-office-2011-installers-application-quit-function/


class MSOffice2011DisableAllQuit(Processor):
    """Overwrites the Office2011_all_quit_14.x.x.combo.pkg/Scripts/preinstall
    script with one that doesn't kill all of your browsers.

    """
    description = __doc__

    input_variables = {
        "unpacked_pkg_path": {
            "required": True,
            "description": ("Path to an unpacked Office update package."),
        },
    }
    output_variables = {
    }

    def main(self):
        """Write a blank shell script over the Office all_quit
        preinstall.

        """
        installs_array = self.env['additional_pkginfo']['installs']
        version = installs_array[0]['CFBundleVersion']
        path = os.path.join(self.env['unpacked_pkg_path'],
                            'Office2011_all_quit_%s.combo.pkg' % version,
                            'Scripts/preinstall')
        with open(path, 'w+') as preinstall:
            preinstall.write('#!/bin/bash\n\nexit 0')


if __name__ == "__main__":
    PROCESSOR = MSOffice2011DisableAllQuit()
    PROCESSOR.execute_shell()
