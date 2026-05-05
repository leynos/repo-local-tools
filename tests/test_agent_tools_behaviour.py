from __future__ import annotations

import json
import os
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
    assert context.last_result is not None
    assert context.last_result.returncode == 0, context.last_result.stderr


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
        config = json.loads((context.repository / relative_path).read_text())
        assert config["mcpServers"][name]["command"] == "python"


@then(parsers.parse('"{path}" ignores generated MCP configuration'))
def gitignore_ignores_mcp(context: ScenarioContext, path: str) -> None:
    content = (context.repository / path).read_text()
    assert ".mcp.json" in content
    assert ".codex/mcp.json" in content
    assert ".factory-droid/mcp.json" in content
    assert ".cursor/mcp.json" in content


@then(parsers.parse('the repository has skill "{name}" in every supported client'))
def repository_has_skill(context: ScenarioContext, name: str) -> None:
    for relative_path in [
        f".claude/skills/{name}/SKILL.md",
        f".codex/skills/{name}/SKILL.md",
        f".factory-droid/skills/{name}/SKILL.md",
        f".cursor/skills/{name}/SKILL.md",
    ]:
        assert (context.repository / relative_path).read_text() == "initial\n"


@then(parsers.parse('"{path}" ignores generated skill directories'))
def gitignore_ignores_skills(context: ScenarioContext, path: str) -> None:
    content = (context.repository / path).read_text()
    assert ".claude/skills/" in content
    assert ".codex/skills/" in content
    assert ".factory-droid/skills/" in content
    assert ".cursor/skills/" in content


@then(parsers.parse('the repository has updated MCP configuration for "{name}"'))
def repository_has_updated_mcp(context: ScenarioContext, name: str) -> None:
    config = json.loads((context.repository / ".mcp.json").read_text())
    assert config["mcpServers"][name]["command"] == "python3"


@then(parsers.parse('the repository has updated skill "{name}"'))
def repository_has_updated_skill(context: ScenarioContext, name: str) -> None:
    assert (
        context.repository / f".claude/skills/{name}/SKILL.md"
    ).read_text() == "updated\n"


@then(parsers.parse('git contains a commit with subject "{subject}"'))
def git_contains_commit(context: ScenarioContext, subject: str) -> None:
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=context.repository,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == subject


def run_tool(context: ScenarioContext, command: str) -> None:
    args = command.split()
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
