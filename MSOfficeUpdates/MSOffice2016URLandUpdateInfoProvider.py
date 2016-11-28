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
import re
import urllib2

from autopkglib import Processor, ProcessorError


__all__ = ["MSOffice2016URLandUpdateInfoProvider"]

# CULTURE_CODE defaulting to 'en-US' as the installers and updates seem to be
# multilingual.
CULTURE_CODE = "0409"
BASE_URL = "https://officecdn.microsoft.com/pr/%s/OfficeMac/%s.xml"

# These can be easily be found as "Application ID" in ~/Library/Preferences/com.microsoft.autoupdate2.plist on a 
# machine that has Microsoft AutoUpdate.app installed on it.
#
# Note that Skype, 'MSFB' has a '16' after it, AutoUpdate has a '03' after it while all the other products have '15'

PROD_DICT = {
    'Excel': {'id': 'XCEL15', 'path': '/Applications/Microsoft Excel.app'},
    'OneNote': {'id': 'ONMC15', 'path': '/Applications/Microsoft OneNote.app'},
    'Outlook': {'id': 'OPIM15', 'path': '/Applications/Microsoft Outlook.app'},
    'PowerPoint': {'id': 'PPT315', 'path': '/Applications/Microsoft PowerPoint.app'},
    'Word': {'id': 'MSWD15', 'path': '/Applications/Microsoft Word.app'},
    'SkypeForBusiness': {'id': 'MSFB16', 'path': '/Applications/Skype for Business.app'},
    'AutoUpdate': {
        'id': 'MSau03',
        'path': '/Library/Application Support/Microsoft/MAU2.0/Microsoft AutoUpdate.app'
    }
}
LOCALE_ID_INFO_URL = "https://msdn.microsoft.com/en-us/goglobal/bb964664.aspx"
SUPPORTED_VERSIONS = ["latest", "latest-delta"]
DEFAULT_VERSION = "latest"
CHANNELS = {
    'Production': 'C1297A47-86C4-4C1F-97FA-950631F94777',
    'InsiderSlow': '1ac37578-5a24-40fb-892e-b89d85b6dfaa',
    'InsiderFast': '4B2D7701-0A4F-49C8-B4CB-0C2D4043F51F',
}
DEFAULT_CHANNEL = "Production"

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
            "default": DEFAULT_VERSION,
            "description": ("Update type to fetch. Supported values are: "
                            "'%s'. Defaults to %s."
                            % ("', '".join(SUPPORTED_VERSIONS),
                               DEFAULT_VERSION)),
        },
        "munki_required_update_name": {
            "required": False,
            "default": "",
            "description":
                ("If the update is a delta, a 'requires' key will be set "
                 "according to the minimum version defined in the MS "
                 "metadata. If this key is set, this name will be used "
                 "for the required item. If unset, NAME will be used.")
        },
        "channel": {
            "required": False,
            "default": DEFAULT_CHANNEL,
            "description":
                ("Update feed channel that will be checked for updates. "
                 "Defaults to %s, acceptable values are either a custom "
                 "UUID or one of: %s" % (
                    DEFAULT_CHANNEL,
                    ", ".join(CHANNELS.keys())))
        }
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
        "minimum_version_for_delta": {
            "description":
                ("If this update is a delta, this value will be set to the "
                 "minimum required application version to which this delta "
                 "can be applied. Otherwise it will be an empty string.")
        },
        "url": {
            "description": "URL to the latest installer.",
        },
    }
    description = __doc__
    min_delta_version = ""

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

    def get_installs_items(self, item):
        """Attempts to parse the Triggers to create an installs item using
        only manifest data, making the assumption that CFBundleVersion and
        CFBundleShortVersionString are equal. Skip SkypeForBusiness as its
        xml does not contain a 'Trigger Condition'"""
        if self.env["product"] != 'SkypeForBusiness':
            self.sanity_check_expected_triggers(item)
        version = self.get_version(item)
        # Skipping CFBundleShortVersionString because it doesn't contain
        # anything more specific than major.minor (no build versions
        # distinguishing Insider builds for example)
        installs_item = {
            "CFBundleVersion": version,
            "path": PROD_DICT[self.env["product"]]['path'],
            "type": "application",
        }
        return [installs_item]

    def get_version(self, item):
        """Extracts the version of the update item."""
        # If the 'Update Version' key exists we pull the "full" version string
        # easily from this
        if item.get("Update Version"):
            self.output(
                "Extracting version %s from metadata 'Update Version' key" %
                item["Update Version"])
            return item["Update Version"]

    def get_installer_info(self):
        """Gets info about an installer from MS metadata."""
        # Get the channel UUID, matching against a custom UUID if one is given
        channel_input = self.env.get("channel", DEFAULT_CHANNEL)
        rex = r"^([0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})$"
        match_uuid = re.match(rex, channel_input)
        if not match_uuid and channel_input not in CHANNELS.keys():
            raise ProcessorError(
                "'channel' input variable must be one of: %s or a custom "
                "uuid" % (", ".join(CHANNELS.keys())))
        if match_uuid:
            channel = match_uuid.groups()[0]
        else:
            channel = CHANNELS[channel_input]
        base_url = BASE_URL % (channel,
                               CULTURE_CODE + PROD_DICT[self.env["product"]]['id'])

        # Get metadata URL
        self.output("Requesting xml: %s" % base_url)
        req = urllib2.Request(base_url)
        # Add the MAU User-Agent, since MAU feed server seems to explicitly
        # block a User-Agent of 'Python-urllib/2.7' - even a blank User-Agent
        # string passes.
        req.add_header(
            "User-Agent",
            "Microsoft%20AutoUpdate/3.6.16080300 CFNetwork/760.6.3 Darwin/15.6.0 (x86_64)")

        try:
            fdesc = urllib2.urlopen(req)
            data = fdesc.read()
            fdesc.close()
        except BaseException as err:
            raise ProcessorError("Can't download %s: %s" % (base_url, err))

        metadata = plistlib.readPlistFromString(data)
        item = {}
        # According to MS, update feeds for a given 'channel' will only ever
        # have two items: a full and a delta. Delta updates will have a
        # 'FullUpdaterLocation' key, so filter by the array according to
        # which item has that key.
        if self.env["version"] == "latest":
            item = [u for u in metadata if not u.get("FullUpdaterLocation")]
        elif self.env["version"] == "latest-delta":
            item = [u for u in metadata if u.get("FullUpdaterLocation")]
        if not item:
            raise ProcessorError("Could not find an applicable update in "
                                 "update metadata.")
        item = item[0]

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

        # Minimum OS version key should exist always, but default to the current
        # minimum as of 16/11/03
        pkginfo["minimum_os_version"] = item.get('Minimum OS', '10.10.5')
        installs_items = self.get_installs_items(item)
        if installs_items:
            pkginfo["installs"] = installs_items

        # Extra work to do if this is a delta updater
        if self.env["version"] == "latest-delta":
            try:
                rel_versions = item["Triggers"]["Registered File"]["VersionsRelative"]
            except KeyError:
                raise ProcessorError("Can't find expected VersionsRelative"
                                     "keys for determining minimum update "
                                     "required for delta update.")
            for expression in rel_versions:
                operator, ver_eval = expression.split()
                if operator == ">=":
                    self.min_delta_version = ver_eval
                    break
            if not self.min_delta_version:
                raise ProcessorError("Not able to determine minimum required "
                                     "version for delta update.")
            # Put minimum_update_version into installs item
            self.output("Adding minimum required version: %s" %
                        self.min_delta_version)
            pkginfo["installs"][0]["minimum_update_version"] = \
                self.min_delta_version
            required_update_name = self.env["NAME"]
            if self.env["munki_required_update_name"]:
                required_update_name = self.env["munki_required_update_name"]
            # Add 'requires' array
            pkginfo["requires"] = ["%s-%s" % (required_update_name,
                                              self.min_delta_version)]

        self.env["version"] = self.get_version(item)
        self.env["minimum_os_version"] = pkginfo["minimum_os_version"]
        self.env["minimum_version_for_delta"] = self.min_delta_version
        self.env["additional_pkginfo"] = pkginfo
        self.env["url"] = item["Location"]
        self.output("Additional pkginfo: %s" % self.env["additional_pkginfo"])

    def main(self):
        """Get information about an update"""
        if self.env["version"] not in SUPPORTED_VERSIONS:
            raise ProcessorError("Invalid 'version': supported values are '%s'"
                                 % "', '".join(SUPPORTED_VERSIONS))
        self.get_installer_info()


if __name__ == "__main__":
    PROCESSOR = MSOffice2016URLandUpdateInfoProvider()
    PROCESSOR.execute_shell()
