#!/usr/bin/python
#
# Copyright 2013 Timothy Sutton
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
"""See docstring for AdobeAcrobatProUpdateInfoProvider class"""

import re

from autopkglib import ProcessorError
from autopkglib.URLGetter import URLGetter

try:
    from plistlib import readPlistFromString
except ImportError:
    from plistlib import readPlistFromBytes as readPlistFromString

__all__ = ["AdobeAcrobatProUpdateInfoProvider"]


MUNKI_UPDATE_NAME_DEFAULT = "AdobeAcrobatPro{MAJREV}_Update"
VERSION_DEFAULT = "latest"
TARGET_DEFAULT = "10.9"
META_BASE_URL = "https://armmf.adobe.com/arm-manifests/mac"
MANIFEST_URL_TEMPLATE = META_BASE_URL + "/{MAJREV}/manifest_url_template.txt"
DL_BASE_URL = "http://armdl.adobe.com"

_URL_VARS = {"PROD": "com_adobe_Acrobat_Pro", "PROD_ARCH": "univ"}
SUPPORTED_VERS = ["9", "10", "11"]


class AdobeAcrobatProUpdateInfoProvider(URLGetter):
    """Provides URL to the latest Adobe Acrobat Pro release."""

    description = __doc__
    input_variables = {
        "target_os": {
            "required": False,
            "description": ("OS X version. Defaults to %s" % TARGET_DEFAULT),
        },
        "major_version": {
            "required": True,
            "description": (
                "Major version. Currently supports: %s" % ", ".join(SUPPORTED_VERS)
            ),
        },
        "version": {
            "required": False,
            "description": ("Update version number. Defaults to %s." % VERSION_DEFAULT),
        },
        "munki_update_name": {
            "required": False,
            "description": (
                "Name for the update in Munki. Defaults to %s"
                % MUNKI_UPDATE_NAME_DEFAULT
            ),
        },
    }
    output_variables = {
        "url": {"description": "URL to the latest Adobe Reader release."},
        "version": {"description": "Version for this update."},
        "additional_pkginfo": {
            "description": "A pkginfo possibly containing additional 'requires' items."
        },
    }

    def process_target_os(self, os_version):
        """Returns a tuple of major and minor versions"""
        # pylint: disable=no-self-use
        major_and_minor_versions = os_version.split(".")
        try:
            major_vers = major_and_minor_versions[0]
            minor_vers = major_and_minor_versions[1]
            if major_vers != "10":
                raise ProcessorError(
                    "Major OS Version %s is not supported" % major_vers
                )
            if int(minor_vers) < 6:
                raise ProcessorError(
                    "Minor OS Version %s is not supported" % minor_vers
                )
        except (TypeError, ValueError):
            raise ProcessorError("OS X Version %s not recognised" % os_version)
        return (major_vers, minor_vers)

    def process_url_vars(self, url):
        """Substitute keys in URL templates with actual values"""
        # pylint: disable=no-self-use
        for var in list(_URL_VARS.keys()):
            subbed_url = url.replace(r"{{{}}}".format(var), _URL_VARS[var])
            url = subbed_url
        return subbed_url

    def get_manifest_data(self, manifest_plist_url):
        """Get manifest(plist) data from a url"""
        manifest_plist_response = self.download(manifest_plist_url)
        try:
            manifest_data = readPlistFromString(manifest_plist_response)
        except Exception as err:
            raise ProcessorError(
                "Can't parse manifest plist at %s: %s" % (manifest_plist_url, err)
            )

        if "PatchURL" not in manifest_data.keys():
            raise ProcessorError(
                "Manifest plist key '%s' not found at %s"
                % ("PatchURL", manifest_plist_url)
            )

        return manifest_data

    def get_acrobat_metadata(self, get_version):
        """Returns a tuple: (url, version, previous_required_version)"""
        template_url = self.process_url_vars(MANIFEST_URL_TEMPLATE)
        template_response = self.download(template_url, text=True)

        if get_version != "latest":
            # /{MAJREV}/latest/{PROD}_{PROD_ARCH}.plist -->
            # /{MAJREV}/get_version/{PROD}_{PROD_ARCH}.plist
            template_response = re.sub(r"\d+\.\d+\.\d+", get_version, template_response)

        manifest_url = self.process_url_vars(
            META_BASE_URL + template_response.decode("utf-8")
        )
        manifest_data = self.get_manifest_data(manifest_url)

        composed_dl_url = DL_BASE_URL + manifest_data["PatchURL"]
        version = manifest_data["BuildNumber"]
        # If there's a previous required version,
        # store that version for later use
        if manifest_data.get("PreviousURLTemplate", "") != "noTemplate":
            prev_manifest_url = self.process_url_vars(
                META_BASE_URL + manifest_data["PreviousURLTemplate"]
            )
            prev_manifest_data = self.get_manifest_data(prev_manifest_url)
            prev_version = prev_manifest_data["BuildNumber"]
        return (composed_dl_url, version, prev_version)

    def main(self):
        """Do our processor task!"""
        target_os = self.env.get("target_os", TARGET_DEFAULT)
        major_version = self.env["major_version"]
        get_version = self.env.get("version", VERSION_DEFAULT)
        if major_version not in SUPPORTED_VERS:
            raise ProcessorError(
                "major_version %s not one of those supported: %s"
                % (major_version, ", ".join(SUPPORTED_VERS))
            )

        # Adobe require a target OS X version to be passed to the URL on more recent
        # updates
        target_os_parsed = self.process_target_os(target_os)
        # global _URL_VARS global statement not needed to modify a key/value pair
        _URL_VARS["MAJREV"] = major_version
        _URL_VARS["OS_VER_MAJ"] = target_os_parsed[0]
        _URL_VARS["OS_VER_MIN"] = target_os_parsed[1]

        munki_update_name = self.env.get("munki_update_name", "")
        if not munki_update_name:
            munki_update_name = self.process_url_vars(MUNKI_UPDATE_NAME_DEFAULT)
        (url, version, prev_version) = self.get_acrobat_metadata(get_version)

        new_pkginfo = {}

        # if our required version is something other than a base version
        # should match a version ending in '.0.0', '.00.0', '.00.00', etc.
        if not re.search(r"\.[0]+\.[0]+", prev_version):
            new_pkginfo["requires"] = ["%s-%s" % (munki_update_name, prev_version)]
            self.output("Update requires previous version: %s" % prev_version)
        new_pkginfo["minimum_os_version"] = "%s.0" % target_os
        new_pkginfo["version"] = version
        self.env["additional_pkginfo"] = new_pkginfo
        self.env["url"] = url
        self.env["version"] = version
        self.output("Found URL %s" % self.env["url"])


if __name__ == "__main__":
    PROCESSOR = AdobeAcrobatProUpdateInfoProvider()
    PROCESSOR.execute_shell()
