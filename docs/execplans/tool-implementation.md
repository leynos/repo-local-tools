# Implement agent tool management CLI

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
 `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: IN PROGRESS

## Purpose / big picture

After this change, a repository maintainer can run one package-provided command
to install, update, and commit local agent tool configuration for Model Context
Protocol (MCP) servers and agent skills. MCP is the protocol used by agent
clients to expose tools. A skill is a directory of reusable instructions or
resources that an agent client can load. The command must read shared source
registries under `$XDG_DATA_HOME/repo-local-tools`, install the requested tools
into the current repository, add generated local directories to `.gitignore`,
and provide explicit `update` and `commit` flows for both MCP servers and
skills.

The visible outcome is a `pyproject.toml` console script backed by Cyclopts.
Running the installed command from a repository root must support these command
families:

```plaintext
repo-local-tools mcp install <name>
repo-local-tools mcp update [<name>]
repo-local-tools mcp commit <name>
repo-local-tools skill install <name-or-archive>
repo-local-tools skill update [<name>]
repo-local-tools skill commit <name>
```

`repo-local-tools` is the proposed console script name. If implementation
uncovers an existing project convention or the user requests a shorter command,
rename the script before implementation begins and record that decision here.

## Constraints

Hard invariants for this plan are:

- Do not begin implementation until this draft is explicitly approved.
- Keep `repo_local_tools/__init__.py` backwards compatible: existing imports of
  `hello` must keep working unless the user approves removal of the generated
  template example.
- Use Cyclopts for the command tree and add it as a runtime dependency in
  `pyproject.toml`.
- Keep CLI argument annotation types that Cyclopts resolves at runtime, such as
  `pathlib.Path`, imported at runtime rather than only under
  `typing.TYPE_CHECKING`.
- Prefer shared definition inputs under `$XDG_DATA_HOME/repo-local-tools` over
  hard-coded client-specific definitions.
- Treat the current working directory as the target repository. Do not install
  into global Claude, Codex, Factory Droid, or Cursor user configuration unless
  the user explicitly broadens the scope.
- Do not overwrite user-authored local files without an atomic backup or a
  clear idempotent merge strategy.
- Keep generated, repo-local runtime material ignored by Git unless it is the
  intentionally committed artifact for `mcp commit` or `skill commit`.
- Follow the project documentation style guide in
  `docs/documentation-style-guide.md` for Markdown changes.
- Use Makefile targets for gates. Run gates sequentially and tee outputs to
  `/tmp`, not into the repository.
- Commit only after the relevant gates pass.

If satisfying the objective requires violating one of these constraints, stop,
record the conflict in `Decision Log`, and ask the user how to proceed.

## Tolerances (exception triggers)

Implementation may proceed within these limits after plan approval:

- Scope: if the implementation requires more than 12 changed repository files,
  stop and ask whether to split the work.
- Interface: if the public command shape must differ from
  `repo-local-tools mcp|skill install|update|commit`, stop and present the
  alternatives.
- Dependencies: Cyclopts may be added as a runtime dependency. If another new
  runtime dependency is needed, stop and ask before adding it.
- Data model: if shared definitions cannot represent at least Claude, Codex,
  Factory Droid, and Cursor from one source form, stop and present the schema
  trade-offs.
- Safety: if installation would require deleting directories that may contain
  user work, stop and ask before deletion.
- Git: if `commit` commands need to modify branch history beyond creating a new
  commit, stop and ask. No amend, reset, rebase, or force-push is in scope.
- Validation: if the same gate fails twice for different reasons, stop and
  summarize the failures instead of continuing to churn.
- Ambiguity: if client-specific directory conventions for Factory Droid or
  Cursor cannot be inferred from source material, implement a configurable
  adapter boundary and leave unresolved clients disabled with explicit errors,
  unless the user supplies the missing conventions.

## Risks

- Risk: The exact repo-local configuration locations for Claude, Codex, Factory
  Droid, and Cursor may differ by client version or may not have project-local
  equivalents. Severity: high Likelihood: medium Mitigation: Model clients as
  adapters with small, testable path/render functions. Use shared definitions
  as the source of truth and make unsupported clients fail explicitly until a
  location is confirmed.

- Risk: The shared definition format is not specified by an existing file.
  Severity: medium Likelihood: high Mitigation: Define a small versioned TOML
  or JSON schema in the plan's first implementation milestone, add fixtures,
  and document the schema in `docs/users-guide.md` before writing installer
  code.

- Risk: `.skill` archive handling can be confused with ordinary filesystem
  paths because the requirement says `bar.skill` is an absolute directory path
  to an Anthropic `.skill` archive. Severity: medium Likelihood: medium
  Mitigation: Treat arguments ending in `.skill` as paths and require them to
  be absolute paths. Validate the path exists, is a zip archive, and contains
  exactly one top-level skill directory before installing.

- Risk: `mcp commit` and `skill commit` may conflict with uncommitted user work
  in the target repository. Severity: high Likelihood: medium Mitigation:
  Refuse to commit if unrelated changes are present. Stage only the generated
  files and `.gitignore` lines belonging to the named MCP server or skill.
  Print the exact files that would be committed on failure.

- Risk: Strict Ruff rules may reject common Cyclopts examples, especially
  annotation imports placed under `TYPE_CHECKING`. Severity: medium Likelihood:
  medium Mitigation: Keep runtime annotations available for Cyclopts and add
  focused tests that import the CLI module and register commands.

## Progress

- [x] (2026-05-05T07:36:21Z) Confirmed the current branch is
  `tool-implementation` and created this draft at
  `docs/execplans/tool-implementation.md`.
- [x] (2026-05-05T07:36:21Z) Read `AGENTS.md`, the ExecPlan skill, the Leta
  skill, `pyproject.toml`, `Makefile`, `docs/users-guide.md`,
  `docs/documentation-style-guide.md`, `.gitignore`, and the current package
  files.
- [x] (2026-05-05T07:36:21Z) Confirmed `grepai` is unavailable because its
  Qdrant backend on `127.0.0.1:6334` is not running; this plan uses direct file
  inspection as the fallback.
- [x] (2026-05-05T08:10:40Z) Received approval to implement the plan and to
  commit formatter changes.
- [x] (2026-05-05T08:10:40Z) Added Cyclopts dependency and console script
  metadata.
- [x] (2026-05-05T08:10:40Z) Added `pytest` unit tests and `pytest-bdd`
  behavioural tests describing CLI registration, source registry loading,
  installation, update, commit, archive handling, and `.gitignore` updates.
- [x] (2026-05-05T08:10:40Z) Ran the red test gate. `make test` failed as
  expected because `repo_local_tools.agent_tools` and `repo_local_tools.cli`
  did not exist. Log: `/tmp/test-repo-local-tools-tool-implementation-red.out`.
- [x] (2026-05-05T08:10:40Z) Implemented the CLI and installer/update/commit
  services.
- [x] (2026-05-05T08:10:40Z) Updated `docs/users-guide.md` and added
  `docs/agent-tool-definition-format.md`.
- [x] (2026-05-05T08:10:40Z) Ran the implementation test gate. `make test`
  passed with 15 tests, including the `pytest-bdd` behavioural scenarios. Log:
  `/tmp/test-repo-local-tools-tool-implementation-implementation.out`.
- [x] (2026-05-05T08:20:43Z) Ran sequential gates successfully:
  `make fmt`, `make markdownlint`, `make nixie`, `make check-fmt`, `make lint`,
  `make typecheck`, `make test`, and `make all`.
- [ ] Commit the approved implementation.

## Surprises & discoveries

- Observation: The repository is currently a minimal generated package with no
  existing CLI module and no populated users' guide. Evidence:
  `repo_local_tools/pure.py` only defines `hello()`, and `docs/users-guide.md`
  only contains its heading. Impact: The implementation should introduce a
  clean feature-oriented module layout rather than retrofit into existing
  command code.

- Observation: `grepai` could not be used for semantic exploration.
  Evidence: `grepai search` failed to connect to Qdrant at `127.0.0.1:6334`.
  Impact: Planning used small direct file reads. Implementation should retry
  `grepai` first if code exploration becomes necessary.

## Decision log

- Decision: Use `repo-local-tools` as the console script name and make `mcp`
  and `skill` Cyclopts subcommands below it. Rationale: The package name
  already communicates the scope, and a single top-level script avoids
  collisions with generic commands named `mcp` or `skill`. Date/Author:
  2026-05-05T07:36:21Z / Codex

- Decision: Treat shared definitions as local source registries under
  `$XDG_DATA_HOME/repo-local-tools/mcp-servers` and
  `$XDG_DATA_HOME/repo-local-tools/skills`. Rationale: This follows the user's
  requested source paths and keeps global package data separate from
  per-repository generated files. Date/Author: 2026-05-05T07:36:21Z / Codex

- Decision: Make client support adapter-based.
  Rationale: Claude, Codex, Factory Droid, and Cursor have different config
  shapes. Adapters keep shared definition parsing independent from client file
  rendering and make unsupported or changing clients easier to isolate.
  Date/Author: 2026-05-05T07:36:21Z / Codex

- Decision: Plan for refusing unsafe Git commits from the CLI rather than
  staging broad repository state. Rationale: `mcp commit <name>` and
  `skill commit <name>` should commit a specific managed artifact. Staging
  unrelated changes would violate user work isolation. Date/Author:
  2026-05-05T07:36:21Z / Codex

- Decision: Store the repo-local managed-tool manifest as JSON at
  `.repo-local-tools/managed-tools.json`. Rationale: MCP source definitions use
  TOML as planned, but the manifest must be written by the tool. Python has a
  standard JSON writer, avoiding a second runtime dependency or a hand-rolled
  TOML serializer. Date/Author: 2026-05-05T08:10:40Z / Codex

- Decision: Render MCP definitions into `.mcp.json`, `.codex/mcp.json`,
  `.factory-droid/mcp.json`, and `.cursor/mcp.json` using the same `mcpServers`
  JSON shape. Rationale: The shared shape provides one preferred definition
  form across Claude, Codex, Factory Droid, and Cursor while keeping client
  adapters small and replaceable if a confirmed client-specific schema is later
  needed. Date/Author: 2026-05-05T08:10:40Z / Codex

- Decision: Install skills into `.claude/skills/<name>`,
  `.codex/skills/<name>`, `.factory-droid/skills/<name>`, and
  `.cursor/skills/<name>`. Rationale: This gives every requested client a
  deterministic repo-local target while preserving the original skill directory
  contents exactly. Date/Author: 2026-05-05T08:10:40Z / Codex

## Outcomes & retrospective

Implementation is in progress. The current code adds the Cyclopts command
surface, MCP and skill install/update/commit services, unit tests, behavioural
tests, and user documentation. The implementation test gate has passed. The
individual formatting, lint, typechecking, Markdown validation, test, and
aggregate gates have passed. The remaining work is to commit the implementation.

## Context and orientation

The repository root is `/data/leynos/Projects/repo-local-tools`. The package is
configured in `pyproject.toml`, currently with no runtime dependencies and no
`[project.scripts]` table. The Python package directory is `repo_local_tools/`.
It currently contains only `__init__.py` and `pure.py`, both from a generated
example. The project uses Hatchling as the build backend and `uv` for syncing.

The Makefile is the operational source of truth for gates. `make all` runs
`build`, `check-fmt`, `lint`, `typecheck`, and `test`. Markdown-only changes
also require `make markdownlint` and `make nixie`. Command output should be
captured with `tee` into `/tmp`, using names such as
`/tmp/markdownlint-repo-local-tools-tool-implementation.out`.

The relevant user requirements are:

- `mcp install <foo>` installs an MCP server in the local repository from a
  definition under `$XDG_DATA_HOME/repo-local-tools/mcp-servers`.
- MCP installs must support Claude, Codex, Factory Droid, and Cursor using
  preferred shared definition forms.
- `skill install <foo>` installs an agent skill in the local repository from a
  skill repository under `$XDG_DATA_HOME/repo-local-tools/skills`.
- If a skill argument has the form `bar.skill`, treat it as an absolute path to
  an Anthropic `.skill` archive, which is a zip file containing one named skill
  directory.
- Skill installs must support Claude, Codex, Factory Droid, and Cursor using
  preferred shared definition forms.
- Following install, add relevant generated directories to `.gitignore`.
- Implement `update` commands for MCP servers and skills. Without a name, update
  all managed MCP servers or skills in the repository. With a name, update only
  that MCP server or skill.
- Implement `commit` commands for MCP servers and skills. The command commits a
  specific managed MCP server or skill to Git.

A preferred shared definition form means one registry entry should be able to
render the per-client local files required by all supported clients. The plan
uses this interpretation because it minimizes drift between agent clients.

## Plan of work

Stage A is command and schema design. Add a small design section to
`docs/users-guide.md` that explains the source registries, the target local
repository layout, and the command examples. Define the shared MCP server
registry schema and the shared skill registry expectations in tests before
implementation. Unit tests should use `pytest` directly for parser, path,
manifest, `.gitignore`, archive-safety, and Git ownership logic. Behavioural
tests should use `pytest-bdd` feature files for end-to-end command behaviour
from a user's perspective. The MCP registry should start with one file per MCP
server under `$XDG_DATA_HOME/repo-local-tools/mcp-servers`, using a
deterministic extension such as `.toml` or `.json`. The implementation should
choose TOML unless the existing ecosystem examples in this repository point
elsewhere, because Python 3.14 includes `tomllib` for reading TOML and
`pyproject.toml` already makes TOML familiar to maintainers. If writing TOML is
required, either write it manually for simple files or stop before adding a
writer dependency.

Stage B is package and CLI scaffolding. Add `cyclopts` to
`project.dependencies` in `pyproject.toml`, add `pytest-bdd` to the `dev`
dependency group, and add:

```toml
[project.scripts]
repo-local-tools = "repo_local_tools.cli:main"
```

Create `repo_local_tools/cli.py` with a `main() -> None` entrypoint and a
Cyclopts application tree. Keep argument types such as `Path` available at
runtime. The CLI module should be thin: it parses arguments, invokes service
functions, and converts domain errors into clear command-line messages.

Stage C is domain model and registry loading. Add a feature-oriented module set
under `repo_local_tools/agent_tools/`, for example:

```plaintext
repo_local_tools/agent_tools/__init__.py
repo_local_tools/agent_tools/definitions.py
repo_local_tools/agent_tools/gitignore.py
repo_local_tools/agent_tools/git_ops.py
repo_local_tools/agent_tools/install.py
repo_local_tools/agent_tools/paths.py
repo_local_tools/agent_tools/skills.py
repo_local_tools/agent_tools/mcps.py
repo_local_tools/agent_tools/clients.py
```

`paths.py` should resolve `$XDG_DATA_HOME`, defaulting to `~/.local/share` only
when the environment variable is unset. `definitions.py` should load and
validate source definitions. `clients.py` should expose adapter objects for
Claude, Codex, Factory Droid, and Cursor. `gitignore.py` should add missing
ignore lines idempotently. `git_ops.py` should stage and commit only the files
owned by a specific managed tool.

Stage D is MCP installation. Implement `repo-local-tools mcp install <name>` so
it loads the named shared definition, renders client-specific local files into
the current repository, records enough manifest metadata to support later
updates, and updates `.gitignore` for generated directories. The plan should
prefer a manifest file such as `.repo-local-tools/managed-tools.toml` for
tracking installed tool names, source definition paths, installed file paths,
and checksums. The manifest itself should be committed when `commit` is invoked
because it is the source of update and commit ownership.

Stage E is skill installation. Implement
`repo-local-tools skill install <name>` so it copies or renders the named skill
repository from `$XDG_DATA_HOME/repo-local-tools/skills/<name>` into the local
client skill locations. Implement `.skill` archive installation by validating
an absolute path, unpacking the zip into a temporary directory, verifying that
it contains exactly one top-level skill directory, and then installing from
that directory through the same service path as registry skills. Do not trust
paths inside the zip; reject entries that would escape the extraction root.

Stage F is update behaviour. Implement `repo-local-tools mcp update [name]` and
`repo-local-tools skill update [name]` using the manifest. With a name, update
only that item. Without a name, update all installed items of that kind.
Updates should be idempotent and should print a concise summary of changed,
unchanged, and failed items. If a source definition or skill repository no
longer exists, leave the installed files untouched and report the missing
source.

Stage G is commit behaviour. Implement `repo-local-tools mcp commit <name>` and
`repo-local-tools skill commit <name>` so each command reads the manifest,
computes the owned file set for the named item, refuses to proceed if unrelated
tracked or untracked changes would be included, stages only the owned files
plus relevant `.gitignore` and manifest entries, and creates a descriptive Git
commit. The CLI should not push. Commit messages should be deterministic, for
example:

```plaintext
Install MCP server <name>

