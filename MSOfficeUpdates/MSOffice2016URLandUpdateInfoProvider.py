#!/usr/bin/env python
#
# Copyright 2015 Allister Banks and Tim Sutton,
# based on MSOffice2011UpdateInfoProvider by Greg Neagle
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
# Disabling 'no-env-member' for recipe processors
#pylint:disable=e1101
"""See docstring for MSOffice2016URLandUpdateInfoProvider class"""

import plistlib
import urllib2
import re

from operator import itemgetter

from autopkglib import Processor, ProcessorError


__all__ = ["MSOffice2016URLandUpdateInfoProvider"]

# CULTURE_CODE defaulting to 'en-US' as the installers and updates seem to be
# multilingual.
CULTURE_CODE = "0409"
BASE_URL = "http://www.microsoft.com/mac/autoupdate/%s15.xml"
PROD_DICT = {
    'Excel':'XCEL',
    'OneNote':'ONMC',
    'Outlook':'OPIM',
    'PowerPoint':'PPT3',
    'Word':'MSWD',
}
LOCALE_ID_INFO_URL = "https://msdn.microsoft.com/en-us/goglobal/bb964664.aspx"

class MSOffice2016URLandUpdateInfoProvider(Processor):
    """Provides a download URL for the most recent version of MS Office 2016."""
    input_variables = {
        "locale_id": {
            "required": False,
            "default": "1033",
            "description": (
                "Locale ID that determines the language "
                "that is retrieved from the metadata, currently only "
                "used by the update description. See %s "
                "for a list of locale codes. The default is en-US."
                % LOCALE_ID_INFO_URL)
        },
        "product": {
            "required": True,
            "description": "Name of product to fetch, e.g. Excel.",
        },
        "version": {
            "required": False,
            "default": "latest",
            "description": ("Update version to fetch. Currently the only "
                            "supported value is 'latest', which is the "
                            "default."),
        },
    }
    output_variables = {
        "additional_pkginfo": {
            "description":
                "Some pkginfo fields extracted from the Microsoft metadata.",
        },
        "description": {
            "description":
                "Description of the update from the manifest, in the language "
                "given by the locale_id input variable.",
        },
        "version": {
            "description":
                ("The version of the update as extracted from the Microsoft "
                 "metadata.")
        },
        "minimum_os_version": {
            "description":
                ("The minimum os version required by the update as extracted "
                 "from the Microsoft metadata.")
        },
        "url": {
            "description": "URL to the latest installer.",
        },
    }
    description = __doc__

    def sanity_check_expected_triggers(self, item):
        """Raises an exeception if the Trigger Condition or
        Triggers for an update don't match what we expect.
        Protects us if these change in the future."""
        # MS currently uses "Registered File" placeholders, which get replaced
        # with the bundle of a given application ID. In other words, this is
        # the bundle version of the app itself.
        if not item.get("Trigger Condition") == ["and", "Registered File"]:
            raise ProcessorError(
                "Unexpected Trigger Condition in item %s: %s"
                % (item["Title"], item["Trigger Condition"]))
        if not "Registered File" in item.get("Triggers", {}):
            raise ProcessorError(
                "Missing expected 'and Registered File' Trigger in item "
                "%s" % item["Title"])

    def get_installs_items(self, item):
        """Attempts to parse the Triggers to create an installs item using
        only manifest data, making the assumption that CFBundleVersion and
        CFBundleShortVersionString are equal."""
        self.sanity_check_expected_triggers(item)
        version = self.get_version(item)
        installs_item = {
            "CFBundleShortVersionString": version,
            "CFBundleVersion": version,
            "path": ("/Applications/Microsoft %s.app" % self.env["product"]),
            "type": "application",
        }
        return [installs_item]

    def get_version(self, item):
        """Extracts the version of the update item."""
        # We currently expect the version at the end of the Title key,
        # e.g.: "Microsoft Excel Update 15.10.0"
        # item["Title"] = "Microsoft Excel Update 15.10"
        match = re.search(
            r"( Update )(?P<version>\d+\.\d+(\.\d)*)", item["Title"])
        if not match:
            raise ProcessorError(
                "Error validating Office 2016 version extracted "
                "from Title manifest value: '%s'" % item["Title"])
        version = match.group('version')
        return version

    def value_to_os_version_string(self, value):
        """Converts a value to an OS X version number"""
        if isinstance(value, int):
            version_str = hex(value)[2:]
        elif isinstance(value, basestring):
            if value.startswith('0x'):
                version_str = value[2:]
        # OS versions are encoded as hex:
        # 4184 = 0x1058 = 10.5.8
        major = 0
        minor = 0
        patch = 0
        try:
            if len(version_str) == 1:
                major = int(version_str[0])
            if len(version_str) > 1:
                major = int(version_str[0:2])
            if len(version_str) > 2:
                minor = int(version_str[2], 16)
            if len(version_str) > 3:
                patch = int(version_str[3], 16)
        except ValueError:
            raise ProcessorError("Unexpected value in version: %s" % value)
        return "%s.%s.%s" % (major, minor, patch)

    def get_installer_info(self):
        """Gets info about an installer from MS metadata."""
        base_url = BASE_URL % (CULTURE_CODE + PROD_DICT[self.env["product"]])
        version_str = self.env["version"]
        # Get metadata URL
        req = urllib2.Request(base_url)
        # Add the MAU User-Agent, since MAU feed server seems to explicitly
        # block a User-Agent of 'Python-urllib/2.7' - even a blank User-Agent
        # string passes.
        req.add_header("User-Agent",
                       "Microsoft%20AutoUpdate/3.0.6 CFNetwork/720.2.4 Darwin/14.4.0 (x86_64)")
        try:
            fdesc = urllib2.urlopen(req)
            data = fdesc.read()
            fdesc.close()
        except BaseException as err:
            raise ProcessorError("Can't download %s: %s" % (base_url, err))

        metadata = plistlib.readPlistFromString(data)
        if version_str == "latest":
            # Still sort by date, in case we should ever need to support
            # fetching versions other than 'latest'.
            sorted_metadata = sorted(metadata, key=itemgetter('Date'))
            # choose the last item, which should be most recent.
            item = sorted_metadata[-1]

        self.env["url"] = item["Location"]
        self.output("Found URL %s" % self.env["url"])
        self.output("Got update: '%s'" % item["Title"])
        # now extract useful info from the rest of the metadata that could
        # be used in a pkginfo
        pkginfo = {}
        # Get a copy of the description in our locale_id
        all_localizations = item.get("Localized")
        lcid = self.env["locale_id"]
        if lcid not in all_localizations:
            raise ProcessorError(
                "Locale ID %s not found in manifest metadata. Available IDs: "
                "%s. See %s for more details." % (
                    lcid,
                    ", ".join(all_localizations.keys()),
                    LOCALE_ID_INFO_URL))
        manifest_description = all_localizations[lcid]['Short Description']
        # Store the description in a separate output variable and in our pkginfo
        # directly.
        pkginfo["description"] = "<html>%s</html>" % manifest_description
        self.env["description"] = manifest_description

        max_os = self.value_to_os_version_string(item['Max OS'])
        min_os = self.value_to_os_version_string(item['Min OS'])
        if max_os != "0.0.0":
            pkginfo["maximum_os_version"] = max_os
        if min_os != "0.0.0":
            pkginfo["minimum_os_version"] = min_os
        installs_items = self.get_installs_items(item)
        if installs_items:
            pkginfo["installs"] = installs_items

        self.env["version"] = self.get_version(item)
        self.env["minimum_os_version"] = min_os
        self.env["additional_pkginfo"] = pkginfo
        self.env["url"] = item["Location"]
        self.output("Additional pkginfo: %s" % self.env["additional_pkginfo"])

    def main(self):
        """Get information about an update"""
        self.get_installer_info()


if __name__ == "__main__":
    PROCESSOR = MSOffice2016URLandUpdateInfoProvider()
    PROCESSOR.execute_shell()
