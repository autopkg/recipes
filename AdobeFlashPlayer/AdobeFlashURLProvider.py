#!/usr/bin/python
#
# Copyright 2018 Glynn Lane
#
# Based on AdobeFlashURLProvider.py, Copyright 2010 Per Olofsson
# Based on URLTextSearcher.py, Copyright 2014 Jesse Peterson, Copyright 2015 Greg Neagle
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
"""See docstring for AdobeFlashURLProvider class"""

from xml.etree import ElementTree

from autopkglib import ProcessorError
from autopkglib.URLGetter import URLGetter

__all__ = ["AdobeFlashURLProvider"]

UPDATE_XML_URL = (
    "http://fpdownload2.macromedia.com/"
    "get/flashplayer/update/current/xml/version_en_mac_pl.xml"
)

DOWNLOAD_TEMPLATE_URL = (
    "https://fpdownload.macromedia.com/"
    "get/flashplayer/pdc/%s/install_flash_player_osx.dmg"
)


class AdobeFlashURLProvider(URLGetter):
    """Provides URL to the latest Adobe Flash Player release."""

    description = __doc__
    input_variables = {
        "url": {
            "required": False,
            "description": (
                "Override URL. If provided, this processor "
                "just returns without doing anything."
            ),
        },
        "version": {
            "required": False,
            "description": (
                "Specific version to download. If not defined, "
                "defaults to latest version."
            ),
        },
        "request_headers": {
            "description": (
                "Optional dictionary of headers to include with "
                "the download request."
            ),
            "required": False,
        },
        "curl_opts": {
            "description": (
                "Optional array of curl options to include with "
                "the download request."
            ),
            "required": False,
        },
        "CURL_PATH": {
            "required": False,
            "default": "/usr/bin/curl",
            "description": "Path to curl binary. Defaults to /usr/bin/curl.",
        },
    }
    output_variables = {
        "url": {"description": "URL to the latest Adobe Flash Player release."}
    }

    def prepare_curl_cmd(self):
        """Assemble curl command and return it."""
        curl_cmd = super(AdobeFlashURLProvider, self).prepare_curl_cmd()
        self.add_curl_common_opts(curl_cmd)
        curl_cmd.append(UPDATE_XML_URL)
        return curl_cmd

    def get_adobeflash_dmg_url(self):
        """Return the URL for the Adobe Flash DMG"""
        # pylint: disable=no-self-use
        version = self.env.get("version")
        if not version:
            curl_cmd = self.prepare_curl_cmd()
            xml_data = self.download_with_curl(curl_cmd)

            try:
                root = ElementTree.fromstring(xml_data)
            except (OSError, IOError, ElementTree.ParseError) as err:
                raise Exception("Can't read %s: %s" % (xml_data, err))

            # extract version number from the XML
            version = None
            if root.tag == "XML":
                update = root.find("update")
                if update is not None:
                    version = update.attrib.get("version")

            if not version:
                raise ProcessorError("Update XML in unexpected format.")
        else:
            self.output("Using provided version %s" % version)

        # use version number to build a download URL
        version = version.replace(",", ".")
        return DOWNLOAD_TEMPLATE_URL % version

    def main(self):
        """Return a download URL for latest Mac Flash Player"""

        if "url" in self.env:
            self.output("Using input URL %s" % self.env["url"])
            return
        self.env["url"] = self.get_adobeflash_dmg_url()
        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = AdobeFlashURLProvider()
    PROCESSOR.execute_shell()
