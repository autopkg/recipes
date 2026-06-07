#!/usr/local/autopkg/python
#
# Copyright 2019 Nick McSpadden
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
"""See docstring for GenerateRelocatablePython class"""

import os
import shutil
import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["GenerateRelocatablePython"]


class GenerateRelocatablePython(Processor):
    """Finds the root autopkg-autopkg-foo folder from the expanded autopkg zip
    archive"""

    description = __doc__
    input_variables = {
        "requirements_path": {
            "required": True,
            "description": "Path to the Requirements.txt file to use.",
        },
        "python_version": {
            "required": True,
            "description": "What version of Python to build.",
        },
        "os_version": {
            "required": True,
            "description": "What OS to fetch.",
        },
        "upgrade_pip": {
            "required": False,
            "description": "Whether to upgrade pip to the latest version.",
        },
        "relocatable_python_sha": {
            "required": False,
            "description": (
                "Git commit SHA to check out after cloning relocatable-python. "
                "Pin this to a known-good commit to avoid surprise breakage from "
                "upstream changes."
            ),
        },
    }
    output_variables = {
        "python_path": {"description": "Path to built Python framework."}
    }

    def clone_git_repo(self, target_dir):
        """Clone the Relocatable Python git repo, optionally pinning to a SHA."""
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        git_repo = "https://github.com/gregneagle/relocatable-python.git"
        cmd = ["git", "clone", git_repo, target_dir]
        self.output(f"Cloning Relocatable Python into {target_dir}")
        self.output(f"Command: {' '.join(cmd)}", verbose_level=4)
        try:
            subprocess.run(cmd, timeout=3600, check=True)
        except subprocess.CalledProcessError as e:
            raise ProcessorError(e)
        sha = self.env.get("relocatable_python_sha")
        if sha:
            self.output(f"Checking out relocatable-python at {sha}")
            try:
                subprocess.run(
                    ["git", "-C", target_dir, "checkout", sha],
                    timeout=60,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                raise ProcessorError(e)

    def build_python_framework(self, target_dir):
        """Build the relocatable python framework."""
        dest = os.path.join(self.env["RECIPE_CACHE_DIR"], "Python.framework")
        # Prepare landing zone
        if os.path.exists(dest):
            shutil.rmtree(dest)
        script_path = os.path.join(target_dir, "make_relocatable_python_framework.py")
        cmd = [
            "/usr/local/autopkg/python",
            script_path,
            "--python-version",
            self.env["python_version"],
            "--pip-requirements",
            self.env["requirements_path"],
            "--os-version",
            self.env["os_version"],
            "--destination",
            dest,
        ]
        if self.env.get("upgrade_pip"):
            cmd.append("--upgrade-pip")
        self.output("Building relocatable python framework...")
        self.output(f"Command: {' '.join(cmd)}", verbose_level=4)
        try:
            results = subprocess.run(cmd, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise ProcessorError(e)
        if results.stdout:
            self.output(results, verbose_level=2)
        return dest

    def install_sitecustomize(self, framework_path):
        """Write sitecustomize.py so OpenSSL finds certifi's CA bundle after relocation."""
        major_minor = ".".join(self.env["python_version"].split(".")[:2])
        site_packages = os.path.join(
            framework_path,
            "Versions",
            major_minor,
            "lib",
            f"python{major_minor}",
            "site-packages",
        )
        sitecustomize_path = os.path.join(site_packages, "sitecustomize.py")
        if os.path.exists(sitecustomize_path):
            self.output(
                f"sitecustomize.py already exists at {sitecustomize_path}; skipping"
            )
            return
        # OpenSSL's compiled-in CA path doesn't exist after relocation; point at certifi.
        content = """\
import os


def _ssl_cert_file_is_valid():
    path = os.environ.get('SSL_CERT_FILE')
    return bool(path) and os.path.isfile(path)


if not _ssl_cert_file_is_valid():
    try:
        import certifi
    except ImportError:
        pass
    else:
        os.environ['SSL_CERT_FILE'] = certifi.where()
"""
        with open(sitecustomize_path, "w") as f:
            f.write(content)
        self.output(f"Installed sitecustomize.py at {sitecustomize_path}")

    def smoke_test_https(self, framework_path):
        """Verify that urllib HTTPS works from the built framework."""
        major_minor = ".".join(self.env["python_version"].split(".")[:2])
        python_bin = os.path.join(
            framework_path, "Versions", major_minor, "bin", f"python{major_minor}"
        )
        self.output("Smoke-testing HTTPS from built framework...")
        try:
            subprocess.run(
                [
                    python_bin,
                    "-c",
                    "import urllib.request; urllib.request.urlopen('https://example.com')",
                ],
                timeout=30,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise ProcessorError(f"HTTPS smoke test failed: {e}")
        self.output("HTTPS smoke test passed.")

    def main(self):
        target_dir = os.path.join(self.env["RECIPE_CACHE_DIR"], "relocatable-python")
        # Clone the relocatable python repo
        self.clone_git_repo(target_dir)
        # Build the python framework
        framework_path = self.build_python_framework(target_dir)
        if os.path.exists(framework_path):
            self.output(f"Framework built at {framework_path}")
            self.install_sitecustomize(framework_path)
            self.smoke_test_https(framework_path)
            self.env["python_path"] = framework_path
        else:
            raise ProcessorError(f"Framework not found at path {framework_path}")


if __name__ == "__main__":
    PROCESSOR = GenerateRelocatablePython()
    PROCESSOR.execute_shell()
