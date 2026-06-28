# enoch-mcp

<!-- mcp-name: io.github.alias8818/enoch -->

`enoch-mcp` is a local [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) stdio server for the Enoch FastAPI control-plane API. It lets MCP clients such as Claude Desktop, Cursor, Copilot, and Windsurf inspect and operate a running Enoch instance through tools.

This MCP server is built for the Enoch project: [`alias8818/enoch-agentic-research-system`](https://github.com/alias8818/enoch-agentic-research-system).

This package is a thin HTTP bridge. It does not reimplement Enoch business logic.

## What it does

- Registers MCP tools for Enoch control-plane, Dashboard V1, and core endpoints.
- Sends requests to a configured Enoch API URL.
- Adds `Authorization: Bearer <token>` to every API request.
- Returns Enoch API responses to the MCP client.
- Marks read-only tools with MCP read-only annotations.
- Marks mutating tools as non-read-only and adds approval metadata.
- Keeps safe defaults for dry-run operations.
- Optionally probes configured CPU/GPU workers directly through worker APIs or
  allowlisted SSH diagnostics.

## What it does not do

- It does not run shell commands.
- It does not expose a raw shell tool, even when SSH worker probes are configured.
- It does not read or write local artifact files directly.
- It does not call language models.
- It does not cache, retry, queue, or schedule work.
- It does not add telemetry or analytics.
- It does not bypass Enoch authentication or authorization.

## Requirements

- Python 3.11 or newer
- A running Enoch API, normally at `http://localhost:8787`
- An Enoch API bearer token
- An MCP client that can run local stdio servers

## Installation

Run from PyPI with `uvx`:

```bash
uvx enoch-mcp --api-url http://localhost:8787 --api-token '<token>'
```

Or configure with environment variables:

```bash
export ENOCH_API_URL='http://localhost:8787'
export ENOCH_API_TOKEN='<token>'
uvx enoch-mcp
```

For local development from a checkout:

```bash
git clone https://github.com/alias8818/enoch-mcp.git
cd enoch-mcp
uv sync --dev
uv run enoch-mcp --api-url http://localhost:8787 --api-token '<token>'
```

## Configuration

| Option | Environment variable | Default | Description |
| --- | --- | --- | --- |
| `--api-url` | `ENOCH_API_URL` | `http://localhost:8787` | Base URL for the Enoch API. |
| `--api-token` | `ENOCH_API_TOKEN` | none | Bearer token for the Enoch API. |
| `--worker-probes-json` | `ENOCH_WORKER_PROBES_JSON` | none | Optional JSON map for direct worker diagnostics. |
| `--worker-probes-file` | `ENOCH_WORKER_PROBES_FILE` | none | Optional path to a JSON map for direct worker diagnostics. |

The token is required. If it is missing, tool calls fail before making an HTTP request.

### Optional worker probes

Worker probes are disabled unless `ENOCH_WORKER_PROBES_JSON` or
`ENOCH_WORKER_PROBES_FILE` is configured. This keeps the default package a thin
control-plane bridge. When configured, the MCP exposes named diagnostics for
worker truth: API health, wake-gate dashboard status, active process markers,
bounded log tails, disk space, and expected artifact presence.

Example:

```json
{
  "cpu": {
    "api_url": "http://127.0.0.1:18788",
    "api_token": "worker-api-token",
    "service_name": "enoch-control-plane",
    "project_root": "/srv/enoch/projects"
  },
  "gb10": {
    "api_url": "http://127.0.0.1:18789",
    "api_token": "worker-api-token",
    "ssh_host": "100.92.44.26",
    "ssh_user": "enoch",
    "service_name": "enoch-control-plane",
    "project_root": "/srv/enoch/projects",
    "log_paths": ["/var/log/enoch-control-plane.log"]
  }
}
```

Supported fields per lane:

- `api_url`: worker wake-gate base URL. Used first for `/healthz`,
  `/dashboard/api`, `/dashboard/api/run/{run_id}`, and `/project-status/{project_id}`.
- `api_token`: worker bearer token. Treated as secret.
- `ssh_host`, `ssh_user`, `ssh_port`: optional SSH fallback/debug target.
- `service_name`: systemd unit name for service checks and journal tails.
- `project_root`, `state_dir`: fixed worker roots used for disk and artifact checks.
- `log_paths`: fixed wake-gate log paths that may be tailed.

SSH probes only run fixed diagnostic commands. They do not accept arbitrary shell
input from the MCP client. User-supplied IDs are limited to safe run/project
identifier characters, log output is bounded, SSH uses batch mode and no stdin,
and the recommended deployment is a read-only worker user or forced-command
policy.

## MCP client setup

### Claude Desktop

Add an entry like this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "enoch": {
      "command": "uvx",
      "args": ["enoch-mcp"],
      "env": {
        "ENOCH_API_URL": "http://localhost:8787",
        "ENOCH_API_TOKEN": "replace-with-token"
      }
    }
  }
}
```

For local development, point Claude Desktop at the checkout:

```json
{
  "mcpServers": {
    "enoch": {
      "command": "uv",
      "args": ["--directory", "/path/to/enoch-mcp", "run", "enoch-mcp"],
      "env": {
        "ENOCH_API_URL": "http://localhost:8787",
        "ENOCH_API_TOKEN": "replace-with-token"
      }
    }
  }
}
```

### Cursor

Add an MCP server entry that runs the same stdio command:

```json
{
  "mcpServers": {
    "enoch": {
      "command": "uvx",
      "args": ["enoch-mcp"],
      "env": {
        "ENOCH_API_URL": "http://localhost:8787",
        "ENOCH_API_TOKEN": "replace-with-token"
      }
    }
  }
}
```

Use the equivalent MCP server settings for other clients that support local stdio MCP servers.

### Codex on the Enoch workstation

For this workstation, use the repo wrapper so Codex does not store the Enoch
bearer token directly. The wrapper starts or reuses an SSH tunnel to
`enoch-core.exe.xyz`, reads the control-plane token on the remote host, and then
runs this checkout over stdio:

```toml
[mcp_servers.enoch]
command = "/home/jeremy/Desktop/projects/enoch-release/enoch-mcp/scripts/run_codex_mcp.sh"
startup_timeout_sec = 60.0
```

The wrapper honors these optional environment overrides:

- `ENOCH_MCP_SSH_HOST` default `enoch-core.exe.xyz`
- `ENOCH_MCP_LOCAL_PORT` default `18787`
- `ENOCH_MCP_REMOTE_PORT` default `8787`
- `ENOCH_MCP_ENABLE_WORKER_PROBES` default `1`
- `ENOCH_MCP_WORKER_BASE_PORT` default `18788`

When worker probes are enabled, the wrapper reads configured Enoch
`worker_targets` on `enoch-core`, opens local SSH tunnels for each worker API,
and exports `ENOCH_WORKER_PROBES_JSON` for this MCP process. The Codex config
still does not store the control-plane or worker bearer tokens.

## Tools

### Read-only tools

These tools are registered with `readOnlyHint=true`.

| Tool | Endpoint | Purpose |
| --- | --- | --- |
| `enoch_status` | `GET /control/api/status` | Full control-plane status, dispatch safety, counts, warnings, and conflicts. |
| `enoch_queue_health` | `GET /control/api/queue-health` | Queue health, worker freshness, alert findings, and recent events. |
| `enoch_overview` | `GET /control/api/v1/overview` | Bounded operator overview: counts, active work, paper pipeline, top actions, and recent events. |
| `enoch_automation_readiness` | `GET /control/api/v1/automation-readiness` | Canonical long-haul readiness check for “can I leave this running?” |
| `enoch_research_quality` | `GET /control/api/v1/research-quality` | Latest research quality readiness report. |
| `enoch_intake_status` | `GET /control/api/intake/ideas` | Current control-plane idea intake status. |
| `enoch_lanes` | `GET /control/api/v1/lanes` | Bounded worker-lane state and lane-aware next candidate. |
| `enoch_probe_worker` | worker API / allowlisted SSH | Optional direct worker truth: health, wake-gate status, active process markers, matching run presence, disk, and telemetry. |
| `enoch_worker_logs` | allowlisted SSH only | Optional bounded tail for `service`, `wake_gate`, or `active_run` logs. |
| `enoch_worker_artifacts` | worker API / allowlisted SSH | Optional expected artifact presence check for one project/run. |
| `enoch_queue_list` | `GET /control/api/queues/{status}` | Queue rows for `active`, `queued`, `blocked`, or `paused`. |
| `enoch_v1_queue` | `GET /control/api/v1/queue` | Cursor-paginated Dashboard V1 queue rows. |
| `enoch_projects` | `GET /control/api/v1/projects` | Cursor-paginated project list. |
| `enoch_project_detail` | `GET /control/api/v1/projects/{project_id}` | Project detail with related rows and events. |
| `enoch_runs` | `GET /control/api/v1/runs` | Cursor-paginated run list. |
| `enoch_run_detail` | `GET /control/api/v1/runs/{run_id}` | Run detail with related rows and events. |
| `enoch_papers_list` | `GET /control/api/papers` | Paginated paper listing. |
| `enoch_paper_detail` | `GET /control/api/papers/{paper_id}` | Paper detail with related project, run, events, and warnings. |
| `enoch_paper_artifact` | `GET /control/api/papers/{paper_id}/artifact/{field}` | Artifact content served by the Enoch API. |
| `enoch_reviews_list` | `GET /control/api/paper-reviews` | Publication automation/detail queue; not a normal human editorial review gate. |
| `enoch_review_next` | `GET /control/api/paper-reviews/next` | Next publication automation item. |
| `enoch_events` | `GET /control/api/v1/events` | Cursor-paginated Dashboard V1 event log query. |
| `enoch_core_health` | `GET /enoch-core/health` | Enoch core health and mode. |
| `enoch_core_queue_projection` | `GET /enoch-core/projections/queue` | Core queue projection. |
| `enoch_core_paper_candidates` | `GET /enoch-core/candidates/paper-draft` or `/paper-polish` | Next draft or polish candidate. |

### Mutating tools

These tools are registered as non-read-only and include `userApproval` metadata. MCP annotations and metadata are hints to clients; confirmation behavior depends on the MCP client.

| Tool | Endpoint | Safety behavior |
| --- | --- | --- |
| `enoch_dispatch` | `POST /control/dispatch-next` | Defaults to `dry_run=true`. |
| `enoch_dispatch_one` | `POST /control/dispatch-one` | Explicit single-project dispatch; defaults to `dry_run=true`. |
| `enoch_queue_alert_check` | `POST /control/api/alerts/queue-check` | Queue alert/stale-active check; defaults to `dry_run=true`. |
| `enoch_reconcile_stale_lane` | `POST /control/api/alerts/queue-check` | Focused stale-lane explanation/reconcile wrapper; defaults to `dry_run=true`. |
| `enoch_research_run_cycle` | `POST /control/api/research/run-cycle` | One bounded research autopilot cycle; defaults to `dry_run=true`. |
| `enoch_launch_followup` | `POST /control/api/v1/followups/launch-next` | Launch next bounded follow-up candidate; defaults to `dry_run=true`. |
| `enoch_pause` | `POST /control/pause` | Requires an explicit reason. |
| `enoch_resume` | `POST /control/resume` | Requires an explicit tool call. |
| `enoch_preflight` | `POST /control/worker/preflight` | Checks worker health; does not dispatch by itself. |
| `enoch_intake_notion` | `POST /control/intake/notion-ideas` | Legacy compatibility path; defaults to `dry_run=true`. |
| `enoch_intake_ideas` | `POST /control/intake/ideas` | Current control-plane idea intake; defaults to `dry_run=true`. |
| `enoch_review_claim` | `POST /control/api/paper-reviews/{paper_id}/claim` | Claims a review. |
| `enoch_review_checklist` | `POST /control/api/paper-reviews/{paper_id}/checklist/{item_id}` | Updates one checklist item. |
| `enoch_review_status` | `POST /control/api/paper-reviews/{paper_id}/status` | Updates review status. |
| `enoch_draft_paper` | `POST /control/papers/draft-next` | Checks or requests next paper draft; defaults to `dry_run=true`. |
| `enoch_rewrite_draft` | `POST /control/api/paper-reviews/{paper_id}/rewrite-draft` | Requests draft rewrite. |

## Live smoke test

A live smoke script is included for checking a running Enoch instance before publishing or changing client configuration:

```bash
ENOCH_API_TOKEN='<token>' uv run python scripts/live_smoke.py --api-url http://localhost:8787
```

The script:

- verifies that the expected tools are registered;
- verifies approval metadata on mutating tools;
- calls read-only tools against the configured Enoch API;
- reads one paper detail and one artifact when available;
- calls direct worker probes only when worker probe config is present;
- calls only safe mutating paths by default: dispatch dry-runs, queue alert dry-run,
  stale-lane reconcile dry-run, research cycle dry-run, follow-up dry-run,
  worker preflight, idea intake dry-run, legacy Notion intake dry-run when
  enabled, and paper draft dry-run.

It does not print the bearer token.

## Development

```bash
uv sync --dev
uv run ruff check .
uv run pytest
uv build
```

Run the MCP server from a checkout:

```bash
uv run enoch-mcp --api-url http://localhost:8787 --api-token '<token>'
```

The server uses stdio transport, so it waits for MCP protocol messages on standard input.

## Error handling

- HTTP 4xx/5xx responses from Enoch are returned as MCP tool errors that include the status code and response body.
- Network failures are returned as transport errors.
- Missing bearer tokens are reported before a request is sent.

## Security notes

- Treat `ENOCH_API_TOKEN` like any other credential.
- Treat `ENOCH_WORKER_PROBES_JSON` like a credential when it includes worker API tokens.
- Prefer environment variables or your MCP client's secret storage over hard-coded tokens.
- Do not expose an Enoch API endpoint to networks or users that should not operate the control plane.
- Mutating tool approval prompts are MCP-client dependent; review your client behavior before enabling mutating workflows.
- Worker SSH diagnostics are named probes with fixed commands, not a general
  remote shell. Use a dedicated read-only/forced-command SSH identity when
  possible.

## License

MIT
