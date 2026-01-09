#!/bin/sh
#
# Pre-built copies of the Android Fortran compiler are only available for Linux x86_64,
# so we use Docker to allow it to run on macOS as well.
#
# TODO: only run docker build once, then replace this file with a different script.
set -eu

cwd="$(pwd)"
cd "$(dirname "$(realpath "$0")")"

arch="$(echo "$CIBW_HOST_TRIPLET" | sed 's/-.*//')"
tag="cibw-android-fortran-$arch"

docker build \
    --platform linux/amd64 -f fortran.dockerfile -t "$tag" --build-arg arch="$arch" .

# On macOS, Docker can only mount certain host directories by default.
if [ "$(uname)" = "Darwin" ]; then
    mount_args="-v /Users:/host/Users -v /tmp:/host/tmp"
else
    mount_args="-v /:/host"
fi

# TODO mount /Users, /home, /private and /tmp if they exist, then pass working dir using
# -w. Then no entry point script is needed.
# shellcheck disable=SC2086
docker run --rm --platform linux/amd64 $mount_args "$tag" "$cwd" "$@"
