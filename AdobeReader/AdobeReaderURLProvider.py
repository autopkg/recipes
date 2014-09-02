#!/usr/bin/python
#
# Copyright 2010 Per Olofsson
# Additions copyright 2014 wycomco GmbH (choules@wycomco.de)
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


import json
import urllib2

from autopkglib import Processor, ProcessorError


__all__ = ["AdobeReaderURLProvider"]


AR_BASE_URL = (
    "http://get.adobe.com/reader/webservices/json/standalone/"
    "?platform_type=Macintosh&platform_dist=OSX&platform_arch=x86-32"
    "&platform_misc=10.8.0&language=%s&eventname=readerotherversions")

LANGUAGE_DEFAULT = "English"
MAJOR_VERSION_DEFAULT = "11"

MAJOR_VERSION_MATCH_STR = "adobe/reader/mac/%s"

MULTILANGUAGE_UPDATER = "false"

AR_UPDATER_DOWNLOAD_URL = (
    "http://download.adobe.com/"
    "pub/adobe/reader/mac/%s.x/%s/misc/AdbeRdrUpd%s.dmg")

AR_UPDATER_BASE_URL = "https://armmf.adobe.com/arm-manifests/mac"

AR_URL_TEMPLATE = "/%s/current_version_url_template.txt"

AR_MAJREV_IDENTIFIER = "{MAJREV}"

class AdobeReaderURLProvider(Processor):
    """Provides URL to the latest Adobe Reader release."""
    description = __doc__
    input_variables = {
        "language": {
            "required": False,
            "description": ("Which language to download. Examples: 'English', "
                            "'German', 'Japanese', 'Swedish'. Default is %s."
                            % LANGUAGE_DEFAULT),
        },
        "major_version": {
            "required": False,
            "description": ("Major version. Examples: '10', '11'. Defaults to "
                            "%s" % MAJOR_VERSION_DEFAULT)
        },
        "base_url": {
            "required": False,
            "description": "Default is %s" % AR_BASE_URL,
        },
        "multilanguage_updater": {
            "required": False,
            "description": ("Full version (English only) or updater "
                            "(multilanguage). "
                            "Examples: 'true', 'false'. Defaults to "
                            "%s" % MULTILANGUAGE_UPDATER)
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Adobe Reader release.",
        },
        "version": {
            "description": "Version for this update.",
        },
    }

    def get_reader_dmg_url(self, base_url, language, major_version):
        '''Returns download URL for Adobe Reader DMG'''
        #pylint: disable=no-self-use
        request = urllib2.Request(base_url % language)
        request.add_header("x-requested-with", "XMLHttpRequest")
        try:
            url_handle = urllib2.urlopen(request)
            json_response = url_handle.read()
            url_handle.close()
        except BaseException as err:
            raise ProcessorError("Can't open %s: %s" % (base_url, err))

        reader_info = json.loads(json_response)
        major_version_string = MAJOR_VERSION_MATCH_STR % major_version
        matches = [item["download_url"] for item in reader_info
                   if major_version_string in item["download_url"]]
        try:
            url = matches[0]
        except IndexError:
            raise ProcessorError(
                "Can't find Adobe Reader download URL for %s, version %s"
                % (language, major_version))

        matches = [item["Version"] for item in reader_info
                   if major_version_string in item["download_url"]]

        try:
            version = matches[0]
        except IndexError:
            raise ProcessorError(
                "Can't find version information on Adobe Reader download URL"
                " for %s, version %s"
                % (language, major_version))

        return (url, version)

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

        version_string = version_string.replace(
            AR_MAJREV_IDENTIFIER, major_version)

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
        # Determine base_url, language and major_version.
        base_url = self.env.get("base_url", AR_BASE_URL)
        language = self.env.get("language", LANGUAGE_DEFAULT)
        major_version = self.env.get("major_version", MAJOR_VERSION_DEFAULT)
        multilanguage_updater = self.env.get(
            "multilanguage_updater", MULTILANGUAGE_UPDATER)

        if multilanguage_updater == "true":
            (url, version) = self.get_reader_updater_dmg_url(
                major_version)
        else:
            (url, version) = self.get_reader_dmg_url(
                base_url, language, major_version)

        self.env["url"] = url
        self.env["version"] = version

        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = AdobeReaderURLProvider()
    PROCESSOR.execute_shell()

