# repo-local-tools users' guide

`repo-local-tools` manages repository-local agent tool configuration. It reads
shared source definitions from `$XDG_DATA_HOME/repo-local-tools`, installs the
requested Model Context Protocol (MCP) servers and skills into the current Git
repository, records ownership metadata, and lets maintainers update or commit
managed files explicitly.

Run commands from the target repository root.

## Source registry layout

The tool reads shared source data from the XDG data directory. If
`$XDG_DATA_HOME` is unset, the default root is
`~/.local/share/repo-local-tools`.

MCP server definitions live under:

```plaintext
$XDG_DATA_HOME/repo-local-tools/mcp-servers/<name>.toml
```

Skill repositories live under:

```plaintext
$XDG_DATA_HOME/repo-local-tools/skills/<name>/
```

Anthropic `.skill` archives may also be installed directly. Archive paths must
be absolute and must point at a zip file containing exactly one top-level skill
directory.

## MCP server commands

Install one MCP server definition into the current repository:

```bash
repo-local-tools mcp install echo
```

This reads:

```plaintext
$XDG_DATA_HOME/repo-local-tools/mcp-servers/echo.toml
```

It writes repo-local client configuration for Claude, Codex, Factory Droid, and
Cursor:

```plaintext
.mcp.json
.codex/mcp.json
.factory-droid/mcp.json
.cursor/mcp.json
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

## Skill commands

Install one shared skill repository:

```bash
repo-local-tools skill install reviewer
```

This reads:

```plaintext
$XDG_DATA_HOME/repo-local-tools/skills/reviewer/
```

It writes the skill into each repo-local client location:

```plaintext
.claude/skills/reviewer/
.codex/skills/reviewer/
.factory-droid/skills/reviewer/
.cursor/skills/reviewer/
```

Install an Anthropic `.skill` archive:

```bash
repo-local-tools skill install /absolute/path/reviewer.skill
```

The archive is validated before extraction. Entries that escape the archive
root are rejected, and archives with zero or multiple top-level directories are
rejected.

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
generated directories ignored by default while still allowing maintainers to
commit a specific MCP server or skill intentionally.

## Definition format

See [Agent tool definition format](agent-tool-definition-format.md) for the
shared MCP definition schema and the skill source rules.
