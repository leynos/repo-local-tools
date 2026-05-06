# repo-local-tools users' guide

`repo-local-tools` manages repository-local agent tool configuration. It reads
shared source definitions from the XDG (Cross-Desktop Group) data directory at
`$XDG_DATA_HOME/repo-local-tools`, installs the requested Model Context
Protocol (MCP) servers and skills into the current Git repository, records
ownership metadata, and lets maintainers update or commit managed files
explicitly.

The users' guide is written for maintainers who already have a Git repository
and want repeatable local configuration for agent clients such as Claude,
Codex, Factory Droid, and Cursor.

## External documentation

`repo-local-tools` does not replace the upstream documentation for MCP servers
or agent skills. It provides a repo-local installation workflow around those
formats.

- Model Context Protocol documentation[^1] explains MCP, its architecture,
  servers, clients, SDKs, and examples.
- Model Context Protocol specification repository[^2] contains the protocol
  specification, schema, and official documentation source.
- Anthropic Agent Skills documentation[^3] explains skill structure,
  progressive disclosure, supported Claude surfaces, runtime constraints, and
  examples.

## Command overview

Commands are run from the target repository root. The command treats the
current working directory as the repository that receives generated files.

```bash
repo-local-tools --help
repo-local-tools load [path]
repo-local-tools mcp --help
repo-local-tools skill --help
```

The command groups are:

```plaintext
repo-local-tools mcp install <name>
repo-local-tools mcp update [name]
repo-local-tools mcp commit <name>
repo-local-tools skill install <name-or-archive>
repo-local-tools skill update [name]
repo-local-tools skill commit <name>
```

The `load` command copies local skill sources and MCP JSON configurations into
the shared XDG registry. The `install` commands render files into the current
repository. The `update` commands refresh installed items from their original
source definitions. The `commit` commands create a Git commit for one managed
item and refuse to proceed when unrelated changes are present.

## Source registry layout

The tool reads shared source data from the same XDG data directory. If
`$XDG_DATA_HOME` is unset, the default root is:

```plaintext
~/.local/share/repo-local-tools
```

MCP server definitions live under:

```plaintext
$XDG_DATA_HOME/repo-local-tools/mcp-servers/<name>.toml
```

Skill repositories live under:

```plaintext
$XDG_DATA_HOME/repo-local-tools/skills/<name>/
```

Anthropic `.skill` archives may also be installed directly. Archive paths must
be absolute and must point to a zip file containing exactly one top-level skill
directory.

`repo-local-tools load` writes to the same shared source registry. It is useful
when a project already contains a `SKILL.md`, `.skill` bundle, `mcp.json`, or
`mcpServers.json` file and the maintainer wants to make those tools available
for later `mcp install` or `skill install` commands.

## Loading local sources

Run `load` without a path to scan the current directory:

```bash
repo-local-tools load
```

The omitted-path scan loads every supported source it finds:

- If `SKILL.md` exists in the current directory, the current directory is
  loaded as a skill. If the file has a frontmatter `name`, that name is used;
  otherwise, the current directory name is used. The fallback names `skill` and
  `src` are rejected because they are too ambiguous.
- If `mcp.json` or `mcpServers.json` exists, each server under its top-level
  `mcpServers` object is loaded into the shared MCP registry.
- Each `.skill` bundle in the current directory is loaded individually.
- If a `skill` or `skills` subdirectory exists, each direct subdirectory under
  it is loaded as an individual skill directory.

Run `load` with a path to load one source or scan another directory:

```bash
repo-local-tools load path/to/SKILL.md
repo-local-tools load path/to/reviewer.skill
repo-local-tools load path/to/mcp.json
repo-local-tools load path/to/project
```

Path handling follows the same rules:

- `SKILL.md` loads its enclosing directory as one skill.
- `.skill` loads that archive as one skill.
- `mcp.json` or `mcpServers.json` loads every server from its `mcpServers`
  object.
- Any other directory is scanned as though `load` had been run from that
  directory.

MCP JSON input follows the interoperable MCP configuration shape used by
FastMCP and many MCP clients:

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

Each loaded server is converted into a shared TOML definition under:

```plaintext
$XDG_DATA_HOME/repo-local-tools/mcp-servers/<name>.toml
```

Each loaded skill is copied under:

```plaintext
$XDG_DATA_HOME/repo-local-tools/skills/<name>/
```

## MCP server definition syntax

An MCP server definition is a TOML file. The file name and `name` field must
match. For example, the definition for `echo` lives at:

```plaintext
$XDG_DATA_HOME/repo-local-tools/mcp-servers/echo.toml
```

A minimal definition is:

```toml
name = "echo"
command = "python"
```

A definition with arguments and environment variables is:

```toml
name = "echo"
command = "python"
args = ["-m", "example"]

[env]
MODE = "test"
```

