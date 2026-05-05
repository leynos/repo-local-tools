# repo-local-tools

*Repository-local setup for agent tools, without the copy-paste ceremony.*

`repo-local-tools` installs shared Model Context Protocol (MCP) server
configuration and reusable agent skills into the current Git repository. It
keeps the source definitions in one XDG data directory, renders repo-local
files for supported agent clients, and commits one managed tool at a time.

______________________________________________________________________

## Why repo-local-tools?

- **One source, many agents**: A single MCP or skill definition can be rendered
  for Claude, Codex, Factory Droid, and Cursor.
- **Repository-local by default**: Generated files live in the target project,
  not in hidden global client state.
- **Safe Git workflow**: Managed files are tracked in a manifest, ignored by
  default, and committed explicitly when a maintainer asks for that tool.

______________________________________________________________________

## Quick start

### Installation

From a checkout of this repository:

```bash
uv sync --group dev
```

### Hello world

Create a tiny MCP configuration in a project:

```bash
mkdir -p /path/to/project
cat > /path/to/project/mcp.json <<'EOF_MCP'
{
  "mcpServers": {
    "hello": {
      "command": "python",
      "args": ["-m", "http.server", "9000"]
    }
  }
}
EOF_MCP
```

Load it into the shared registry, then install it into the repository-local
agent client files:

```bash
cd /path/to/project
uv run --project /path/to/repo-local-tools repo-local-tools load
uv run --project /path/to/repo-local-tools repo-local-tools mcp install hello
```

The project now has repo-local MCP configuration for the supported agent
clients, plus a managed-tool manifest that records where the generated files
came from.

______________________________________________________________________

## Features

- Install, update, and commit shared MCP server definitions.
- Install, update, and commit shared skill directories.
- Install absolute Anthropic `.skill` archives safely.
- Load local `SKILL.md`, `.skill`, `mcp.json`, and `mcpServers.json` sources
  into the shared registry.
- Render repo-local files for Claude, Codex, Factory Droid, and Cursor.
- Add generated client paths to `.gitignore` automatically.
- Refuse scoped commits when unrelated repository changes are present.
- Provide `pytest` unit coverage and `pytest-bdd` behavioural coverage.

______________________________________________________________________

## Learn more

- [Users' guide](docs/users-guide.md) — complete usage documentation.
- [Definition format](docs/agent-tool-definition-format.md) — source syntax for
  MCP servers and skills.
- [ExecPlan](docs/execplans/tool-implementation.md) — implementation plan,
  decisions, validation evidence, and retrospective notes.

______________________________________________________________________

## Licence

ISC — see [LICENSE](LICENSE) for details.

______________________________________________________________________

## Contributing

Contributions are welcome. Please see [AGENTS.md](AGENTS.md) for repository
workflow, quality gate, and commit guidance.
