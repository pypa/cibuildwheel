#!/usr/bin/env bash
set -o errexit
set -o xtrace

if [ "$(uname -s)" == "Darwin" ]; then
  sudo softwareupdate --install-rosetta --agree-to-license
fi

$PYTHON --version
$PYTHON -m venv venv
venv/bin/python -m pip install -U pip
venv/bin/python -m pip install -e ".[dev]"
venv/bin/python -m pip freeze
venv/bin/python --version
