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
"""See docstring for AdobeFlashURLProvider class"""


import urllib2
from xml.etree import ElementTree

from autopkglib import Processor, ProcessorError


__all__ = ["AdobeFlashURLProvider"]

UPDATE_XML_URL = ("http://fpdownload2.macromedia.com/"
                  "get/flashplayer/update/current/xml/version_en_mac_pl.xml")

DOWNLOAD_TEMPLATE_URL = ("https://fpdownload.macromedia.com/"
                         "get/flashplayer/pdc/%s/install_flash_player_osx.dmg")

class AdobeFlashURLProvider(Processor):
    """Provides URL to the latest Adobe Flash Player release."""
    description = __doc__
    input_variables = {
        "url": {
            "required": False,
            "description": ("Override URL. If provided, this processor "
                            "just returns without doing anything."),
        },
        "version": {
            "required": False,
            "description": ("Specific version to download. If not defined, "
                            "defaults to latest version.")
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Adobe Flash Player release.",
        },
    }

    def get_adobeflash_dmg_url(self):
        '''Return the URL for the Adobe Flash DMG'''
        version = self.env.get("version")
        if not version:
            # Read update XML.
            try:
                fref = urllib2.urlopen(UPDATE_XML_URL)
                xml_data = fref.read()
                fref.close()
            except BaseException as err:
                raise ProcessorError(
                    "Can't download %s: %s" % (UPDATE_XML_URL, err))

            # parse XML data
            try:
                root = ElementTree.fromstring(xml_data)
            except (OSError, IOError, ElementTree.ParseError), err:
                raise Exception("Can't read %s: %s" % (xml_data, err))

            # extract version number from the XML
            version = None
            if root.tag == "XML":
                update = root.find("update")
                if update is not None:
                    version = update.attrib.get('version')

            if not version:
                raise ProcessorError("Update XML in unexpected format.")
        else:
            self.output("Using provided version %s" % version)

        # use version number to build a download URL
        version = version.replace(",", ".")
        return DOWNLOAD_TEMPLATE_URL % version

    def main(self):
        '''Return a download URL for latest Mac Flash Player'''
        if "url" in self.env:
            self.output("Using input URL %s" % self.env["url"])
            return
        self.env["url"] = self.get_adobeflash_dmg_url()
        self.output("Found URL %s" % self.env["url"])


if __name__ == '__main__':
    PROCESSOR = AdobeFlashURLProvider()
    PROCESSOR.execute_shell()
