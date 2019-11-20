#!/usr/local/autopkg/python
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

import certifi
from autopkglib import Processor, ProcessorError

try:
    from urllib.request import urlopen  # For Python 3
except ImportError:
    from urllib2 import urlopen  # For Python 2

try:
    from plistlib import readPlistFromString
except ImportError:
    from plistlib import readPlistFromBytes as readPlistFromString


__all__ = ["AdobeReaderUpdatesURLProvider"]

MAJOR_VERSION_DEFAULT = "11"
CHECK_OS_VERSION_DEFAULT = "10.8"

AR_UPDATER_DOWNLOAD_URL = (
    "http://download.adobe.com/" "pub/adobe/reader/mac/{}.x/{}/misc/AdbeRdrUpd{}.dmg"
)
AR_UPDATER_DOWNLOAD_URL2 = "http://ardownload.adobe.com"


AR_UPDATER_BASE_URL = "https://armmf.adobe.com/arm-manifests/mac"
AR_URL_TEMPLATE = "/{}/current_version_url_template.txt"
AR_MANIFEST_TEMPLATE = "/{}/manifest_url_template.txt"
AR_MAJREV_IDENTIFIER = "{MAJREV}"
OSX_MAJREV_IDENTIFIER = "{OS_VER_MAJ}"
OSX_MINREV_IDENTIFIER = "{OS_VER_MIN}"
AR_PROD_IDENTIFIER = "{PROD}"
AR_PROD_ARCH_IDENTIFIER = "{PROD_ARCH}"
AR_PROD = "com_adobe_Reader"
AR_PROD_ARCH = "univ"


class AdobeReaderUpdatesURLProvider(Processor):
    """Provides URL to the latest Adobe Reader release."""

    description = __doc__
    input_variables = {
        "major_version": {
            "required": False,
            "description": (
                "Major version. Examples: '10', '11'. Defaults to "
                f"{MAJOR_VERSION_DEFAULT}"
            ),
        },
        "os_version": {
            "required": False,
            "default": CHECK_OS_VERSION_DEFAULT,
            "description": (
                f"Version of OS X to check. Default: {CHECK_OS_VERSION_DEFAULT}"
            ),
        },
    }
    output_variables = {
        "url": {"description": "URL to the latest Adobe Reader release."},
        "version": {"description": "Version for this update."},
    }

    def get_reader_updater_pkg_url(self, major_version):
        """Returns download URL for Adobe Reader Updater DMG"""

        try:
            url_handle = urlopen(
                AR_UPDATER_BASE_URL + AR_MANIFEST_TEMPLATE.format(major_version),
                cafile=certifi.where(),
            )
            version_string = url_handle.read().decode()
            url_handle.close()
        except Exception as err:
            raise ProcessorError(f"Can't open manifest template: {err}")
        os_maj, os_min = self.env["os_version"].split(".")
        version_string = version_string.replace(AR_MAJREV_IDENTIFIER, major_version)
        version_string = version_string.replace(OSX_MAJREV_IDENTIFIER, os_maj)
        version_string = version_string.replace(OSX_MINREV_IDENTIFIER, os_min)
        version_string = version_string.replace(AR_PROD_IDENTIFIER, AR_PROD)
        version_string = version_string.replace(AR_PROD_ARCH_IDENTIFIER, AR_PROD_ARCH)

        try:
            url_handle = urlopen(
                AR_UPDATER_BASE_URL + version_string, cafile=certifi.where()
            )
            plist = readPlistFromString(url_handle.read())
            url_handle.close()
        except Exception as err:
            raise ProcessorError(f"Can't get or read manifest: {err}")

        url = AR_UPDATER_DOWNLOAD_URL2 + plist["PatchURL"]
        return url

    def get_reader_updater_dmg_url(self, major_version):
        """Returns download URL for Adobe Reader Updater DMG"""

        try:
            url_handle = urlopen(
                AR_UPDATER_BASE_URL + AR_URL_TEMPLATE.format(major_version),
                cafile=certifi.where(),
            )
            version_string = url_handle.read().decode()
            url_handle.close()
        except Exception as err:
            raise ProcessorError(f"Can't open URL template: {err}")
        os_maj, os_min = self.env["os_version"].split(".")
        version_string = version_string.replace(AR_MAJREV_IDENTIFIER, major_version)
        version_string = version_string.replace(OSX_MAJREV_IDENTIFIER, os_maj)
        version_string = version_string.replace(OSX_MINREV_IDENTIFIER, os_min)

        try:
            url_handle = urlopen(
                AR_UPDATER_BASE_URL + version_string, cafile=certifi.where()
            )
            version = url_handle.read().decode()
            url_handle.close()
        except Exception as err:
            raise ProcessorError(f"Can't get version string: {err}")

        versioncode = version.replace(".", "")
        url = AR_UPDATER_DOWNLOAD_URL.format(major_version, version, versioncode)

        return (url, version)

    def main(self):
        major_version = self.env.get("major_version", MAJOR_VERSION_DEFAULT)

        (url, version) = self.get_reader_updater_dmg_url(major_version)
        # only need the version, getting the URL from the manifest now
        url = self.get_reader_updater_pkg_url(major_version)

        self.env["url"] = url
        self.env["version"] = version

        self.output(f"Found URL {self.env['url']}")


if __name__ == "__main__":
    PROCESSOR = AdobeReaderUpdatesURLProvider()
    PROCESSOR.execute_shell()
