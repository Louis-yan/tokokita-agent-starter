#!/usr/bin/env bash
# Ubuntu 24.04 ECS only; execute as root after installing requirements.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run in the ECS root Workbench session.' >&2; exit 1; }
[[ -x /opt/tokokita-agent/.venv/bin/uvicorn ]]
[[ -f /etc/tokokita-agent.env ]]
cat > /etc/systemd/system/tokokita-agent.service <<'EOF'
[Unit]
Description=TokoKita cloud training service
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
WorkingDirectory=/opt/tokokita-agent
EnvironmentFile=/etc/tokokita-agent.env
ExecStart=/opt/tokokita-agent/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/nginx/sites-available/tokokita-agent <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
EOF
ln -sfn /etc/nginx/sites-available/tokokita-agent /etc/nginx/sites-enabled/tokokita-agent
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl daemon-reload
systemctl enable --now nginx tokokita-agent
systemctl restart tokokita-agent
systemctl reload nginx
for attempt in $(seq 1 30); do
    if curl -fsS http://127.0.0.1/healthz; then printf '\nCloud service ready.\n'; exit 0; fi
    sleep 2
done
echo 'Startup failed. Read: journalctl -u tokokita-agent -n 30 --no-pager' >&2
exit 1
