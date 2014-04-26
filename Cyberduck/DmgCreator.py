#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
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

# This is a modified DmgCreator just for the Cyberduck.munki recipe
# that will be removed once support for 'dmg_megabytes' is available
# in a released version of AutoPkg.

import os
import subprocess
import shutil
import tempfile

from autopkglib import Processor, ProcessorError


__all__ = ["DmgCreator"]


class DmgCreator(Processor):
    description = "Creates a disk image from a directory."
    input_variables = {
        "dmg_root": {
            "required": True,
            "description": "Directory that will be copied to a disk image.",
        },
        "dmg_path": {
            "required": True,
            "description": "The dmg to be created.",
        },
        "dmg_format": {
            "required": False,
            "description": "The dmg format. Defaults to UDZO.",
        },
        "dmg_compression_level": {
            "required": False,
            "description": ("Compression level between '1' and '9' to use "
                            "when using UDZO. Defaults to '5', a point "
                            "beyond which very little space savings is "
                            "gained.")
        },
        "dmg_megabytes": {
            "required": False,
            "description": ("Value to set for the '-megabytes' option. Defaults to not set and the option isn't used.")
        }
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def main(self):
        # Remove existing dmg if it exists.
        if os.path.exists(self.env['dmg_path']):
            os.unlink(self.env['dmg_path'])

        # Build a command for hdiutil.
        cmd = [
            "/usr/bin/hdiutil",
            "create",
            "-plist",
            "-format",
            "UDZO",
            "-imagekey",
            "zlib-level=5"
            ]
        if self.env.get("dmg_megabytes"):
            cmd.extend(["-megabytes", str(self.env["dmg_megabytes"])])
        cmd.extend([
            "-srcfolder", self.env['dmg_root'],
            self.env['dmg_path']
            ])

        # Call hdiutil.
        try:
            p = subprocess.Popen(cmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("hdiutil execution failed with error code %d: %s" % (
                                  e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("creation of %s failed: %s" % (self.env['dmg_path'], err))
        
        # Read output plist.
        #output = FoundationPlist.readPlistFromString(out)
        self.output("Created dmg from %s at %s" 
            % (self.env['dmg_root'], self.env['dmg_path']))

if __name__ == '__main__':
    processor = DmgCreator()
    processor.execute_shell()
    

