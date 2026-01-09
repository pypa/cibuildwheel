#!/bin/sh

set -eu

cwd="${1:?}"
shift

cd "/host$cwd"
exec /root/*-linux-android-4.9/bin/*-linux-android-gfortran "$@"
