"""Behavioural tests for repository-local agent tool workflows.

These pytest-bdd scenarios validate installing, loading, updating, and
committing MCP servers and skills through the CLI. Run them with
`uv run pytest tests/test_agent_tools_behaviour.py`.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from repo_local_tools.agent_tools.clients import MCP_CONFIG_PATHS, SKILL_ROOTS

scenarios("features/agent_tools.feature")
COMMAND_TIMEOUT_SECONDS = 30


@dataclasses.dataclass(slots=True)
class ScenarioContext:
    repository: Path
    xdg_data_home: Path
    last_result: subprocess.CompletedProcess[str] | None


@pytest.fixture
def context(tmp_path: Path) -> ScenarioContext:
    return ScenarioContext(
        repository=tmp_path / "repository",
        xdg_data_home=tmp_path / "xdg",
        last_result=None,
    )


@given("a git repository workspace")
def git_repository_workspace(context: ScenarioContext) -> None:
    context.repository.mkdir()
    subprocess.run(
        ["git", "init"],
        cwd=context.repository,
        check=True,
        capture_output=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@example.invalid"],
        cwd=context.repository,
        check=True,
        capture_output=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    subprocess.run(
        ["git", "config", "user.name", "Repo Local Tools Tests"],
        cwd=context.repository,
        check=True,
        capture_output=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )


@given(parsers.parse('an MCP registry definition named "{name}"'))
def mcp_registry_definition(context: ScenarioContext, name: str) -> None:
    write_mcp_definition(context, name, command="python")


@given(parsers.parse('a skill registry directory named "{name}"'))
def skill_registry_directory(context: ScenarioContext, name: str) -> None:
    write_skill(context.xdg_data_home / "repo-local-tools" / "skills" / name, "initial")


@given(parsers.parse('a local skill source named "{name}"'))
def local_skill_source(context: ScenarioContext, name: str) -> None:
    write_skill(context.repository / "skills" / name, "local")


@given(parsers.parse('a local MCP JSON configuration for "{name}"'))
def local_mcp_json_configuration(context: ScenarioContext, name: str) -> None:
    (context.repository / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    name: {"command": "python", "args": ["-m", "example"]},
                },
            },
        ),
    )


@given(parsers.parse('an installed MCP server named "{name}"'))
def installed_mcp_server(context: ScenarioContext, name: str) -> None:
    mcp_registry_definition(context, name)
    run_tool(context, f"repo-local-tools mcp install {name}")


@given(parsers.parse('an installed skill named "{name}"'))
def installed_skill(context: ScenarioContext, name: str) -> None:
    skill_registry_directory(context, name)
    run_tool(context, f"repo-local-tools skill install {name}")


@when(parsers.parse('I run "{command}"'))
def run_named_command(context: ScenarioContext, command: str) -> None:
    run_tool(context, command)


@when(parsers.parse('I change the MCP registry definition named "{name}"'))
def change_mcp_registry_definition(context: ScenarioContext, name: str) -> None:
    write_mcp_definition(context, name, command="python3")


@when(parsers.parse('I change the skill registry directory named "{name}"'))
def change_skill_registry_directory(context: ScenarioContext, name: str) -> None:
    write_skill(context.xdg_data_home / "repo-local-tools" / "skills" / name, "updated")


@then("the command succeeds")
def command_succeeds(context: ScenarioContext) -> None:
    assert context.last_result is not None, "no command result was captured"
    assert context.last_result.returncode == 0, (
        f"expected command to succeed with return code 0, found "
        f"{context.last_result.returncode}; stderr: {context.last_result.stderr!r}; "
        f"stdout: {context.last_result.stdout!r}"
    )


@then(
    parsers.parse(
        'the repository has MCP configuration for "{name}" in every supported client'
    )
)
def repository_has_mcp_config(context: ScenarioContext, name: str) -> None:
    for relative_path in MCP_CONFIG_PATHS:
        config_path = context.repository / relative_path
        config = json.loads(config_path.read_text())
        actual_command = config["mcpServers"][name]["command"]
        assert actual_command == "python", (
            f"expected MCP {name!r} in {relative_path} to use command 'python', "
            f"found {actual_command!r}; config at {config_path}: {config!r}"
        )


@then(parsers.parse('"{path}" ignores generated MCP configuration'))
def gitignore_ignores_mcp(context: ScenarioContext, path: str) -> None:
    gitignore_path = context.repository / path
    content = gitignore_path.read_text()
    for pattern in (relative_path.as_posix() for relative_path in MCP_CONFIG_PATHS):
        assert pattern in content, (
            f"expected {gitignore_path} to include {pattern!r}; content: {content!r}"
        )


@then(parsers.parse('the repository has skill "{name}" in every supported client'))
def repository_has_skill(context: ScenarioContext, name: str) -> None:
    for root in SKILL_ROOTS:
        skill_path = context.repository / root / name / "SKILL.md"
        content = skill_path.read_text()
        assert content == "initial\n", (
            f"expected skill file {skill_path} to contain 'initial\\n', "
            f"found {content!r}"
        )


@then(parsers.parse('"{path}" ignores generated skill directories'))
def gitignore_ignores_skills(context: ScenarioContext, path: str) -> None:
    gitignore_path = context.repository / path
    content = gitignore_path.read_text()
    for pattern in (f"{root.as_posix()}/" for root in SKILL_ROOTS):
        assert pattern in content, (
            f"expected {gitignore_path} to include {pattern!r}; content: {content!r}"
        )


@then(parsers.parse('the repository has updated MCP configuration for "{name}"'))
def repository_has_updated_mcp(context: ScenarioContext, name: str) -> None:
    for relative_path in MCP_CONFIG_PATHS:
        config_path = context.repository / relative_path
        config = json.loads(config_path.read_text())
        actual_command = config["mcpServers"][name]["command"]
        assert actual_command == "python3", (
            f"expected updated MCP {name!r} in {relative_path} to use command "
            f"'python3', found {actual_command!r}; config at {config_path}: "
            f"{config!r}"
        )


@then(parsers.parse('the repository has updated skill "{name}"'))
def repository_has_updated_skill(context: ScenarioContext, name: str) -> None:
    for root in SKILL_ROOTS:
        skill_path = context.repository / root / name / "SKILL.md"
        content = skill_path.read_text()
        assert content == "updated\n", (
            f"expected updated skill file {skill_path} to contain 'updated\\n', "
            f"found {content!r}"
        )


@then(parsers.parse('the shared registry has skill "{name}"'))
def shared_registry_has_skill(context: ScenarioContext, name: str) -> None:
    skill_path = (
        context.xdg_data_home / "repo-local-tools" / "skills" / name / "SKILL.md"
    )
    content = skill_path.read_text()
    assert content == "local\n", (
        f"expected shared skill {name!r} at {skill_path} to contain 'local\\n', "
        f"found {content!r}"
    )


@then(parsers.parse('the shared registry has MCP server "{name}"'))
def shared_registry_has_mcp_server(context: ScenarioContext, name: str) -> None:
    definition_path = (
        context.xdg_data_home / "repo-local-tools" / "mcp-servers" / f"{name}.toml"
    )
    content = definition_path.read_text()
    assert f'name = "{name}"' in content, (
        f"expected {definition_path} to define MCP name {name!r}; content: {content!r}"
    )
    assert 'command = "python"' in content, (
        f"expected {definition_path} to define command 'python'; content: {content!r}"
    )


@then(parsers.parse('git contains a commit with subject "{subject}"'))
def git_contains_commit(context: ScenarioContext, subject: str) -> None:
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=context.repository,
        check=True,
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    actual_subject = result.stdout.strip()
    assert actual_subject == subject, (
        f"expected latest git commit subject {subject!r}, found {actual_subject!r}; "
        f"raw git log output: {result.stdout!r}"
    )


def run_tool(context: ScenarioContext, command: str) -> None:
    stripped_command = command.strip()
    if not stripped_command:
        msg = "command must not be empty"
        raise ValueError(msg)
    args = shlex.split(stripped_command)
    if args[0] == "repo-local-tools":
        args = [sys.executable, "-m", "repo_local_tools.cli", *args[1:]]

    environment = os.environ.copy()
    environment["XDG_DATA_HOME"] = str(context.xdg_data_home)
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    if existing_pythonpath:
        environment["PYTHONPATH"] = f"{existing_pythonpath}{os.pathsep}{Path.cwd()}"
    else:
        environment["PYTHONPATH"] = str(Path.cwd())
    context.last_result = subprocess.run(
        args,
        cwd=context.repository,
        env=environment,
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )


def write_mcp_definition(context: ScenarioContext, name: str, command: str) -> None:
    registry = context.xdg_data_home / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True, exist_ok=True)
    (registry / f"{name}.toml").write_text(
        f'name = "{name}"\ncommand = "{command}"\nargs = ["-m", "example"]\n',
    )


def write_skill(skill_directory: Path, body: str) -> None:
    skill_directory.mkdir(parents=True, exist_ok=True)
    (skill_directory / "SKILL.md").write_text(f"{body}\n")
