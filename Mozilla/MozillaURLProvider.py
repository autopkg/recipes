#!/usr/bin/python
#
# Copyright 2010 Per Olofsson, 2013 Greg Neagle
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
"""See docstring for MozillaURLProvider class"""

import re
import urllib2

from autopkglib import Processor, ProcessorError


__all__ = ["MozillaURLProvider"]


MOZ_BASE_URL = "http://ftp.mozilla.org/pub/mozilla.org"
               #"firefox/releases")
RE_DMG = re.compile(r'a[^>]* href="(?P<filename>[^"]+\.dmg)"')


class MozillaURLProvider(Processor):
    """Provides URL to the latest Firefox release."""
    description = __doc__
    input_variables = {
        "product_name": {
            "required": True,
            "description":
                "Product to fetch URL for. One of 'firefox', 'thunderbird'.",
        },
        "release": {
            "required": False,
            "description": (
                "Which release to download. Examples: 'latest', "
                "'latest-10.0esr', 'latest-esr', 'latest-beta'."),
        },
        "locale": {
            "required": False,
            "description":
                "Which localization to download, default is 'en_US'.",
        },
        "base_url": {
            "required": False,
            "description": "Default is '%s." % MOZ_BASE_URL,
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Mozilla product release.",
        },
    }

    def get_mozilla_dmg_url(self, base_url, product_name, release, locale):
        """Get download URL for Mozilla product"""
        #pylint: disable=no-self-use
        # Allow locale as both en-US and en_US.
        locale = locale.replace("_", "-")

        # Construct download directory URL.
        release_dir = release.lower()

        index_url = "/".join(
            (base_url, product_name, "releases", release_dir, "mac", locale))
        #print >>sys.stderr, index_url

        # Read HTML index.
        try:
            fref = urllib2.urlopen(index_url)
            html = fref.read()
            fref.close()
        except BaseException as err:
            raise ProcessorError("Can't download %s: %s" % (index_url, err))

        # Search for download link.
        match = RE_DMG.search(html)
        if not match:
            raise ProcessorError(
                "Couldn't find %s download URL in %s"
                % (product_name, index_url))

        # Return URL.
        return "/".join(
            (base_url, product_name, "releases", release_dir, "mac", locale,
             match.group("filename")))

    def main(self):
        """Provide a Mozilla download URL"""
        # Determine product_name, release, locale, and base_url.
        product_name = self.env["product_name"]
        release = self.env.get("release", "latest")
        locale = self.env.get("locale", "en_US")
        base_url = self.env.get("base_url", MOZ_BASE_URL)

        self.env["url"] = self.get_mozilla_dmg_url(
            base_url, product_name, release, locale)
        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = MozillaURLProvider()
    PROCESSOR.execute_shell()

