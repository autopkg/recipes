#!/usr/bin/python
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
"""See docstring for TheUnarchiverURLProvider class"""

import re
import urllib2

from autopkglib import Processor, ProcessorError


__all__ = ["TheUnarchiverURLProvider"]


THEUNARCHIVER_BASE_URL = "http://unarchiver.c3.cx/unarchiver"
RE_THEUNARCHIVER_ZIP = re.compile(
    r'href="(?P<url>http://theunarchiver.googlecode.com/files/'
    + r'TheUnarchiver[^"]+\.zip)"', re.I)


class TheUnarchiverURLProvider(Processor):
    """Provides URL to the latest release of The Unarchiver."""
    description = __doc__
    input_variables = {
        "base_url": {
            "required": False,
            "description": "Default is 'http://unarchiver.c3.cx/unarchiver'.",
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest release of The Unarchiver.",
        },
    }

    def get_theunarchiver_zip_url(self, base_url):
        """Find download UTL for zip download"""
        #pylint: disable=no-self-use
        # Read HTML index.
        try:
            # Without specifing an Accept, the server returns
            # Content-Location: unarchiver.css instead of unarchiver.html
            req = urllib2.Request(base_url)
            req.add_header("Accept",
                           "text/html,application/xhtml+xml,application/xml")
            fref = urllib2.urlopen(req)
            html = fref.read()
            fref.close()
        except BaseException as err:
            raise ProcessorError("Can't download %s: %s" % (base_url, err))

        # Search for download link.
        match = RE_THEUNARCHIVER_ZIP.search(html)
        if not match:
            raise ProcessorError(
                "Couldn't find The Unarchiver download URL in %s" % base_url)

        # Return URL.
        return match.group("url")

    def main(self):
        # Determine base_url.
        base_url = self.env.get('base_url', THEUNARCHIVER_BASE_URL)

        self.env["url"] = self.get_theunarchiver_zip_url(base_url)
        self.output("Found URL %s" % self.env["url"])


if __name__ == '__main__':
    PROCESSOR = TheUnarchiverURLProvider()
    PROCESSOR.execute_shell()