Add local agent client configuration for the <name> MCP server and record it in
repo-local-tools managed tool metadata.
```

For an update, use `Update MCP server <name>` or `Update skill <name>`.

Stage H is documentation and hardening. Expand `docs/users-guide.md` with
examples for all commands, explain `$XDG_DATA_HOME`, document archive safety
rules, document generated local directories, and document the refusal behaviour
for unsafe commits. If the implementation introduces a non-trivial schema, add
a small design note under `docs/`, such as
`docs/agent-tool-definition-format.md`, and link it from the users' guide.

## Concrete steps

From `/data/leynos/Projects/repo-local-tools`, after explicit approval:

1. Add `pytest` unit tests first for parser, manifest, `.gitignore`, archive,
   and Git helper behaviour. Add `pytest-bdd` feature files and step
   definitions for user-visible `mcp` and `skill` install, update, and commit
   flows:

   ```bash
   make test 2>&1 | tee /tmp/test-repo-local-tools-tool-implementation-red.out
   ```

   Before implementation, the new unit tests and behavioural scenarios should
   fail because the CLI modules and command handlers do not exist.

2. Add `cyclopts` and the console script in `pyproject.toml`, then run the
   sync/build gate:

   ```bash
   make build 2>&1 | tee /tmp/build-repo-local-tools-tool-implementation.out
   ```

   Expected successful tail:

   ```plaintext
   Resolved ... packages
   Installed ... packages
   ```

3. Implement the command tree, source loading, installers, update logic,
   `.gitignore` helper, and Git commit helper in small commits. After each
   logical change, run the relevant focused test command first:

   ```bash
   UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools uv run pytest tests/test_cli.py -v \
     2>&1 | tee /tmp/test-cli-repo-local-tools-tool-implementation.out
   ```

   For behavioural scenarios, run the relevant `pytest-bdd` feature-backed
   tests directly before the full suite:

   ```bash
   UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools uv run pytest tests/features -v \
     2>&1 | tee /tmp/test-bdd-repo-local-tools-tool-implementation.out
   ```

4. Run full Python gates sequentially before each implementation commit:

   ```bash
   make check-fmt 2>&1 | tee /tmp/check-fmt-repo-local-tools-tool-implementation.out
   make lint 2>&1 | tee /tmp/lint-repo-local-tools-tool-implementation.out
   make typecheck 2>&1 | tee /tmp/typecheck-repo-local-tools-tool-implementation.out
   make test 2>&1 | tee /tmp/test-repo-local-tools-tool-implementation.out
   ```

5. After documentation changes, run Markdown gates sequentially:

   ```bash
   make fmt 2>&1 | tee /tmp/fmt-repo-local-tools-tool-implementation.out
   make markdownlint 2>&1 | tee /tmp/markdownlint-repo-local-tools-tool-implementation.out
   make nixie 2>&1 | tee /tmp/nixie-repo-local-tools-tool-implementation.out
   ```

6. Before final completion, run the aggregate gate:

   ```bash
   make all 2>&1 | tee /tmp/all-repo-local-tools-tool-implementation.out
   ```

7. Commit each gated logical change using a file-based commit message. Do not
   pass commit messages with `git commit -m`.

## Validation and acceptance

Acceptance is behavioural. A reviewer should be able to create temporary source
registries, run the installed CLI from a temporary Git repository, and observe
client files, `.gitignore`, manifest entries, updates, and commits.

Required tests:

- `pytest` unit tests cover registry parsing, path resolution, manifest reads
  and writes, `.gitignore` idempotence, zip archive safety, adapter rendering,
  and Git owned-path calculation.
- `pytest-bdd` behavioural tests cover command-line scenarios for install,
  update, and commit flows for both MCP servers and skills.
- Importing `repo_local_tools.cli` succeeds and Cyclopts registers the `mcp` and
  `skill` command groups.
- `repo-local-tools mcp install example` reads
  `$XDG_DATA_HOME/repo-local-tools/mcp-servers/example.toml` or the selected
  schema equivalent and writes the expected repo-local client files.
- `repo-local-tools skill install example` reads
  `$XDG_DATA_HOME/repo-local-tools/skills/example` and writes the expected
  repo-local client files.
- `repo-local-tools skill install /absolute/path/example.skill` rejects relative
  archive paths, rejects unsafe zip entries, and accepts a valid archive with
  exactly one top-level skill directory.
- Install commands update `.gitignore` without duplicating lines.
- `update` without a name updates all installed items of that kind.
- `update <name>` updates only the named item.
- `commit <name>` stages only files owned by that item plus the required
  `.gitignore` and manifest changes.
- `commit <name>` refuses to proceed when unrelated changes would be staged or
  when the current directory is not a Git repository.
- Missing source registries and unknown names produce clear non-zero failures.

Quality criteria:

- Formatting: `make check-fmt` passes.
- Linting: `make lint` passes.
- Type checking: `make typecheck` passes.
- Tests: `make test` passes, including both direct `pytest` unit tests and
  `pytest-bdd` behavioural scenarios.
- Documentation: `make markdownlint` and `make nixie` pass after Markdown
  changes.
- Aggregate gate: `make all` passes before final completion.

## Idempotence and recovery

Install and update commands must be safe to run repeatedly. Re-running an
install for the same MCP server or skill should refresh managed files from the
same source definition, leave unrelated local files untouched, and avoid adding
duplicate `.gitignore` lines. Re-running update should produce either a changed
or unchanged summary without corrupting the manifest.

For archive installation, extraction should occur in a temporary directory. If
validation fails, no target files should be changed. If copying fails halfway,
the command should either use atomic replacement for the managed target
directory or leave enough manifest state unchanged that a later retry can
replace the partial directory safely.

For Git commits, the command should inspect repository status before staging.
If it refuses to commit, it must leave the index as it found it or clearly
state which paths it staged before failure. The preferred implementation is to
compute and validate the owned path set before staging anything.

## Artifacts and notes

Initial repository observations:

```plaintext
branch: tool-implementation
package files: repo_local_tools/__init__.py, repo_local_tools/pure.py
pyproject runtime dependencies: []
existing console scripts: none
users guide content: heading only
```

Relevant prior lesson from memory: Cyclopts command registration can fail when
argument annotation types are imported only under `TYPE_CHECKING`, because
Cyclopts resolves annotations through `typing.get_type_hints()` at runtime.

## Interfaces and dependencies

The `pyproject.toml` change should add exactly one approved runtime dependency
unless the user approves more:

```toml
[project]
dependencies = [
    "cyclopts",
]

