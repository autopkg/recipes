#!/usr/local/autopkg/python
#
# Copyright 2010 Per Olofsson
#           2022 Nate Felton <n8felton>
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
from urllib.parse import quote

from autopkglib.URLGetter import URLGetter

__all__ = ["AdobeReaderURLProvider"]

# https://rdc.adobe.io/reader/products?os=Mac%20OS%2010.14.0&api_key=dc-get-adobereader-cdn
# {"products":{"reader":[{"displayName":"Reader DC 2022.001.20112 for Mac","fileSize":327.5,"version":"22.001.20112"}],"dcPro":[]},"addons":[]}
RDC_PRODUCTS_URL = "https://rdc.adobe.io/reader/products?os={OS_VERSION}&api_key=dc-get-adobereader-cdn"
# https://rdc.adobe.io/reader/downloadUrl?name=Reader%20DC%202022.001.20112%20for%20Mac&os=Mac%20OS%2010.14.0&api_key=dc-get-adobereader-cdn
# {"downloadURL":"https://ardownload2.adobe.com/pub/adobe/reader/mac/AcrobatDC/2200120112/AcroRdrDC_2200120112_MUI.dmg","installer":"standalone","saveName":"AcroRdrDC_2200120112_MUI.dmg"}
RDC_DOWNLOAD_URL = "https://rdc.adobe.io/reader/downloadUrl?name={DISPLAY_NAME}&os={OS_VERSION}&api_key=dc-get-adobereader-cdn"

OS_VERSION_DEFAULT = "Mac OS 10.14.0"


class AdobeReaderURLProvider(URLGetter):
    """Provides URL to the latest Adobe Acrobat Reader DC release."""

    description = __doc__
    input_variables = {
        "os_version": {
            "required": False,
            "description": (
                f"macOS version to use in URL search. Defaults to '{OS_VERSION_DEFAULT}'."
            ),
        },
        "base_url": {
            "required": False,
            "description": f"Default is {RDC_PRODUCTS_URL}",
        },
        "download_url": {
            "required": False,
            "description": f"Default is {RDC_DOWNLOAD_URL}",
        },
    }
    output_variables = {
        "url": {"description": "URL to the latest Adobe Acrobat Reader DC release."},
        "filename": {
            "description": "The Adobe provided filename to save the download as."
        },
        "version": {
            "description": "Version of the latest Adobe Acrobat Reader DC release."
        },
    }

    def get_reader_download_info(self, base_url, os_version):
        """Returns information required to download Adobe Acrobat Reader DC"""
        request_url = base_url.format(OS_VERSION=os_version)
        self.output(f"RDC_PRODUCTS_URL: {request_url}", 3)
        json_response = self.download(request_url)
        reader_info = json.loads(json_response)
        self.output(reader_info, 3)
        display_name = reader_info["products"]["reader"][0]["displayName"]
        version = reader_info["products"]["reader"][0]["version"]
        self.output(f"[displayName] : {display_name}")
        self.output(f"[version]     : {version}")
        return display_name, version

    def get_reader_download_url(self, rdc_download_url, os_version, display_name):
        """Returns the download URL for the latest version of Adobe Acrobat Reader DC"""
        rdc_download_url = rdc_download_url.format(
            OS_VERSION=os_version, DISPLAY_NAME=display_name
        )
        self.output(f"RDC_DOWNLOAD_URL: {rdc_download_url}", 3)
        json_response = self.download(rdc_download_url)
        download_info = json.loads(json_response)
        self.output(download_info, 3)
        download_url = download_info["downloadURL"]
        filename = download_info["saveName"]
        self.output(f"[download_url]: {download_url}")
        return download_url, filename

    def main(self):
        """Main process"""
        base_url = self.env.get("base_url", RDC_PRODUCTS_URL)
        rdc_download_url = self.env.get("download_url", RDC_DOWNLOAD_URL)
        os_version = self.env.get("os_version", OS_VERSION_DEFAULT)
        if not os_version.startswith("Mac OS"):
            self.output(
                "WARNING: Please update the OS_VERSION in your override "
                f"from '{os_version}' to 'Mac OS {os_version}'"
            )
            os_version = f"Mac OS {os_version}"
        # Quote those os_version to make it a URL safe string
        os_version = quote(os_version)
        display_name, self.env["version"] = self.get_reader_download_info(
            base_url, os_version
        )
        # Quote those display_name to make it a URL safe string
        display_name = quote(display_name)
        self.env["url"], self.env["filename"] = self.get_reader_download_url(
            rdc_download_url, os_version, display_name
        )


if __name__ == "__main__":
    PROCESSOR = AdobeReaderURLProvider()
    PROCESSOR.execute_shell()
