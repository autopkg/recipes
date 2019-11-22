#!/usr/bin/python
#
# Copyright 2013 Greg Neagle
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
"""See docstring for AdobeReaderRepackager class"""

from __future__ import absolute_import

import os
import shutil
import subprocess
from xml.etree import ElementTree

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter

__all__ = ["AdobeReaderRepackager"]


class AdobeReaderRepackager(DmgMounter):

    # Modifies the Adobe Reader installer pkg so that:
    #
    # 1) preinstall script does not interfere with installation when installed
    #    by root (for example, with Munki) -- the included preinstall script has
    #    a bunch of unneeded stuff in it and attempts to move any currently
    #    installed copy of Adobe Reader into the current user's trash before
    #    install. We replace this with a simple script that just does an
    #    rm -r $install_location/Adobe Reader.app
    #
    # 2) Modifies the Distribution script to enable installation on any volume;
    #    this should allow use of this package in InstaDMG/System Image Utility/
    #    Filewave Lightning imaging workflows, and with Deploy Studio as a
    #    non-postponed install.
    #
    #    The postinstall script decompresses several files inside the
    #    Adobe Reader.app application bundle. In the past, this was another
    #    thing preventing install on non-boot volumes. But testing with the
    #    11.0.3 installer pkg seems to indicate that the postinstall script and
    #    decompress utility does the right thing on non-boot volumes, so nothing
    #    special needs to be done with this.
    #
    #    One could argue that it would make for a "neater" package to eliminate
    #    the postinstall script and the decompress bit; I'm taking the position
    #    of doing the minimum required to make the package work in the required
    #    scenarios.
    #
    # The basic set of operations:
    #
    # 1) Expand the pkg with pkgutil --expand
    # 2) Modify the Distribution file to allow install anywhere by removing
    #    the <domains> element if it exists.
    # 3) Replace the preinstall in application.pkg with our own
    # 4) Reflatten the pkg with pkgutil --flatten
    #
    # Note that this will remove any signing that is present. This is actually
    # OK; it should not prevent any distribution system (Munki, Casper, etc)
    # from installing this package.
    #
    # Though the AdobeReaderURLProvider can get Reader 10 as well as 11, it
    # is unlikely that this provider can properly repackage Reader 10.
    #
    """Mounts an Adobe Reader XI install dmg and repackages the AdobeReader.pkg
    for automated deployment."""
    description = __doc__
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Path to a dmg containing the Adobe Reader installer.",
        }
    }
    output_variables = {"pkg_path": "Path to the repackaged package."}

    def find_pkg(self, dir_path):
        """Return path to the first package in dir_path"""
        # pylint: disable=no-self-use
        for item in os.listdir(dir_path):
            if item.endswith(".pkg"):
                return os.path.join(dir_path, item)
        raise ProcessorError("No package found in %s" % dir_path)

    def expand(self, pkg, expand_dir):
        """Uses pkgutil to expand a flat package."""
        # pylint: disable=no-self-use
        if os.path.isdir(expand_dir):
            try:
                shutil.rmtree(expand_dir)
            except (OSError, IOError) as err:
                raise ProcessorError("Can't remove %s: %s" % (expand_dir, err))
        try:
            subprocess.check_call(["/usr/sbin/pkgutil", "--expand", pkg, expand_dir])
        except subprocess.CalledProcessError as err:
            raise ProcessorError("%s expanding %s" % (err, pkg))
        return expand_dir

    def flatten(self, expanded_pkg, destination):
        """Flatten an expanded flat pkg"""
        # pylint: disable=no-self-use
        if os.path.exists(destination):
            try:
                os.unlink(destination)
            except OSError as err:
                raise ProcessorError("Can't remove %s: %s" % (destination, err))
        try:
            subprocess.check_call(
                ["/usr/sbin/pkgutil", "--flatten", expanded_pkg, destination]
            )
        except subprocess.CalledProcessError as err:
            raise ProcessorError("%s flattening %s" % (err, expanded_pkg))

    def modify_distribution(self, expanded_pkg):
        """Modify the package Distribution file so that installation is allowed
        on non-boot volumes."""
        # pylint: disable=no-self-use
        dist_file = os.path.join(expanded_pkg, "Distribution")
        if not os.path.exists(dist_file):
            raise ProcessorError("%s not found")
        try:
            dist = ElementTree.parse(dist_file)
        except (OSError, IOError, ElementTree.ParseError) as err:
            raise ProcessorError("Can't read %s: %s" % (dist_file, err))

        dist_root = dist.getroot()
        if dist_root.tag not in ["installer-script", "installer-gui-script"]:
            raise ProcessorError("Distribution file is not in the expected format.")
        domains = dist_root.find("domains")
        if domains is not None:
            dist_root.remove(domains)
            try:
                dist.write(dist_file)
            except (OSError, IOError) as err:
                raise ProcessorError("Could not write %s: %s" % (dist_file, err))

    def replace_app_preinstall(self, expanded_pkg):
        """Replace the preinstall script in application.pkg with our own"""
        pkg_name = os.path.basename(expanded_pkg)
        app_pkg = os.path.join(expanded_pkg, "application.pkg")
        if not os.path.exists(app_pkg):
            raise ProcessorError("application.pkg not found!")
        preinstall_script = os.path.join(app_pkg, "Scripts/preinstall")
        if pkg_name.startswith("AcroRdrDC"):
            our_script = os.path.join(
                os.path.dirname(__file__),
                "package_resources/scripts/readerdc_preinstall",
            )
        else:
            our_script = os.path.join(
                os.path.dirname(__file__), "package_resources/scripts/reader_preinstall"
            )
        if not os.path.exists(our_script):
            raise ProcessorError("%s not found" % our_script)
        try:
            os.unlink(preinstall_script)
        except (OSError, IOError) as err:
            raise ProcessorError("%s removing %s" % (err, preinstall_script))
        try:
            shutil.copy(our_script, preinstall_script)
        except (OSError, IOError) as err:
            raise ProcessorError(
                "%s copying %s to %s" % (err, our_script, preinstall_script)
            )
        self.output(
            "Replaced pkg preinstall script with our custom script at %s" % our_script
        )

    def main(self):
        # Mount the image.
        mount_point = self.mount(self.env["dmg_path"])
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            pkg = self.find_pkg(mount_point)
            pkg_name = os.path.splitext(os.path.basename(pkg))[0]
            expand_dir = os.path.join(self.env["RECIPE_CACHE_DIR"], pkg_name)
            modified_pkg = os.path.join(
                self.env["RECIPE_CACHE_DIR"], os.path.basename(pkg)
            )
            expanded_pkg = self.expand(pkg, expand_dir)
            self.modify_distribution(expanded_pkg)
            self.replace_app_preinstall(expanded_pkg)
            self.flatten(expanded_pkg, modified_pkg)
            self.env["pkg_path"] = modified_pkg

        except Exception as err:
            raise ProcessorError(err)
        finally:
            self.unmount(self.env["dmg_path"])


if __name__ == "__main__":
    PROCESSOR = AdobeReaderRepackager()
    PROCESSOR.execute_shell()
