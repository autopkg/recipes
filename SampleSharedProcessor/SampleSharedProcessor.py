#!/usr/local/autopkg/python
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
"""See docstring for SampleSharedProcessor class"""


import os

from autopkglib import Processor, ProcessorError

__all__ = ["SampleSharedProcessor"]


class SampleSharedProcessor(Processor):
    """This processor doesn't do anything useful. It is a demonstration of using
    a shared processor via a recipe repo."""

    description = __doc__
    input_variables = {
        "shared_processor_input_var": {
            "required": True,
            "description": "Test the use of an input variable in a shared processor.",
        }
    }
    output_variables = {
        "module_file_path": {"description": "Outputs this module's file path."}
    }

    def main(self):
        try:
            module_file_path = os.path.abspath(__file__)
            self.output(
                f"The input variable data '{self.env['shared_processor_input_var']}' "
                "was given to this Processor."
            )
            self.output(f"This shared processor is located at {module_file_path}")
            self.env["module_file_path"] = module_file_path
        except Exception as err:
            # handle unexpected errors here
            raise ProcessorError(err)


if __name__ == "__main__":
    PROCESSOR = SampleSharedProcessor()
    PROCESSOR.execute_shell()
