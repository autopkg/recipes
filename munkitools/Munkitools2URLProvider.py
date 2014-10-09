#!/usr/bin/python
#
# Copyright 2014 Tim Sutton, borrows liberally from
# MunkitoolsURLProvider, copyright 2013 Greg Neagle
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
"""See docstring for Munkitools2URLProvider processor"""

import re
import urllib2

from autopkglib import Processor, ProcessorError


__all__ = ["Munkitools2URLProvider"]


RELEASE_BASE_URL = "https://github.com/munki/munki/releases"

RE_PKG_LINK = re.compile(
    r'href="(?P<url>/munki/munki/releases/download/.*?/munkitools-2[.0-9]*.pkg)"')


class Munkitools2URLProvider(Processor):
    """Provides a download URL for Munki tools."""
    description = __doc__
    input_variables = {
        "base_url": {
            "required": False,
            "description": "Default is %s" % RELEASE_BASE_URL,
        }
    }
    output_variables = {
        "url": {
            "description": "URL to Munkitools flat pkg download.",
        },
    }

    def get_munkitools_pkg_url(self, base_url):
        """Get data from URL and return a download URL"""
        #pylint: disable=no-self-use
        # Read HTML index.
        try:
            fref = urllib2.urlopen(base_url)
            html = fref.read()
            fref.close()
        except BaseException as err:
            raise ProcessorError("Can't download %s: %s" % (base_url, err))

        match = RE_PKG_LINK.search(html)

        if not match:
            raise ProcessorError(
                "Couldn't find munkitools download URL in %s" % base_url)

        link = urllib2.quote(match.group("url"), safe=":/%")
        if link.startswith("/"):
            link = "https://github.com" + link
        return link

    def main(self):
        """Find and return a download URL"""
        base_url = self.env.get("base_url", RELEASE_BASE_URL)
        if base_url == RELEASE_BASE_URL:
            self.env["url"] = self.get_munkitools_pkg_url(base_url)
        else:
            self.env["url"] = base_url
        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = Munkitools2URLProvider()
    PROCESSOR.execute_shell()
