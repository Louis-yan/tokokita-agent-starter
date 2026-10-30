#!/usr/bin/env bash
# Recreate from an existing image and a protected configuration snapshot.
set -euo pipefail
tag=${1:?Usage: run_image.sh TAG ENV_FILE}
env_file=${2:?Missing protected env snapshot}
[[ "$tag" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]] || exit 2
docker image inspect "tokokita-agent:$tag" >/dev/null
[[ -f "$env_file" ]]
systemctl disable --now tokokita-agent
docker rm -f tokokita-agent >/dev/null 2>&1 || true
docker run -d --name tokokita-agent --restart unless-stopped \
  --env-file "$env_file" -e DATA_DIR=/srv/agent/data \
  -p 127.0.0.1:8000:8000 \
  --log-opt max-size=10m --log-opt max-file=3 "tokokita-agent:$tag"
for attempt in $(seq 1 60); do
    if curl -fsS http://127.0.0.1/healthz; then printf '\nRunning tokokita-agent:%s\n' "$tag"; exit 0; fi
    sleep 2
done
echo 'Health check failed; inspect docker logs and use rollback.sh with the last verified tag.' >&2
exit 1
