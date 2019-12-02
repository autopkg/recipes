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
    }
    output_variables = {
        "python_path": {"description": "Path to built Python framework."}
    }

    def clone_git_repo(self, target_dir):
        """Clone the Relocatable Python git repo."""
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

    def build_python_framework(self, target_dir):
        """Build the relocatable python framework."""
        dest = os.path.join(self.env["RECIPE_CACHE_DIR"], "Python.framework")
        # Prepare landing zone
        if os.path.exists(dest):
            shutil.rmtree(dest)
        script_path = os.path.join(target_dir, "make_relocatable_python_framework.py")
        cmd = [
            script_path,
            "--python-version",
            self.env["python_version"],
            "--pip-requirements",
            self.env["requirements_path"],
            "--destination",
            dest,
        ]
        self.output("Building relocatable python framework...")
        try:
            results = subprocess.run(cmd, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise ProcessorError(e)
        if results.stdout:
            self.output(results, verbose_level=2)
        return dest

    def main(self):
        target_dir = os.path.join(self.env["RECIPE_CACHE_DIR"], "relocatable-python")
        # Clone the relocatable python repo
        self.clone_git_repo(target_dir)
        # Build the python framework
        framework_path = self.build_python_framework(target_dir)
        if os.path.exists(framework_path):
            self.output(f"Framework built at {framework_path}")
            self.env["python_path"] = framework_path
        else:
            raise ProcessorError(f"Framework not found at path {framework_path}")


if __name__ == "__main__":
    PROCESSOR = GenerateRelocatablePython()
    PROCESSOR.execute_shell()
