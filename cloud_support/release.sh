#!/usr/bin/env bash
# Build an immutable tag, snapshot its configuration, then deploy it.
set -euo pipefail
cd /opt/tokokita-agent
tag=${1:?Usage: bash cloud_support/release.sh v1}
[[ "$tag" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]] || exit 2
if docker image inspect "tokokita-agent:$tag" >/dev/null 2>&1; then
    echo "Tag $tag already exists; choose a new tag. To restore it, use rollback.sh $tag." >&2
    exit 2
fi
grep -q '^DATABASE_URL=mysql+pymysql://' /etc/tokokita-agent.env
mkdir -p /etc/tokokita-releases
chmod 700 /etc/tokokita-releases
[[ ! -e "/etc/tokokita-releases/$tag.env" ]] || { echo 'Configuration snapshot already exists.' >&2; exit 2; }
docker build -t "tokokita-agent:$tag" .
install -m 600 /etc/tokokita-agent.env "/etc/tokokita-releases/$tag.env"
bash cloud_support/run_image.sh "$tag" "/etc/tokokita-releases/$tag.env"
