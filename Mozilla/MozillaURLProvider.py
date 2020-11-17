#!/usr/bin/python
#
# Copyright 2010 Per Olofsson, 2013 Greg Neagle
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
"""See docstring for MozillaURLProvider class"""

from __future__ import absolute_import

import json
import re
from typing import List, Tuple

from autopkglib import URLGetter

__all__: List[str] = ["MozillaURLProvider"]


MOZ_BASE_URL: str = (
    "https://download.mozilla.org/"
    "?product={product_release}-ssl&os={platform}&lang={locale}"
)

MOZ_PRODUCT_VERSIONS_URL: str = (
    "https://product-details.mozilla.org/1.0/{product}_versions.json"
)

# As of July/2020 here are the known supported products, releases, and platforms:
# For linux, linux64, osx, win, and win64:
#  Product            Release
#  -------            -------
#  firefox            latest
#  firefox            version   (i.e., 79.0)
#  firefox-beta       latest
#  firefox-esr        latest
#  firefox-nightly    latest
#
#  thunderbird        latest
#  thunderbird        version (i.e., 78.0)
#  thunderbird-beta   latest
# Additionally for win and win64 there are additional releases for MSI installers:
#  msi-latest
#  <version>-msi (i.e., 79.0-msi)
# Note that the position of 'msi' is different.
#
#  Platforms
#  ---------
#  linux
#  linux64
#  osx
#  win
#  win64
#
# See also:
#    https://releases.mozilla.org/pub/firefox/releases/latest/README.txt
#    https://releases.mozilla.org/pub/firefox/releases/latest-esr/README.txt
#    https://releases.mozilla.org/pub/firefox/releases/latest-beta/README.txt
#    https://releases.mozilla.org/pub/thunderbird/releases/latest/README.txt
#    https://releases.mozilla.org/pub/thunderbird/releases/latest-beta/README.txt
#    https://product-details.mozilla.org/1.0/firefox_versions.json
#    https://product-details.mozilla.org/1.0/thunderbird_versions.json


class MozillaURLProvider(URLGetter):
    """Provides URL to the latest Firefox release."""

    description = __doc__
    input_variables = {
        "product_name": {
            "required": True,
            "description": (
                "Product to fetch URL for. One of: "
                "'firefox', 'firefox-esr', 'firefox-beta', 'firefox-nightly', "
                "'thunderbird', 'thunderbird-beta'."
            ),
        },
        "release": {
            "required": False,
            "default": "latest",
            "description": ("Which release to download. Examples: 'latest', 79.0"),
        },
        "locale": {
            "required": False,
            "default": "en-US",
            "description": ("Which localization to download, default is 'en-US'."),
        },
        "platform": {
            "required": False,
            "default": "osx",
            "description": "Which platform/OS to download: 'osx' (default), 'linux', "
            "'linux64', 'win', 'win64'.",
        },
        "base_url": {
            "required": False,
            "description": (
                f"(Advanced) URL for downloads.  Default is '{MOZ_BASE_URL}'."
            ),
            "default": MOZ_BASE_URL,
        },
        "versions_base_url": {
            "required": False,
            "description": (
                "(Advanced) URL for product release version information. "
                f" Default is '{MOZ_PRODUCT_VERSIONS_URL}'."
            ),
            "default": MOZ_PRODUCT_VERSIONS_URL,
        },
    }
    output_variables = {
        "url": {"description": "URL to the latest Mozilla product release."},
        "moz_version": {
            "description": (
                "Resolved version number for a release normalized to a 3 or 4 digit "
                "semantic version. For example:  'latest-beta' -> 79.0b9 -> 79.0.0.9"
            )
        },
        "moz_original_version": {
            "description": (
                "Pre-normalized version number from the product versions information."
            )
        },
    }

    def fixup_locale(self, locale: str) -> str:
        # Allow locale as both en-US and en_US.
        return locale.replace("_", "-")

    def fixup_product_release(self, product: str, release: str) -> str:
        # Fix product and release into correct format for legacy inputs.
        if release in ("latest-esr", "esr-latest"):
            product += "-esr"
            release = "latest"
        elif release in ("latest-beta", "beta-latest"):
            product += "-beta"
            release = "latest"

        return f"{product}-{release}"

    def normalize_version(self, orig_version: str) -> str:
        """Versions are normalized like these examples:
        * 78.0.2 into 78.0.2,
        * 79.0b9 into 79.0.0.9,
        * 68.10.0esr into 68.10.0,
        * 77.0-msi into 77.0 (a special case for Windows MSI)."""
        norm_version = re.sub(r"[ab]", ".0.", orig_version)
        norm_version = norm_version.replace("esr", "")
        norm_version = norm_version.replace("-msi", "")
        return norm_version

    def resolve_product_release_version(
        self, base_url: str, product: str, release: str
    ) -> Tuple[str, str]:
        """Resolves a symbolic release like 'latest' to a normalized version number.
        Returns a tuple of (normalized version, original version from web api)"""
        if "firefox" in product:
            simple_product = "firefox"
        elif "thunderbird" in product:
            simple_product = "thunderbird"
        else:
            raise ValueError(f"Product '{product}' is not a supported product.")

        product_release = self.fixup_product_release(product, release)
        release_key = ""
        # Some of these keys are not supported for Thunderbird as of July/2020.
        if "esr" in product_release:
            release_key = f"{simple_product.upper()}_ESR"
        elif "beta" in product_release:
            release_key = f"LATEST_{simple_product.upper()}_DEVEL_VERSION"
        elif "nightly" in product_release:
            release_key = f"{simple_product.upper()}_NIGHTLY"
        elif "latest" in product_release:
            release_key = f"LATEST_{simple_product.upper()}_VERSION"
        else:
            # In this case, it must be an unknown symbolic release or a version number.
            # Pass it through normalization, which *should* leave unknown symbolic
            # releases more or less untouched.
            return (self.normalize_version(release), release)

        json_data = self.download(base_url.format(product=simple_product))
        release_data = json.loads(json_data)
        orig_version = release_data[release_key]
        return (self.normalize_version(orig_version), orig_version)

    def main(self):
        """Provide a Mozilla download URL"""
        # Determine product_name, release, locale, and base_url.
        product_name = self.env["product_name"]
        release = self.env.get("release", "latest")
        locale = self.fixup_locale(self.env.get("locale", "en-US"))
        platform = self.env.get("platform", "osx")
        base_url = self.env.get("base_url", MOZ_BASE_URL)

        self.env["url"] = base_url.format(
            product_release=self.fixup_product_release(product_name, release),
            platform=platform,
            locale=locale,
        )
        (
            self.env["moz_version"],
            self.env["moz_original_version"],
        ) = self.resolve_product_release_version(
            self.env["versions_base_url"], product_name, release
        )
        self.env["moz_locale"] = locale
        self.output(f"Found URL {self.env['url']}")


if __name__ == "__main__":
    PROCESSOR = MozillaURLProvider()
    PROCESSOR.execute_shell()
