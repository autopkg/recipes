#!/usr/bin/python
#
# Copyright 2014: wycomco GmbH (choules@wycomco.de)
#           2015: modifications by Tim Sutton
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
"""See docstring for AdobeReaderURLProvider class"""
# Disabling warnings for env members and imports that only affect recipe-
# specific processors.
#pylint: disable=e1101

import urllib2

from autopkglib import Processor, ProcessorError


__all__ = ["AdobeReaderUpdatesURLProvider"]

MAJOR_VERSION_DEFAULT = "11"
CHECK_OS_VERSION_DEFAULT = "10.8"
MAJOR_VERSION_MATCH_STR = "adobe/reader/mac/%s"

AR_UPDATER_DOWNLOAD_URL = (
    "http://download.adobe.com/"
    "pub/adobe/reader/mac/%s.x/%s/misc/AdbeRdrUpd%s.dmg")

AR_UPDATER_BASE_URL = "https://armmf.adobe.com/arm-manifests/mac"
AR_URL_TEMPLATE = "/%s/current_version_url_template.txt"
AR_MAJREV_IDENTIFIER = "{MAJREV}"
OSX_MAJREV_IDENTIFIER = "{OS_VER_MAJ}"
OSX_MINREV_IDENTIFIER = "{OS_VER_MIN}"

class AdobeReaderUpdatesURLProvider(Processor):
    """Provides URL to the latest Adobe Reader release."""
    description = __doc__
    input_variables = {
        "major_version": {
            "required": False,
            "description": ("Major version. Examples: '10', '11'. Defaults to "
                            "%s" % MAJOR_VERSION_DEFAULT)
        },
        "os_version": {
            "required": False,
            "default": CHECK_OS_VERSION_DEFAULT,
            "description": ("Version of OS X to check. Default: %s" %
                            CHECK_OS_VERSION_DEFAULT)
        }
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Adobe Reader release.",
        },
        "version": {
            "description": "Version for this update.",
        },
    }

    def get_reader_updater_dmg_url(self, major_version):
        '''Returns download URL for Adobe Reader Updater DMG'''

        request = urllib2.Request(
            AR_UPDATER_BASE_URL + AR_URL_TEMPLATE % major_version)
        try:
            url_handle = urllib2.urlopen(request)
            version_string = url_handle.read()
            url_handle.close()
        except BaseException as err:
            raise ProcessorError("Can't open URL template: %s" % (err))
        os_maj, os_min = self.env["os_version"].split(".")
        version_string = version_string.replace(
            AR_MAJREV_IDENTIFIER, major_version)
        version_string = version_string.replace(OSX_MAJREV_IDENTIFIER, os_maj)
        version_string = version_string.replace(OSX_MINREV_IDENTIFIER, os_min)

        request = urllib2.Request(
            AR_UPDATER_BASE_URL + version_string)
        try:
            url_handle = urllib2.urlopen(request)
            version = url_handle.read()
            url_handle.close()
        except BaseException as err:
            raise ProcessorError("Can't get version string: %s" % (err))

        versioncode = version.replace('.', '')
        url = AR_UPDATER_DOWNLOAD_URL % (major_version, version, versioncode)

        return (url, version)

    def main(self):
        major_version = self.env.get("major_version", MAJOR_VERSION_DEFAULT)

        (url, version) = self.get_reader_updater_dmg_url(major_version)

        self.env["url"] = url
        self.env["version"] = version

        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = AdobeReaderUpdatesURLProvider()
    PROCESSOR.execute_shell()
