#!/usr/bin/env bash
set -euo pipefail

HOST="${ENOCH_MCP_SSH_HOST:-control-host}"
LOCAL_PORT="${ENOCH_MCP_LOCAL_PORT:-18787}"
REMOTE_PORT="${ENOCH_MCP_REMOTE_PORT:-8787}"
WORKER_BASE_PORT="${ENOCH_MCP_WORKER_BASE_PORT:-18788}"
REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if ! (echo >"/dev/tcp/127.0.0.1/${LOCAL_PORT}") >/dev/null 2>&1; then
  ssh -n -o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=15 -f -N \
    -L "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" "${HOST}"
fi

export ENOCH_API_URL="http://127.0.0.1:${LOCAL_PORT}"
export ENOCH_API_TOKEN="$(
  ssh -n -o BatchMode=yes -o ConnectTimeout=8 "${HOST}" 'sudo -n python3 - <<'"'"'PY'"'"'
import json
from pathlib import Path

cfg = json.loads(Path("/etc/enoch-control-plane/config.json").read_text())
token = cfg.get("control_api_bearer_token") or cfg.get("omx_inbound_bearer_token")
if not token:
    raise SystemExit("missing Enoch control API token")
print(token)
PY'
)"

if [[ "${ENOCH_MCP_ENABLE_WORKER_PROBES:-1}" == "1" && -z "${ENOCH_WORKER_PROBES_JSON:-}" ]]; then
  WORKER_PROBE_BUNDLE="$(
    ssh -n -o BatchMode=yes -o ConnectTimeout=8 "${HOST}" "sudo -n ENOCH_MCP_WORKER_BASE_PORT='${WORKER_BASE_PORT}' python3 - <<'PY'
import json
import os
from pathlib import Path
from urllib.parse import urlparse

cfg = json.loads(Path('/etc/enoch-control-plane/config.json').read_text())
base_port = int(os.environ.get('ENOCH_MCP_WORKER_BASE_PORT') or 18788)
targets = cfg.get('worker_targets') or {}
sync_ssh = str(cfg.get('paper_evidence_sync_ssh_host') or '').strip()
probes = {}
tunnels = []
for offset, (name, target) in enumerate(sorted(targets.items())):
    if not isinstance(target, dict):
        continue
    wake_url = str(target.get('wake_gate_url') or '').strip()
    parsed = urlparse(wake_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        continue
    remote_port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    local_port = base_port + offset
    role = str(target.get('role') or name).lower()
    lane = 'gb10' if role == 'gpu_worker' or name == 'gb10' else 'cpu'
    probes[lane] = {
        'lane': lane,
        'api_url': f'{parsed.scheme}://127.0.0.1:{local_port}',
        'api_token': target.get('bearer_token') or cfg.get('worker_wake_gate_bearer_token'),
        'service_name': 'enoch-control-plane',
    }
    if lane == 'gb10' and sync_ssh:
        if '@' in sync_ssh:
            user, host = sync_ssh.split('@', 1)
            probes[lane]['ssh_user'] = user
            probes[lane]['ssh_host'] = host
        else:
            probes[lane]['ssh_host'] = sync_ssh
    tunnels.append({'local_port': local_port, 'remote_host': parsed.hostname, 'remote_port': remote_port})
print(json.dumps({'probes': probes, 'tunnels': tunnels}, separators=(',', ':')))
PY"
  )"
  while read -r worker_local_port worker_remote_host worker_remote_port; do
    if [[ -z "${worker_local_port}" ]]; then
      continue
    fi
    if ! (echo >"/dev/tcp/127.0.0.1/${worker_local_port}") >/dev/null 2>&1; then
      ssh -n -o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=15 -f -N \
        -L "${worker_local_port}:${worker_remote_host}:${worker_remote_port}" "${HOST}"
    fi
  done < <(
    python3 -c 'import json, sys
data = json.load(sys.stdin)
for item in data.get("tunnels", []):
    print(item.get("local_port", ""), item.get("remote_host", ""), item.get("remote_port", ""))' \
      <<<"${WORKER_PROBE_BUNDLE}"
  )
  export ENOCH_WORKER_PROBES_JSON="$(
    python3 -c 'import json, sys
print(json.dumps(json.load(sys.stdin).get("probes", {}), separators=(",", ":")))' \
      <<<"${WORKER_PROBE_BUNDLE}"
  )"
fi

if [[ -x "${REPO_DIR}/.venv/bin/enoch-mcp" ]]; then
  exec "${REPO_DIR}/.venv/bin/enoch-mcp"
fi

exec uv --directory "${REPO_DIR}" run --no-sync enoch-mcp
