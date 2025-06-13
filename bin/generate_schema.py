#!/usr/bin/env python

# /// script
# dependencies = ["pyyaml"]
# ///

import argparse
import copy
import functools
import json
import sys
from typing import Any

import yaml

make_parser = functools.partial(argparse.ArgumentParser, allow_abbrev=False)
if sys.version_info >= (3, 14):
    make_parser = functools.partial(make_parser, color=True, suggest_on_error=True)
parser = make_parser()
parser.add_argument("--schemastore", action="store_true", help="Generate schema_store version")
args = parser.parse_args()

starter = """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/pypa/cibuildwheel/blob/main/cibuildwheel/resources/cibuildwheel.schema.json
$defs:
  inherit:
    enum:
      - none
      - prepend
      - append
    default: none
    description: How to inherit the parent's value.
  enable:
    enum:
      - cpython-experimental-riscv64
      - cpython-freethreading
      - cpython-prerelease
      - graalpy
      - pyodide-prerelease
      - pypy
      - pypy-eol
  description: A Python version or flavor to enable.
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
    description: Set the tool to use to build, either "pip" (default for now), "build", or "build[uv]"
    oneOf:
      - enum: [pip, build, "build[uv]", default]
      - type: string
        pattern: '^pip; ?args:'
      - type: string
        pattern: '^build; ?args:'
      - type: string
        pattern: '^build\\[uv\\]; ?args:'
      - type: object
        additionalProperties: false
        required: [name]
        properties:
          name:
            enum: [pip, build, "build[uv]"]
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
        pattern: '^docker; ?(create_args|disable_host_mount):'
      - type: string
        pattern: '^podman; ?(create_args|disable_host_mount):'
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
          disable-host-mount:
            type: boolean
  dependency-versions:
    default: pinned
    description: Specify how cibuildwheel controls the versions of the tools it uses
    oneOf:
      - enum: [pinned, latest]
      - type: string
        description: Path to a file containing dependency versions, or inline package specifications, starting with "packages:"
        not:
          enum: [pinned, latest]
      - type: object
        additionalProperties: false
        properties:
          file:
            type: string
      - type: object
        additionalProperties: false
        properties:
          packages:
            type: array
            items:
              type: string
  enable:
    description: Enable or disable certain builds.
    oneOf:
      - $ref: "#/$defs/enable"
      - type: array
        items:
          $ref: "#/$defs/enable"
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
  manylinux-armv7l-image:
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
  manylinux-riscv64-image:
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
  musllinux-armv7l-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-i686-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-ppc64le-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-riscv64-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-s390x-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  musllinux-x86_64-image:
    type: string
    description: Specify alternative manylinux / musllinux container images
  xbuild-tools:
    description: Binaries on the path that should be included in an isolated cross-build environment
    type: string_array
  pyodide-version:
    type: string
    description: Specify the version of Pyodide to use
  repair-wheel-command:
    description: Execute a shell command to repair each built wheel.
    type: string_array
  skip:
    description: Choose the Python versions to skip.
    type: string_array
  test-command:
    description: Execute a shell command to test each built wheel.
    type: string_array
  test-extras:
    description: Install your wheel for testing using `extras_require`
    type: string_array
  test-sources:
    description: Test files that are required by the test environment
    type: string_array
  test-groups:
    description: Install extra groups when testing
    type: string_array
  test-requires:
    description: Install Python dependencies before running the tests
    type: string_array
  test-skip:
    description: Skip running tests on some builds.
    type: string_array
  test-environment:
    description: Set environment variables for the test environment
    type: string_table
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
      type: string
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
  minProperties: 2
  additionalProperties: false
  properties:
    select: {}
    inherit:
      type: object
      additionalProperties: false
      properties:
        before-all: {"$ref": "#/$defs/inherit"}
        before-build: {"$ref": "#/$defs/inherit"}
        xbuild-tools: {"$ref": "#/$defs/inherit"}
        before-test: {"$ref": "#/$defs/inherit"}
        config-settings: {"$ref": "#/$defs/inherit"}
        container-engine: {"$ref": "#/$defs/inherit"}
        environment: {"$ref": "#/$defs/inherit"}
        environment-pass: {"$ref": "#/$defs/inherit"}
        repair-wheel-command: {"$ref": "#/$defs/inherit"}
        test-command: {"$ref": "#/$defs/inherit"}
        test-extras: {"$ref": "#/$defs/inherit"}
        test-sources: {"$ref": "#/$defs/inherit"}
        test-requires: {"$ref": "#/$defs/inherit"}
        test-environment: {"$ref": "#/$defs/inherit"}
"""
)

for key, value in schema["properties"].items():
    value["title"] = f"CIBW_{key.replace('-', '_').upper()}"

non_global_options = {k: {"$ref": f"#/properties/{k}"} for k in schema["properties"]}
del non_global_options["build"]
del non_global_options["skip"]
del non_global_options["test-skip"]
del non_global_options["enable"]

overrides["items"]["properties"]["select"]["oneOf"] = string_array
overrides["items"]["properties"] |= non_global_options.copy()

del overrides["items"]["properties"]["archs"]

not_linux = non_global_options.copy()

del not_linux["environment-pass"]
del not_linux["container-engine"]
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
    "pyodide": as_object(not_linux),
    "ios": as_object(not_linux),
}

oses["linux"]["properties"]["repair-wheel-command"] = {
    **schema["properties"]["repair-wheel-command"],
    "default": "auditwheel repair -w {dest_dir} {wheel}",
}
oses["macos"]["properties"]["repair-wheel-command"] = {
    **schema["properties"]["repair-wheel-command"],
    "default": "delocate-wheel --require-archs {delocate_archs} -w {dest_dir} -v {wheel}",
}

del oses["linux"]["properties"]["dependency-versions"]

schema["properties"]["overrides"] = overrides
schema["properties"] |= oses

if args.schemastore:
    schema["$id"] = "https://json.schemastore.org/partial-cibuildwheel.json"
    schema["description"] = (
        "cibuildwheel's toml file, generated with ./bin/generate_schema.py --schemastore from cibuildwheel."
    )

print(json.dumps(schema, indent=2))