Fields are interpreted as follows:

- `name`: Required string. This is the MCP server name written into generated
  client configuration. It must match the file name without `.toml`.
- `command`: Required string. This is the executable command used to start the
  MCP server.
- `args`: Optional list of strings. These are passed to `command` in order.
- `env`: Optional TOML table. Each key and value must be a string environment
  variable.

During installation, the definition is rendered into the same `mcpServers`
shape for each supported client:

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

The generated MCP files are:

```plaintext
.mcp.json
.codex/mcp.json
.factory-droid/mcp.json
.cursor/mcp.json
```

## MCP server commands

Install one MCP server definition into the current repository:

```bash
repo-local-tools mcp install echo
```

Update all managed MCP servers:

```bash
repo-local-tools mcp update
```

Update one managed MCP server:

```bash
repo-local-tools mcp update echo
```

Commit one managed MCP server:

```bash
repo-local-tools mcp commit echo
```

The commit command stages only the files owned by the named MCP server, the
managed-tool manifest, and relevant `.gitignore` entries. It refuses to proceed
if unrelated repository changes are present.

## Skill definition syntax

A shared skill source is a directory under:

```plaintext
$XDG_DATA_HOME/repo-local-tools/skills/<name>/
```

Every skill should contain a `SKILL.md` file. The upstream Anthropic skill
format uses YAML frontmatter for discovery metadata followed by Markdown
instructions:

```markdown
---
name: reviewer
description: Review changes for correctness, risk, and missing tests.
---

# Reviewer

Use this skill when reviewing a code change before it is merged.
```

The important parts are:

- `name`: The skill identifier. Anthropic's guidance requires lowercase letters,
  numbers, and hyphens.
- `description`: A concise trigger description that tells the agent when the
  skill is relevant.
- Markdown body: The instructions, examples, scripts, and references the agent
  may load progressively when the skill is used.
- Extra files: Optional scripts, references, templates, fixtures, or assets that
  belong with the skill directory.

`repo-local-tools` copies the directory as-is into each supported repo-local
client skill location:

```plaintext
.claude/skills/<name>/
.codex/skills/<name>/
.factory-droid/skills/<name>/
.cursor/skills/<name>/
```

## `.skill` archive syntax

A `.skill` archive is a zip file containing exactly one top-level skill
directory. The argument to the install command must be an absolute path ending
in `.skill`. For example:

```plaintext
/tmp/reviewer.skill
```

The archive layout should look like:

```plaintext
reviewer/
reviewer/SKILL.md
reviewer/scripts/check.py
reviewer/REFERENCE.md
```

The archive is rejected when:

- the path is relative;
- the file is not a valid zip archive;
- the archive contains zero or multiple top-level directories;
- an entry uses an absolute path; or
- an entry contains `..` and could escape the extraction root.

## Skill commands

Install one shared skill repository:

```bash
repo-local-tools skill install reviewer
```

Install an Anthropic `.skill` archive:

```bash
repo-local-tools skill install /absolute/path/reviewer.skill
```

Update all managed skills:

```bash
repo-local-tools skill update
```

Update one managed skill:

```bash
repo-local-tools skill update reviewer
```

Commit one managed skill:

```bash
repo-local-tools skill commit reviewer
```

## Managed files and `.gitignore`

Install commands add generated client paths to `.gitignore` so ordinary Git
status output stays focused on intentional source changes. The managed-tool
manifest is not ignored:

```plaintext
.repo-local-tools/managed-tools.json
```

The manifest records each installed MCP server or skill, the source path used
for updates, the generated file paths, and the `.gitignore` patterns added for
that tool. `update` and `commit` commands use this manifest to decide which
files belong to each managed item.

`commit` commands use `git add -f` for ignored managed files. This keeps local
generated directories ignored by default, while still allowing maintainers to
commit a specific MCP server or skill intentionally.

## Example workflow

A maintainer can load a project-local MCP JSON file into the shared registry:

```bash
cat > mcp.json <<'EOF_MCP'
{
  "mcpServers": {
    "hello": {
      "command": "python",
      "args": ["-m", "http.server", "9000"]
    }
  }
}
EOF_MCP
repo-local-tools load
```

Then the maintainer can install it into a project:

```bash
repo-local-tools mcp install hello
```

After reviewing the generated files, the maintainer can commit only that MCP
server:

```bash
repo-local-tools mcp commit hello
```

## Definition format reference

See [Agent tool definition format](agent-tool-definition-format.md) for the
compact in-repository source schema reference.

[^1]: Model Context Protocol documentation:
    <https://modelcontextprotocol.io/docs/getting-started/intro>.

[^2]: Model Context Protocol specification repository:
    <https://github.com/modelcontextprotocol/modelcontextprotocol>.

[^3]: Anthropic Agent Skills documentation:
    <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview>.
