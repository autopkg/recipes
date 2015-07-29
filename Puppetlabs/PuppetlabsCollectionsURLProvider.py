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
"""See docstring for PuppetlabsCollectionsURLProvider class"""

import urllib2
import re
from distutils.version import LooseVersion

from autopkglib import Processor, ProcessorError

__all__ = ["PuppetlabsCollectionsURLProvider"]

DL_INDEX = "https://downloads.puppetlabs.com/mac/PC1"
DEFAULT_VERSION = "10.10"

class PuppetlabsCollectionsURLProvider(Processor):
    """Extracts a URL for a PuppetLabs collection."""
    description = __doc__
    input_variables = {
        "get_os_version": {
            "required": False,
            "description":
                ("Specific OS version-tagged pkg to request. Defaults to '%s', which "
                 "automatically finds the highest available OS version, currently only 10.9 or 10.10."
                 % (DEFAULT_VERSION)),
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
        """Return a download URL for a PuppetLabs collection"""
        # look for "product-1.2.3-osx-version-x86_64.dmg"
        # e.g. https://downloads.puppetlabs.com/mac/PC1/puppet-agent-1.2.2-osx-10.10-x86_64.dmg
        # skip anything with a '-' following the version no. ('rc', etc.)
        os_version = self.env.get("get_os_version")
        if not os_version:
            os_version == DEFAULT_VERSION
        version_re = r"\d+\.\d+\.\d+" # puppet-agent-1.2.0-osx-10.9-x86_64.dmg
        re_download = ("href=\"(puppet-agent-(%s)-osx-(%s)-x86_64.dmg)\"" % (version_re, os_version))

        try:
            data = urllib2.urlopen(DL_INDEX).read()
        except BaseException as err:
            raise ProcessorError(
                "Unexpected error retrieving download index: '%s'" % err)

        # (dmg, version)
        candidates = re.findall(re_download, data)
        self.output("candidates are %s", candidates)
        if not candidates:
            raise ProcessorError(
                "Unable to parse any products from download index.")

        # sort to get the highest version
        highest = candidates[0]
        if  len(candidates) > 1:
            for prod in candidates:
                if LooseVersion(prod[1]) > LooseVersion(highest[1]):
                    highest = prod

        ver, url = highest[1], "%s/%s" % (DL_INDEX, highest[0])
        self.env["version"] = ver
        self.env["url"] = url
        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = PuppetlabsProductsURLProvider()
    PROCESSOR.execute_shell()
