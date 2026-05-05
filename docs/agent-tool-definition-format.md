# Agent tool definition format

This document defines the shared source formats used by `repo-local-tools`. The
formats are intentionally small so one source entry can render repo-local agent
client files for Claude, Codex, Factory Droid, and Cursor.

## Model Context Protocol (MCP) server definitions

MCP server definitions are TOML files under:

```plaintext
$XDG_DATA_HOME/repo-local-tools/mcp-servers/<name>.toml
```

The file name and the `name` field must match.

```toml
name = "echo"
command = "python"
args = ["-m", "example"]

[env]
MODE = "test"
```

Required fields:

- `name`: The MCP server name used in generated client configuration.
- `command`: The executable command used to start the MCP server.

Optional fields:

- `args`: A list of string arguments passed to `command`.
- `env`: A TOML table of string environment variables.

`repo-local-tools load` can create these TOML files from an MCP JSON
configuration file named `mcp.json` or `mcpServers.json`. The JSON input must
use a top-level `mcpServers` object:

```json
{
  "mcpServers": {
    "echo": {
      "command": "python",
      "args": ["-m", "example"],
      "env": {
        "MODE": "test"
      }
    }
  }
}
```

Each server under `mcpServers` is loaded as a separate shared TOML definition.

During installation, the definition is rendered into `.mcp.json`,
`.codex/mcp.json`, `.factory-droid/mcp.json`, and `.cursor/mcp.json` using the
same `mcpServers` object shape:

```json
{
  "mcpServers": {
    "echo": {
      "args": ["-m", "example"],
      "command": "python",
      "env": {
        "MODE": "test"
      }
    }
  }
}
```

## Skill sources

Shared skill repositories live under:

```plaintext
$XDG_DATA_HOME/repo-local-tools/skills/<name>/
```

The directory is copied exactly into each repo-local client skill directory:

```plaintext
.claude/skills/<name>/
.codex/skills/<name>/
.factory-droid/skills/<name>/
.cursor/skills/<name>/
```

Anthropic `.skill` archives are accepted when the command argument ends with
`.skill`. The argument must be an absolute path. The archive must be a zip file
with exactly one top-level directory, and archive entries must not contain
absolute paths or `..` path components.

## Managed-tool manifest

Installed tools are recorded in:

```plaintext
.repo-local-tools/managed-tools.json
```

The manifest is JSON because the tool must write it during install and update
operations without adding a TOML writer dependency. MCP source definitions
remain TOML because Python can read TOML through the standard library `tomllib`.
