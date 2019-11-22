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
"""See docstring for AdobeReaderURLProvider class"""

import json

from autopkglib import ProcessorError
from autopkglib.URLGetter import URLGetter

__all__ = ["AdobeReaderURLProvider"]

AR_BASE_URL = (
    "http://get.adobe.com/reader/webservices/json/standalone/"
    "?platform_type=Macintosh&platform_dist=OSX&platform_arch=x86-32"
    "&platform_misc=%s&language=%s&eventname=readerotherversions"
)

LANGUAGE_DEFAULT = "English"
MAJOR_VERSION_DEFAULT = "11"
OS_VERSION_DEFAULT = "10.8.0"

MAJOR_VERSION_MATCH_STR = "adobe/reader/mac/%s"


class AdobeReaderURLProvider(URLGetter):
    """Provides URL to the latest Adobe Reader release."""

    description = __doc__
    input_variables = {
        "language": {
            "required": False,
            "description": (
                "Which language to download. Examples: 'English', "
                "'German', 'Japanese', 'Swedish'. Default is %s." % LANGUAGE_DEFAULT
            ),
        },
        "os_version": {
            "required": False,
            "description": (
                "OS X version to use in URL search. Defaults to %s."
                " Reader DC requires '10.9.0'" % OS_VERSION_DEFAULT
            ),
        },
        "major_version": {
            "required": False,
            "description": (
                "Major version. Examples: '10', '11', 'AcrobatDC'. "
                "Defaults to %s" % MAJOR_VERSION_DEFAULT
            ),
        },
        "base_url": {"required": False, "description": "Default is %s" % AR_BASE_URL},
    }
    output_variables = {
        "url": {"description": "URL to the latest Adobe Reader release."}
    }

    def get_reader_dmg_url(self, base_url, language, major_version, os_version):
        """Returns download URL for Adobe Reader DMG"""
        request_url = base_url % (os_version, language)
        header = {"x-requested-with": "XMLHttpRequest"}
        json_response = self.download(request_url, headers=header)

        reader_info = json.loads(json_response)
        major_version_string = MAJOR_VERSION_MATCH_STR % major_version
        matches = [
            item["download_url"]
            for item in reader_info
            if major_version_string in item["download_url"]
        ]
        try:
            return matches[0]
        except IndexError:
            raise ProcessorError(
                "Can't find Adobe Reader download URL for %s, version %s"
                % (language, major_version)
            )

    def main(self):
        # Determine base_url, language and major_version.
        base_url = self.env.get("base_url", AR_BASE_URL)
        language = self.env.get("language", LANGUAGE_DEFAULT)
        major_version = self.env.get("major_version", MAJOR_VERSION_DEFAULT)
        os_version = self.env.get("os_version", OS_VERSION_DEFAULT)

        self.env["url"] = self.get_reader_dmg_url(
            base_url, language, major_version, os_version
        )
        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = AdobeReaderURLProvider()
    PROCESSOR.execute_shell()
