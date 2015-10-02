#!/usr/bin/python
#
# Copyright 2015 Timothy Sutton, w/ insignificant contributions by Allister Banks
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
"""See docstring for PuppetlabsProductsURLProvider class"""

import urllib2
import re
from distutils.version import LooseVersion

from autopkglib import Processor, ProcessorError

__all__ = ["PuppetlabsProductsURLProvider"]

DL_INDEX = "https://downloads.puppetlabs.com/mac"
DEFAULT_VERSION = "latest"
OS_VERSION = "10.10"

class PuppetlabsProductsURLProvider(Processor):
    """Extracts a URL for a Puppet Labs item."""
    description = __doc__
    input_variables = {
        "product_name": {
            "required": True,
            "description":
                "Product to fetch URL for. One of 'puppet', 'facter', 'hiera',"
                "or 'agent'.",
        },
        "get_version": {
            "required": False,
            "description":
                ("Specific version to request. Defaults to '%s', which "
                 "automatically finds the highest available release version."
                 % (DEFAULT_VERSION)),
        },
        "get_os_version": {
            "required": False,
            "description":
                ("When fetching the puppet-agent, collection-style pkg, "
                 "designates OS. Defaults to '%s'. Currently only 10.9 "
                 "or 10.10 packages are available."
                 % (OS_VERSION)),
        },
    }
    output_variables = {
        "version": {
            "description": "Version of the product.",
        },
        "url": {
            "description": "Download URL.",
        },
    }

    def main(self):
        """Return a download URL for a PuppetLabs item"""
        download_url = DL_INDEX
        prod = self.env["product_name"]
        if prod == 'agent':
            os_version = self.env.get("get_os_version", OS_VERSION)
            version_re = r"\d+\.\d+\.\d+" # e.g.: 10.10/PC1/x86_64/puppet-agent-1.2.5-1.osx10.10.dmg
            download_url += str('/' + os_version + "/PC1/x86_64")
            re_download = ("href=\"(puppet-agent-(%s)-1.osx(%s).dmg)\"" % (version_re, os_version))
        else:
            # look for "product-1.2.3.dmg"
            # skip anything with a '-' following the version no. ('rc', etc.)
            version_re = self.env.get("get_version")
            if not version_re or version_re == DEFAULT_VERSION:
                version_re = r"\d+[\.\d]+"
            re_download = ("href=\"(%s-(%s)+.dmg)\""
                           % (self.env["product_name"].lower(), version_re))

        try:
            data = urllib2.urlopen(download_url).read()
        except BaseException as err:
            raise ProcessorError(
                "Unexpected error retrieving download index: '%s'" % err)

        # (dmg, version)
        candidates = re.findall(re_download, data)
        if not candidates:
            raise ProcessorError(
                "Unable to parse any products from download index.")

        # sort to get the highest version
        highest = candidates[0]
        if  len(candidates) > 1:
            for prod in candidates:
                if LooseVersion(prod[1]) > LooseVersion(highest[1]):
                    highest = prod

        ver, url = highest[1], "%s/%s" % (download_url, highest[0])
        self.env["version"] = ver
        self.env["url"] = url
        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = PuppetlabsProductsURLProvider()
    PROCESSOR.execute_shell()
