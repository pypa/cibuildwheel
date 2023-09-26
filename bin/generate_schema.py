#!/usr/bin/env python

import copy
import json
from typing import Any

import yaml

starter = """
$id: https://github.com/pypa/cibuildwheel/blob/main/cibuildwheel/resources/cibuildwheel.schema.json
$schema: http://json-schema.org/draft-07/schema
additionalProperties: false
description: cibuildwheel's settings.
type: object
properties:
  archs:
    description: Change the architectures built on your machine by default.
    type: string_array
  before-all:
    description: Execute a shell command on the build system before any wheels are built.
    type: string_array
  before-build:
    description: Execute a shell command preparing each wheel's build.
    type: string_array
  before-test:
    description: Execute a shell command before testing each wheel.
    type: string_array
  build:
    default: ['*']
    description: Choose the Python versions to build.
    type: string_array
  build-frontend:
    default: default
    description: Set the tool to use to build, either "pip" (default for now) or "build"
    oneOf:
      - enum: [pip, build, default]
      - type: string
        pattern: '^pip; ?args:'
      - type: string
        pattern: '^build; ?args:'
      - type: object
        additionalProperties: false
        required: [name]
        properties:
          name:
            enum: [pip, build]
          args:
            type: array
            items:
              type: string
  build-verbosity:
    type: integer
    minimum: -3
    maximum: 3
    default: 0
    description: Increase/decrease the output of pip wheel.
  config-settings:
    description: Specify config-settings for the build backend.
    type: string_table_array
  container-engine:
    oneOf:
      - enum: [docker, podman]
      - type: string
        pattern: '^docker; ?create_args:'
      - type: string
        pattern: '^podman; ?create_args:'
      - type: object
        additionalProperties: false
        required: [name]
        properties:
          name:
            enum: [docker, podman]
          create-args:
            type: array
            items:
              type: string
  dependency-versions:
    default: pinned
    description: Specify how cibuildwheel controls the versions of the tools it uses
    type: string
  environment:
    description: Set environment variables needed during the build.
    type: string_table
  environment-pass:
    description: Set environment variables on the host to pass-through to the container
      during the build.
    type: string_array
  manylinux-aarch64-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  manylinux-i686-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  manylinux-ppc64le-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  manylinux-pypy_aarch64-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  manylinux-pypy_i686-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  manylinux-pypy_x86_64-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  manylinux-s390x-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  manylinux-x86_64-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-aarch64-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-i686-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-ppc64le-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-s390x-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-x86_64-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  repair-wheel-command:
    type: string_array
    description: Execute a shell command to repair each built wheel.
  skip:
    description: Choose the Python versions to skip.
    type: string_array
  test-command:
    description: Execute a shell command to test each built wheel.
    type: string_array
  test-extras:
    description: Install your wheel for testing using `extras_require`
    type: string_array
  test-requires:
    description: Install Python dependencies before running the tests
    type: string_array
  test-skip:
    description: Skip running tests on some builds.
    type: string_array
"""

schema = yaml.safe_load(starter)

string_array = yaml.safe_load(
    """
- type: string
- type: array
  items:
    type: string
"""
)

string_table_array = yaml.safe_load(
    """
- type: string
- type: object
  additionalProperties: false
  patternProperties:
    .+:
      oneOf:
        - type: string
        - type: array
          items:
            type: string
"""
)

string_table = yaml.safe_load(
    """
- type: string
- type: object
  additionalProperties: false
  patternProperties:
    .+:
      - type: string
"""
)

for value in schema["properties"].values():
    match value:
        case {"type": "string_array"}:
            del value["type"]
            value["oneOf"] = string_array
        case {"type": "string_table"}:
            del value["type"]
            value["oneOf"] = string_table
        case {"type": "string_table_array"}:
            del value["type"]
            value["oneOf"] = string_table_array

overrides = yaml.safe_load(
    """
type: array
description: An overrides array
items:
  type: object
  required: ["select"]
  additionalProperties: false
  properties:
    select: {}
"""
)

non_global_options = copy.deepcopy(schema["properties"])
del non_global_options["build"]
del non_global_options["skip"]
del non_global_options["container-engine"]
del non_global_options["test-skip"]

overrides["items"]["properties"]["select"]["oneOf"] = string_array
overrides["items"]["properties"] |= non_global_options.copy()

del overrides["items"]["properties"]["archs"]

not_linux = non_global_options.copy()

del not_linux["environment-pass"]
for key in list(not_linux):
    if "linux-" in key:
        del not_linux[key]


def as_object(d: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": copy.deepcopy(d),
    }


oses = {
    "linux": as_object(non_global_options),
    "windows": as_object(not_linux),
    "macos": as_object(not_linux),
}

oses["linux"]["properties"]["repair-wheel-command"][
    "default"
] = "auditwheel repair -w {dest_dir} {wheel}"
oses["macos"]["properties"]["repair-wheel-command"][
    "default"
] = "delocate-wheel --require-archs {delocate_archs} -w {dest_dir} -v {wheel}"

del oses["linux"]["properties"]["dependency-versions"]

schema["properties"]["overrides"] = overrides
schema["properties"] |= oses

for key, value in schema["properties"].items():
    value["title"] = f'CIBW_{key.replace("-", "_").upper()}'
for key, value in schema["properties"]["linux"]["properties"].items():
    value["title"] = f'CIBW_{key.replace("-", "_").upper()}_LINUX'
for key, value in schema["properties"]["macos"]["properties"].items():
    value["title"] = f'CIBW_{key.replace("-", "_").upper()}_MACOS'
for key, value in schema["properties"]["windows"]["properties"].items():
    value["title"] = f'CIBW_{key.replace("-", "_").upper()}_WINDOWS'

print(json.dumps(schema, indent=2))
