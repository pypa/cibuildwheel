#!/usr/bin/env bash
set -o errexit
set -o xtrace

if [ "$(uname -s)" == "Darwin" ]; then
  sudo softwareupdate --install-rosetta --agree-to-license
else
  docker run --rm --privileged docker.io/tonistiigi/binfmt:latest --install all
fi

$PYTHON --version
$PYTHON -m venv venv
venv/bin/python -m pip install -U pip dependency-groups
venv/bin/python -m dependency_groups test | xargs venv/bin/python -m pip install -e.
venv/bin/python -m pip freeze
venv/bin/python --version
