#!/usr/bin/python
#
# Copyright 2015 Tim Sutton
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
"""See docstring for AdobeFlashDownloadDecoder class"""

import os
import subprocess

from autopkglib import Processor, ProcessorError


__all__ = ["AdobeFlashDownloadDecoder"]

#pylint: disable=missing-docstring
#pylint: disable=e1101

class AdobeFlashDownloadDecoder(Processor):
    '''Decodes an Adobe Flash Download using `security cms`. Thanks to Per
    Olofsson for documenting the use of the `security` command to decode the
    ASN-1 data from Adobe's Flash Player download.'''
    description = __doc__
    input_variables = {
        "encoded_path": {
            "required": True,
            "description": ("Path to a downloaded, encoded DMG from Adobe's "
                            "auto-update url."),
        },
    }
    output_variables = {
        "pathname": {
            "description": ("Path to the decoded DMG file. Note that this is "
                            "the same variable name as output by "
                            "URLDownloader, since we have ."),
        },
    }

    def main(self):
        '''Decode the file specified at encoded_path to a new file stored
        in the pathname variable.'''
        inpath = self.env["encoded_path"]
        outname = self.env.get("NAME", "AdobeFlashPlayer") + ".dmg"
        outpath = os.path.join(self.env["RECIPE_CACHE_DIR"], outname)

        sec_cmd = ["/usr/bin/security", "cms", "-D",
                   "-i", inpath,
                   "-o", outpath]
        # wrap our call around a general exception in case of unexpected
        # issues calling `security`
        try:
            proc = subprocess.Popen(sec_cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            _, err = proc.communicate()
            # we expect no output on success, so raise an error in case
            # of any non-zero return code or stderr output
            if proc.returncode or err:
                raise ProcessorError("`security` error: %s, return code: %s"
                                     % (err, proc.returncode))
        except Exception as exp:
            raise ProcessorError("Unexpected exception in running `security` "
                                 "command: %s" % exp)
        self.env["pathname"] = outpath


if __name__ == '__main__':
    PROCESSOR = AdobeFlashDownloadDecoder()
    PROCESSOR.execute_shell()
