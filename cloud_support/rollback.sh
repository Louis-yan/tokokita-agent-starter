#!/usr/bin/env bash
# No docker build: restore the saved image AND the corresponding configuration.
set -euo pipefail
cd /opt/tokokita-agent
tag=${1:?Usage: bash cloud_support/rollback.sh v2}
[[ "$tag" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]] || exit 2
bash cloud_support/run_image.sh "$tag" "/etc/tokokita-releases/$tag.env"
printf 'Rolled back to tokokita-agent:%s\n' "$tag"
