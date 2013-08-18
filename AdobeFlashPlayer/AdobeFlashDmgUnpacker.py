#!/usr/bin/env python
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


import os
import FoundationPlist
import tempfile
import shutil
import subprocess

from autopkglib.DmgMounter import DmgMounter
from autopkglib import Processor, ProcessorError


__all__ = ["AdobeFlashDmgUnpacker"]


class AdobeFlashDmgUnpacker(DmgMounter):
    description = "Mounts a Flash dmg and extracts the Player pkg payload to pkgroot."
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": 
                "Path to a dmg containing the Flash player installer.",
        },
        "pkgroot": {
            "required": True,
            "description": 
                "Path to where the new package root will be created.",
        },
    }
    output_variables = {
        "version": {
            "description": "Version of the flash plugin.",
        },
    }
    
    __doc__ = description
    
    def read_bundle_info(self, path):
        """Read Contents/Info.plist inside a bundle."""
        
        try:
            info = FoundationPlist.readPlist(
                os.path.join(path, "Contents", "Info.plist"))
        except FoundationPlist.FoundationPlistException as err:
            raise ProcessorError(err)
        return info

    def extract_payload(self, pkg_path, extract_root):
        '''Extract package contents to extract_root, preserving intended
         directory structure'''
        info_plist = os.path.join(pkg_path, "Contents/Info.plist")
        archive_path = os.path.join(pkg_path, "Contents/Archive.pax.gz")
        if not os.path.exists(info_plist):
            raise ProcessorError("Info.plist not found in pkg")
        if not os.path.exists(archive_path):
            raise ProcessorError("Archive.pax.gz not found in pkg")

        if os.path.exists(extract_root):
            try:
                shutil.rmtree(extract_root)
            except (OSError, IOError), err:
                raise ProcessorError("Failed to remove extract_root: %s" % err)

        try:
            info = FoundationPlist.readPlist(info_plist)
        except FoundationPlist.FoundationPlistException, err:
            raise ProcessorError("Failed to read Info.plist: %s" % err)

        install_target = info.get("IFPkgFlagDefaultLocation", "/").lstrip("/")
        extract_path = os.path.join(extract_root, install_target)
        try:
            os.makedirs(extract_path, 0755)
        except (OSError, IOError), err:
            raise ProcessorError("Failed to create extract_path: %s" % err)

        # Unpack payload.
        try:
            p = subprocess.Popen(("/usr/bin/ditto",
                                  "-x",
                                  "-z",
                                  archive_path,
                                  extract_path),
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as err:
            raise ProcessorError(
                "ditto execution failed with error code %d: %s" 
                % (err.errno, err.strerror))
        if p.returncode != 0:
            raise ProcessorError("Unpacking payload failed: %s" % err)

    def decompress_plugin(self, pkg_path, pkgroot):
        '''Patches postflight binary to decompress the Flash Player.plugin'''
        # Create temporary directory that we'll use to uncompress the plugin
        temp_path = tempfile.mkdtemp(prefix="flashXX", dir="/private/tmp")
        try:
            # temp path length must match original path length or our
            # patching can't possibly work
            if len(temp_path) != len("/Library/Internet Plug-Ins"):
                raise ProcessorError("temp_path length mismatch.")

            # Move Flash Player.plugin.lzma to our temp_path
            src = os.path.join(pkgroot, 
                "Library/Internet Plug-Ins/Flash Player.plugin.lzma")
            try:
                shutil.move(src, temp_path)
            except (OSError, IOError), err:
                raise ProcessorError(
                    "Couldn't move %s to %s" % (src, temp_path))

            # Patch postflight executable.
            # It's hard-coded to work on 
            # "/Library/Internet Plug-Ins/Flash Player.plugin.lzma",
            # so patch with a pathname the exact same length and
            # hope for the best...
            with open(os.path.join(
                        pkg_path, "Contents/Resources/postflight"), "rb") as f:
                postflight = f.read()
            postflight_path = os.path.join(temp_path, "postflight")
            with open(postflight_path, "wb") as f:
                f.write(postflight.replace(
                    "/Library/Internet Plug-Ins", temp_path))
            os.chmod(postflight_path, 0700)

            # Run patched postflight to unpack plugin.
            subprocess.check_call(postflight_path)

            # Check to see if we got a uncompressed plugin where we expect
            plugin_path = os.path.join(temp_path, "Flash Player.plugin")
            if not os.path.isdir(plugin_path):
                raise ProcessorError("Unpacking Flash plugin failed.")

            # Move plugin back into pkgroot.
            plugin_destination = os.path.join(pkgroot, 
                "Library/Internet Plug-Ins/Flash Player.plugin")
            shutil.copytree(plugin_path, plugin_destination, symlinks=True)
        finally:
            shutil.rmtree(temp_path)

    def copy_install_app(self, mount_point, pkgroot):
        '''Copy installation app to pkgroot as Adobe Flash Player Install 
        Manager.app'''

        source_app_path = os.path.join(
            mount_point, "Install Adobe Flash Player.app")
        dest_path = os.path.join(pkgroot, "Applications/Utilities")
        dest_app_path = os.path.join(
            dest_path, "Adobe Flash Player Install Manager.app")
        try:
            os.makedirs(dest_path, 0755)
            shutil.copytree(source_app_path, dest_app_path)
        except (OSError, IOError), err:
            raise ProcessorError(
                "Couldn't copy Adobe Flash Player Install Manager.app")

        # remove embedded pkg from copied app
        embedded_pkg_path = os.path.join(dest_app_path,
            "Contents/Resources/Adobe Flash Player.pkg")
        try:
            shutil.rmtree(embedded_pkg_path)
        except (OSError, IOError), err:
            raise ProcessorError(
                "Couldn't clean up Adobe Flash Player Install Manager.app")

    def main(self):
        # Mount the image.
        mount_point = self.mount(self.env["dmg_path"])
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            pkgroot = self.env['pkgroot']

            # extract package payload
            pkg_path = os.path.join(mount_point,
                "Install Adobe Flash Player.app",
                "Contents/Resources/Adobe Flash Player.pkg")
            self.extract_payload(pkg_path, pkgroot)

            # decompress the actual plugin
            self.decompress_plugin(pkg_path, pkgroot)

            # copy app to pkgroot as Adobe Flash Player Install Manager.app
            self.copy_install_app(mount_point, pkgroot)

            # Read version of plugin
            plugin_path = os.path.join(pkgroot, 
                "Library/Internet Plug-Ins/Flash Player.plugin")
            info = self.read_bundle_info(plugin_path)
            self.env["version"] = info["CFBundleShortVersionString"]

        except BaseException as e:
            raise ProcessorError(e)
        finally:
            self.unmount(self.env["dmg_path"])


if __name__ == '__main__':
    processor = AdobeFlashDmgUnpacker()
    processor.execute_shell()
