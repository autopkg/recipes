#!/usr/bin/env python
#
# Copyright 2014 Timothy Sutton
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

import json
import urllib2

from autopkglib import Processor, ProcessorError

__all__ = ["GitHubReleasesInfoProvider"]

# http://developer.github.com/v3/repos/releases

class GitHubReleasesInfoProvider(Processor):
    description = ("Get URL and version info from the latest release on a GitHub project's releases page.")
    input_variables = {
        "github_repo": {
            "required": True,
            "description": ("Name of a GitHub user and repo, ie. 'MagerValp/AutoDMG'")
        },
        "github_auth_token": {
            "required": False,
            "description": "API token to send with request. Without this, your client is rate-limited to 60 requests per hour."
        }
    }
    output_variables = {
        "url": {
            "description": "URL for the first asset found for the project's latest release."
        },
        "version": {
            "description": "Version info parsed, naively derived from the release's tag."
        }
    }

    __doc__ = description

    API_BASE_URL = "https://api.github.com"
    def call_api(self, endpoint, query=None, accept="application/vnd.github.v3+json", token=None):
        """Return dict from JSON result of an API call. Endpoints begin with a forward-slash."""
        url = self.API_BASE_URL + endpoint
        if query:
            url += "?" + query
        req = urllib2.Request(url)
        req.add_header("Accept", accept)
        if token:
            req.add_header("Authorization", "token %s" % token)
        json_resp = urllib2.urlopen(req)
        data = json.load(json_resp)
        return data or None


    def get_asset_url(self, repo, asset_id, token=None):
        url = self.API_BASE_URL + "/repos/%s/releases/assets/%s" % (
                repo, asset_id)
        req = urllib2.Request(url)
        req.add_header("Accept", "application/octet-stream")
        if token:
            req.add_header("Authorization", "token %s" % token)
        urlfd = urllib2.urlopen(req)
        asset_url = urlfd.geturl()
        return asset_url


    def main(self):
        repo = self.env.get("github_repo")
        releases_uri = "/repos/%s/releases" % repo
        releases = self.call_api(releases_uri,
                            token=self.env.get("github_auth_token"))
        if releases:
            # we very naively assume (for now) that the latest release is first in the list
            latest = releases[0]
        else:
            raise ProcessorError("No releases found for repo '%s'" % repo)

        tag = latest["tag_name"]
        assets = latest.get("assets")
        if assets:
            asset = assets[0]
        asset_id = asset["id"]

        asset_url = self.get_asset_url(repo, asset_id)
        self.env["url"] = asset_url

        if tag.startswith("v"):
            self.env["version"] = tag[1:]
        else:
            self.env["version"] = tag

if __name__ == "__main__":
    processor = GitHubReleasesInfoProvider()
    processor.execute_shell()
