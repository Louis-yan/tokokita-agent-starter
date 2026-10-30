# Source this file inside the ECS Workbench terminal.
cd /opt/tokokita-agent || return 1
source .venv/bin/activate
cloudrun() {
    /opt/tokokita-agent/.venv/bin/python /opt/tokokita-agent/cloud_support/run_with_env.py "$@"
}
printf 'ECS project: %s\n' "$PWD"
