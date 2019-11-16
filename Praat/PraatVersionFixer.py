#!/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3
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
"""See docstring for PraatVersionFixer class"""


import os.path

from autopkglib import Processor, ProcessorError
from Foundation import (
    NSData,
    NSPropertyListMutableContainers,
    NSPropertyListSerialization,
    NSPropertyListXMLFormat_v1_0,
)

__all__ = ["PraatVersionFixer"]


class PraatVersionFixer(Processor):
    """Fixes Praat version string."""

    description = __doc__
    input_variables = {
        "app_path": {"required": True, "description": "Path to Praat.app."}
    }
    output_variables = {
        "bundleid": {"description": "Bundle identifier of Praat.app."},
        "version": {"description": "Version of Praat.app."},
    }

    def read_bundle_info(self, path):
        """Read Contents/Info.plist inside a bundle."""
        plistpath = os.path.join(path, "Contents", "Info.plist")
        (
            info,
            _,
            error,
        ) = NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(  # noqa
            NSData.dataWithContentsOfFile_(plistpath),
            NSPropertyListMutableContainers,
            None,
            None,
        )
        if error:
            raise ProcessorError(f"Can't read {plistpath}: {error}")

        return info

    def write_bundle_info(self, info, path):
        """Write Contents/Info.plist inside a bundle."""
        plistpath = os.path.join(path, "Contents", "Info.plist")
        (
            plist_data,
            error,
        ) = NSPropertyListSerialization.dataFromPropertyList_format_errorDescription_(  # noqa
            info, NSPropertyListXMLFormat_v1_0, None
        )
        if error:
            raise ProcessorError(f"Can't serialize {plistpath}: {error}")

        if not plist_data.writeToFile_atomically_(plistpath, True):
            raise ProcessorError(f"Can't write {plistpath}")

    def main(self):
        """Perform our Processor's task"""
        app_path = self.env["app_path"]
        info = self.read_bundle_info(app_path)
        self.env["bundleid"] = info["CFBundleIdentifier"]
        version = info["CFBundleShortVersionString"].replace("Praat ", "")
        info["CFBundleShortVersionString"] = version
        self.env["version"] = version
        self.write_bundle_info(info, app_path)


if __name__ == "__main__":
    PROCESSOR = PraatVersionFixer()
    PROCESSOR.execute_shell()
