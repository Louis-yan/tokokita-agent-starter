"""Change only the non-secret switches used in the labs."""
import sys
from pathlib import Path
from run_with_env import read_env

allowed = {'RETRIEVER': {'keyword', 'embedding'}, 'AUTO_RETRIEVE': {'true', 'false'},
           'MAX_TOOL_ROUNDS': {'1', '2', '3', '4', '5', '6'}}
if len(sys.argv) != 3 or sys.argv[1] not in allowed or sys.argv[2] not in allowed[sys.argv[1]]:
    raise SystemExit('Usage: envctl.py RETRIEVER keyword|embedding; AUTO_RETRIEVE true|false; MAX_TOOL_ROUNDS 1..6')
path = Path('/etc/tokokita-agent.env')
values = read_env(path)
values[sys.argv[1]] = sys.argv[2]
path.write_text(''.join(f'{k}={v}\n' for k, v in values.items()), encoding='utf-8')
path.chmod(0o600)
print(f'{sys.argv[1]}={sys.argv[2]}; restart or recreate the service to apply.')
