# enoch-mcp

<!-- mcp-name: io.github.alias8818/enoch -->

`enoch-mcp` is a local [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) stdio server for the Enoch FastAPI control-plane API. It lets MCP clients such as Claude Desktop, Cursor, Copilot, and Windsurf inspect and operate a running Enoch instance through tools.

This MCP server is built for the Enoch project: [`alias8818/enoch-agentic-research-system`](https://github.com/alias8818/enoch-agentic-research-system).

This package is a thin HTTP bridge. It does not reimplement Enoch business logic.

## What it does

- Registers MCP tools for Enoch control-plane and core endpoints.
- Sends requests to a configured Enoch API URL.
- Adds `Authorization: Bearer <token>` to every API request.
- Returns Enoch API responses to the MCP client.
- Marks read-only tools with MCP read-only annotations.
- Marks mutating tools as non-read-only and adds approval metadata.
- Keeps safe defaults for dry-run operations.

## What it does not do

- It does not run shell commands.
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

The token is required. If it is missing, tool calls fail before making an HTTP request.

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

## Tools

### Read-only tools

These tools are registered with `readOnlyHint=true`.

| Tool | Endpoint | Purpose |
| --- | --- | --- |
| `enoch_status` | `GET /control/api/status` | Full control-plane status, dispatch safety, counts, warnings, and conflicts. |
| `enoch_queue_health` | `GET /control/api/queue-health` | Queue health, worker freshness, alert findings, and recent events. |
| `enoch_queue_list` | `GET /control/api/queues/{status}` | Queue rows for `active`, `queued`, `blocked`, or `paused`. |
| `enoch_papers_list` | `GET /control/api/papers` | Paginated paper listing. |
| `enoch_paper_detail` | `GET /control/api/papers/{paper_id}` | Paper detail with related project, run, events, and warnings. |
| `enoch_paper_artifact` | `GET /control/api/papers/{paper_id}/artifact/{field}` | Artifact content served by the Enoch API. |
| `enoch_reviews_list` | `GET /control/api/paper-reviews` | Publication review queue. |
| `enoch_review_next` | `GET /control/api/paper-reviews/next` | Next review candidate. |
| `enoch_events` | `GET /control/api/events` | Event log query. |
| `enoch_core_health` | `GET /enoch-core/health` | Enoch core health and mode. |
| `enoch_core_queue_projection` | `GET /enoch-core/projections/queue` | Core queue projection. |
| `enoch_core_paper_candidates` | `GET /enoch-core/candidates/paper-draft` or `/paper-polish` | Next draft or polish candidate. |

### Mutating tools

These tools are registered as non-read-only and include `userApproval` metadata. MCP annotations and metadata are hints to clients; confirmation behavior depends on the MCP client.

| Tool | Endpoint | Safety behavior |
| --- | --- | --- |
| `enoch_dispatch` | `POST /control/dispatch-next` | Defaults to `dry_run=true`. |
| `enoch_pause` | `POST /control/pause` | Requires an explicit reason. |
| `enoch_resume` | `POST /control/resume` | Requires an explicit tool call. |
| `enoch_preflight` | `POST /control/worker/preflight` | Checks worker health; does not dispatch by itself. |
| `enoch_intake_notion` | `POST /control/intake/notion-ideas` | Defaults to `dry_run=true`. |
| `enoch_review_claim` | `POST /control/api/paper-reviews/{paper_id}/claim` | Claims a review. |
| `enoch_review_checklist` | `POST /control/api/paper-reviews/{paper_id}/checklist/{item_id}` | Updates one checklist item. |
| `enoch_review_status` | `POST /control/api/paper-reviews/{paper_id}/status` | Updates review status. |
| `enoch_draft_paper` | `POST /control/papers/draft-next` | Requests drafting for the next paper. |
| `enoch_rewrite_draft` | `POST /control/api/paper-reviews/{paper_id}/rewrite-draft` | Requests draft rewrite. |

## Live smoke test

A live smoke script is included for checking a running Enoch instance before publishing or changing client configuration:

```bash
ENOCH_API_TOKEN='<token>' uv run python scripts/live_smoke.py --api-url http://localhost:8787
```

The script:

- verifies that 22 tools are registered;
- verifies approval metadata on mutating tools;
- calls read-only tools against the configured Enoch API;
- reads one paper detail and one artifact when available;
- calls only safe mutating paths: dispatch dry-run, worker preflight, and Notion intake dry-run.

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
- Prefer environment variables or your MCP client's secret storage over hard-coded tokens.
- Do not expose an Enoch API endpoint to networks or users that should not operate the control plane.
- Mutating tool approval prompts are MCP-client dependent; review your client behavior before enabling mutating workflows.

## License

MIT
