#!/bin/bash
__doc__="
Based on code in: https://github.com/redhat-actions/podman-login/blob/main/.github/install_latest_podman.sh
"
# https://podman.io/getting-started/installation
# shellcheck source=/dev/null
. /etc/os-release
echo "deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/ /" | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list
curl -sSfL "https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/Release.key" | sudo apt-key add -
sudo apt-get update
sudo apt-get -y upgrade
sudo apt-get -y install podman
