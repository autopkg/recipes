#!/usr/bin/python
#
# Copyright 2013 Timothy Sutton
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
"""See docstring for TextMateURLProvider processor"""

from __future__ import absolute_import, print_function

from subprocess import PIPE, Popen

from autopkglib import Processor, ProcessorError

DEFAULT_BRANCH = "release"
DEFAULT_OS = "10.14"
BASE_URL = "https://api.textmate.org/downloads/"

# Another interesting URL that returns an ASCII-style plist used by
# the app's own SU mechanism, but the download URL it returns is an
# https URL that urllib/2 cannot handshake with:
# http://api.textmate.org/releases/

__all__ = ["TextMateURLProvider"]


class TextMateURLProvider(Processor):
    """Provides a download URL for a TextMate 2 update.
    TextMate 1 is not supported."""

    description = __doc__
    input_variables = {
        "branch": {
            "required": False,
            "description": (
                "The update branch. One of 'release', 'beta', or 'nightly'. "
                "In the TM GUI, 'Normal' corresponds to 'release', 'Nightly' = "
                "'beta'. Defaults to %s" % DEFAULT_BRANCH
            ),
        },
        "os": {
            "required": False,
            "description": (
                "The macOS version you're requesting TextMate for use on. "
                "Defaults to %s" % DEFAULT_OS
            ),
        },
    }
    output_variables = {"url": {"description": "URL to the latest TextMate 2 tbz."}}

    def main(self):
        url = BASE_URL + self.env.get("branch", DEFAULT_BRANCH)
        os = self.env.get("os", DEFAULT_OS)
        # Using curl to fetch Location header(s) because urllib/2
        # cannot verify the SSL cert and the server won't accept this
        # TextMate's SSL hostnames don't seem to match the SSL cert name,
        # depending on the CA bundle being used. This can be verified
        # using the 'requests' Python library.
        proc = Popen(
            ["/usr/bin/curl", "-ILs", url + "?os=" + os], stdout=PIPE, stderr=PIPE
        )
        out, err = proc.communicate()
        parsed_url = None
        if err:
            print(err)
            raise ProcessorError("curl returned an error: %s" % out)
        for line in out.splitlines():
            if line.startswith("Location"):
                parsed_url = line.split()[1]
        if not parsed_url:
            raise ProcessorError(
                "curl didn't find a resolved 'Location' header we can use. "
                "Full curl output:\n %s" % "\n".join(out.splitlines())
            )

        self.env["url"] = parsed_url


if __name__ == "__main__":
    PROCESSOR = TextMateURLProvider()
    PROCESSOR.execute_shell()
