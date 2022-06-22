#!/usr/local/autopkg/python

import json

from autopkglib import ProcessorError
from autopkglib.URLGetter import URLGetter

__all__ = ["CorrettoURLGetter"]


class CorrettoURLGetter(URLGetter):
    """
    Downloads the latest indexmap for all corretto releases, provides url and version of choosen
    major_version + architecture

    Requires version 1.4.
    """

    input_variables = {
        "corretto_indexmap_url": {
            "required": False,
            "description": "URL to indexmap of Corretto installers",
            "default": "https://raw.githubusercontent.com/corretto/corretto-downloads/main/latest_links/indexmap_with_checksum.json",
        },
        "major_version": {
            "required": True,
            "description": "Major version of corretto to use: 8,11,17,18",
        },
        "architecture": {
            "required": True,
            "description": "Architecture to use, x64 or aarch64",
        },
    }
    output_variables = {
        "version": {"description": "Version of latest major version"},
        "url": {"description": "Download URL for specified version and architecture"},
        "supported_architectures": {
            "description": "Converted to Munki supported architecture type"
        },
    }
    description = __doc__

    def main(self):
        json_data = self.download(self.env["corretto_indexmap_url"])
        self.output("Got latest indexmap")
        indexmap = json.loads(json_data)
        tail_url = indexmap["macos"][self.env["architecture"]]["jdk"][
            self.env["major_version"]
        ]["pkg"]["resource"]
        self.env["url"] = f"https://corretto.aws{tail_url}"
        self.env["version"] = tail_url.split("-", 3)[2]
        self.env["supported_architectures"] = (
            "x86_64" if self.env["architecture"] == "x64" else "arm64"
        )


if __name__ == "__main__":
    PROCESSOR = CorrettoURLGetter()
    PROCESSOR.execute_shell()