[project.scripts]
repo-local-tools = "repo_local_tools.cli:main"
```

The CLI module should expose:

```python
from __future__ import annotations

from pathlib import Path

import cyclopts

app = cyclopts.App()


def main() -> None:
    """Run the repo-local-tools command-line interface."""
    app()
```

The service layer should expose stable functions with signatures close to:

```python
from pathlib import Path


def install_mcp(name: str, repository: Path, xdg_data_home: Path | None) -> None:
    """Install one MCP server into the repository."""


def update_mcps(name: str | None, repository: Path, xdg_data_home: Path | None) -> None:
    """Update one or all installed MCP servers."""


def commit_mcp(name: str, repository: Path) -> None:
    """Commit one managed MCP server to Git."""


def install_skill(source: str, repository: Path, xdg_data_home: Path | None) -> None:
    """Install one skill from a registry name or absolute `.skill` archive path."""


def update_skills(name: str | None, repository: Path, xdg_data_home: Path | None) -> None:
    """Update one or all installed skills."""


def commit_skill(name: str, repository: Path) -> None:
    """Commit one managed skill to Git."""
```

The exact return type may become a structured result object if tests need to
assert changed paths and status messages without parsing stdout. If so, define
the result type in `repo_local_tools/agent_tools/definitions.py` or a dedicated
`results.py` module and record that decision.

## Revision note

Initial draft created on 2026-05-05 for branch `tool-implementation`. The plan
captures the requested Cyclopts entrypoint, MCP and skill install/update/commit
behaviour, `.gitignore` handling, validation strategy, and implementation
approval gate. Implementation remains blocked pending explicit user approval.
