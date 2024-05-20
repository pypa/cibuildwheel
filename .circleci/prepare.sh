#!/usr/bin/env bash
set -o errexit
set -o xtrace

$PYTHON --version
$PYTHON -m pip --version
$PYTHON -m virtualenv --version
$PYTHON -m virtualenv --no-setuptools --no-wheel -p "$PYTHON" venv
venv/bin/python -m pip install -U pip
venv/bin/python -m pip install -e ".[dev]"
venv/bin/python -m pip freeze
venv/bin/python --version
