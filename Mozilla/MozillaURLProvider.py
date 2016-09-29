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
import urllib
import urllib2
import urlparse
from distutils.version import LooseVersion

from autopkglib import Processor, ProcessorError


__all__ = ["MozillaURLProvider"]


MOZ_BASE_URL = "https://download.mozilla.org/?product=%s-%s&os=osx&lang=%s"

# As of 16 Nov 2015 here are the supported products:
# firefox-latest
# firefox-esr-latest
# firefox-beta-latest
# thunderbird-latest
# thunderbird-beta-latest
# 
# See also:
#    http://ftp.mozilla.org/pub/firefox/releases/latest/README.txt
#    http://ftp.mozilla.org/pub/firefox/releases/latest-esr/README.txt
#    http://ftp.mozilla.org/pub/firefox/releases/latest-beta/README.txt
#    http://ftp.mozilla.org/pub/thunderbird/releases/latest/README.txt
#    http://ftp.mozilla.org/pub/thunderbird/releases/latest-beta/README.txt


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
            "default": 'latest',
            "description": (
                "Which release to download. Examples: 'latest', "
                "'esr-latest', 'beta-latest'. Defaults to 'latest'"),
        },
        "locale": {
            "required": False,
            "default": 'en-US',
            "description":
                "Which localization to download, default is 'en-US'.",
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
        """Assemble download URL for Mozilla product"""
        #pylint: disable=no-self-use
        # Allow locale as both en-US and en_US.
        locale = locale.replace("_", "-")
        
        # fix releases into new format
        if release == 'latest-esr':
            release = 'esr-latest'
        if release == 'latest-beta':
            release = 'beta-latest'

        # Construct download URL.
        return base_url % (product_name, release, locale)

    def main(self):
        """Provide a Mozilla download URL"""
        # Determine product_name, release, locale, and base_url.
        product_name = self.env["product_name"]
        release = self.env.get("release", "latest")
        locale = self.env.get("locale", "en-US")
        base_url = self.env.get("base_url", MOZ_BASE_URL)

        self.env["url"] = self.get_mozilla_dmg_url(
            base_url, product_name, release, locale)
        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = MozillaURLProvider()
    PROCESSOR.execute_shell()

