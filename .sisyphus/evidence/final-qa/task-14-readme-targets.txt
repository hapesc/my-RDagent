Command:
python - <<'PY'
from pathlib import Path
targets = ['agentrd_cli.py', 'cli.py', 'app/api_main.py', 'app/startup.py', 'ui/trace_ui.py']
for t in targets:
    print(t, Path(t).exists())
PY

Status: PASS

Output:
agentrd_cli.py True
cli.py True
app/api_main.py True
app/startup.py True
ui/trace_ui.py True
