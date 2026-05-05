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

- [Model Context Protocol documentation](https://modelcontextprotocol.io/docs/getting-started/intro)
  explains MCP, its architecture, servers, clients, SDKs, and examples.
- [Model Context Protocol specification repository](https://github.com/modelcontextprotocol/modelcontextprotocol)
  contains the protocol specification, schema, and official documentation
  source.
- [Anthropic Agent Skills documentation](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
  explains skill structure, progressive disclosure, supported Claude surfaces,
  runtime constraints, and examples.

## Command overview

Commands are run from the target repository root. The command treats the
current working directory as the repository that receives generated files.

```bash
repo-local-tools --help
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

The `install` commands render files into the current repository. The `update`
commands refresh installed items from their original source definitions. The
`commit` commands create a Git commit for one managed item and refuse to
proceed when unrelated changes are present.

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
directory. The install argument must be an absolute path ending in `.skill`.
For example:

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
generated directories ignored by default while still allowing maintainers to
commit a specific MCP server or skill intentionally.

## Example workflow

A maintainer can define a shared MCP server once:

```bash
mkdir -p "${XDG_DATA_HOME:-$HOME/.local/share}/repo-local-tools/mcp-servers"
cat > "${XDG_DATA_HOME:-$HOME/.local/share}/repo-local-tools/mcp-servers/hello.toml" <<'EOF_MCP'
name = "hello"
command = "python"
args = ["-m", "http.server", "9000"]
EOF_MCP
```

Then the maintainer can install it into a project:

```bash
cd /path/to/project
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
