#!/usr/bin/python
#
# Copyright 2013 Greg Neagle
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
"""See docstring for AutoPkgSourceFinder class"""

import os
import glob

from autopkglib import Processor, ProcessorError


__all__ = ["AutoPkgSourceFinder"]


class AutoPkgSourceFinder(Processor):
    """Finds the root autopkg-autopkg-foo folder from the expanded autopkg zip
    archive"""
    description = __doc__
    input_variables = {
        "input_path": {
            "required": True,
            "description": "Path the zip archive was expanded to.",
        },
    }
    output_variables = {
        "autopkg_path": {
            "description": "Root path of expanded autopkg archive.",
        },
    }

    def find_match(self, root_dir, match_string):
        """Finds a file or directory using shell globbing"""
        #pylint: disable=no-self-use
        matches = glob.glob(os.path.join(root_dir, match_string))
        if matches:
            return matches[0][len(root_dir) + 1:]
        else:
            return ""

    def main(self):
        # Get root dir
        root_dir = self.env["input_path"]
        try:
            autopkg_dir = self.find_match(root_dir, 'autopkg-autopkg-*')
            self.env["autopkg_path"] = os.path.join(root_dir, autopkg_dir)
            self.output("Found %s" % self.env["autopkg_path"])
        except BaseException as err:
            raise ProcessorError(err)


if __name__ == "__main__":
    PROCESSOR = AutoPkgSourceFinder()
    PROCESSOR.execute_shell()
