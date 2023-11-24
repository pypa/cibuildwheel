#!/usr/bin/env bash
set -o errexit
set -o xtrace

python3 --version
python3 -m pip --version
python3 -m venv venv
venv/bin/python -m pip install -e ".[dev]"
venv/bin/python -m pip freeze
venv/bin/python --version
