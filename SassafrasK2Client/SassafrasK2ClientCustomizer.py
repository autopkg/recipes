#!/usr/bin/python
#
# Copyright 2013 Tim Sutton
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
"""See docstring for SassafrasK2ClientCustomizer class"""


import os
import subprocess

from autopkglib import Processor, ProcessorError


__all__ = ["SassafrasK2ClientCustomizer"]


CONFIG_SCRIPT_PATH = 'Contents/Resources/k2clientconfig'

class SassafrasK2ClientCustomizer(Processor):
    """Given a flat pkg K2Client installer and the k2clientconfig
    script, run the k2clientconfig script with customizable options."""
    description = __doc__
    input_variables = {
        "base_pkg_path": {
            "required": True,
            "description":
                "Path to a K2Client.pkg installer to be modified."
        },
        "k2clientconfig_options": {
            "required": True,
            "description":
                "String of command arguments to be passed to k2clientconfig."
        },
        "k2clientconfig_path": {
            "required": True,
            "description":
                ("Full path to a k2clientconfig that's written for modifying "
                 "flat packages.")
        }
    }
    output_variables = {
    }

    def main(self):
        script = self.env["k2clientconfig_path"]
        pkg = self.env["base_pkg_path"]
        if not os.path.exists(script):
            raise ProcessorError("No file exists at k2clientconfig_path: "
                                 "%s" % script)
        if not os.access(script, os.X_OK):
            os.chmod(script, 0755)
        if not os.path.exists(pkg):
            raise ProcessorError("No K2Client pkg exists at "
                                 "base_pkg_path: %s" % pkg)

        cmd = [script] + [n for n in self.env["k2clientconfig_options"].split()]
        cmd.append(pkg)
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        _, err = proc.communicate()
        if err:
            raise ProcessorError("k2clientconfig returned errors:\n%s" % err)


if __name__ == "__main__":
    PROCESSOR = SassafrasK2ClientCustomizer()
    PROCESSOR.execute_shell()
