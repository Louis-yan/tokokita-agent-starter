"""Run a command with the ECS env file. Values are data, never shell code."""
import os
import sys
from pathlib import Path


def read_env(path=Path('/etc/tokokita-agent.env')):
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        name, value = line.split('=', 1)
        result[name.strip()] = value
    return result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python cloud_support/run_with_env.py COMMAND [ARGS...]')
    os.execvpe(sys.argv[1], sys.argv[1:], {**os.environ, **read_env()})
