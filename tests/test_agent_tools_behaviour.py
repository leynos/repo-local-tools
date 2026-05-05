from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/agent_tools.feature")


class ScenarioContext:
    def __init__(self) -> None:
        self.repository = Path()
        self.xdg_data_home = Path()
        self.last_result: subprocess.CompletedProcess[str] | None = None


@pytest.fixture
def context(tmp_path: Path) -> ScenarioContext:
    context = ScenarioContext()
    context.repository = tmp_path / "repository"
    context.xdg_data_home = tmp_path / "xdg"
    return context


@given("a git repository workspace")
def git_repository_workspace(context: ScenarioContext) -> None:
    context.repository.mkdir()
    subprocess.run(
        ["git", "init"], cwd=context.repository, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@example.invalid"],
        cwd=context.repository,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Repo Local Tools Tests"],
        cwd=context.repository,
        check=True,
        capture_output=True,
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
    for relative_path in [
        ".mcp.json",
        ".codex/mcp.json",
        ".factory-droid/mcp.json",
        ".cursor/mcp.json",
    ]:
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
    for pattern in [
        ".mcp.json",
        ".codex/mcp.json",
        ".factory-droid/mcp.json",
        ".cursor/mcp.json",
    ]:
        assert pattern in content, (
            f"expected {gitignore_path} to include {pattern!r}; content: {content!r}"
        )


@then(parsers.parse('the repository has skill "{name}" in every supported client'))
def repository_has_skill(context: ScenarioContext, name: str) -> None:
    for relative_path in [
        f".claude/skills/{name}/SKILL.md",
        f".codex/skills/{name}/SKILL.md",
        f".factory-droid/skills/{name}/SKILL.md",
        f".cursor/skills/{name}/SKILL.md",
    ]:
        skill_path = context.repository / relative_path
        content = skill_path.read_text()
        assert content == "initial\n", (
            f"expected skill file {skill_path} to contain 'initial\\n', "
            f"found {content!r}"
        )


@then(parsers.parse('"{path}" ignores generated skill directories'))
def gitignore_ignores_skills(context: ScenarioContext, path: str) -> None:
    gitignore_path = context.repository / path
    content = gitignore_path.read_text()
    for pattern in [
        ".claude/skills/",
        ".codex/skills/",
        ".factory-droid/skills/",
        ".cursor/skills/",
    ]:
        assert pattern in content, (
            f"expected {gitignore_path} to include {pattern!r}; content: {content!r}"
        )


@then(parsers.parse('the repository has updated MCP configuration for "{name}"'))
def repository_has_updated_mcp(context: ScenarioContext, name: str) -> None:
    config_path = context.repository / ".mcp.json"
    config = json.loads(config_path.read_text())
    actual_command = config["mcpServers"][name]["command"]
    assert actual_command == "python3", (
        f"expected updated MCP {name!r} to use command 'python3', "
        f"found {actual_command!r}; config at {config_path}: {config!r}"
    )


@then(parsers.parse('the repository has updated skill "{name}"'))
def repository_has_updated_skill(context: ScenarioContext, name: str) -> None:
    skill_path = context.repository / f".claude/skills/{name}/SKILL.md"
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
    assert f'name = "{name}"' in content
    assert 'command = "python"' in content


@then(parsers.parse('git contains a commit with subject "{subject}"'))
def git_contains_commit(context: ScenarioContext, subject: str) -> None:
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=context.repository,
        check=True,
        capture_output=True,
        text=True,
    )
    actual_subject = result.stdout.strip()
    assert actual_subject == subject, (
        f"expected latest git commit subject {subject!r}, found {actual_subject!r}; "
        f"raw git log output: {result.stdout!r}"
    )


def run_tool(context: ScenarioContext, command: str) -> None:
    args = shlex.split(command)
    if args[0] == "repo-local-tools":
        args = [sys.executable, "-m", "repo_local_tools.cli", *args[1:]]

    environment = os.environ.copy()
    environment["XDG_DATA_HOME"] = str(context.xdg_data_home)
    environment["PYTHONPATH"] = str(Path.cwd())
    context.last_result = subprocess.run(
        args,
        cwd=context.repository,
        env=environment,
        capture_output=True,
        text=True,
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
