"""Keep CodeScene coverage publication restricted to the main workflow."""

from __future__ import annotations

import typing as typ
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"
MAIN_PATH = ROOT / ".github" / "workflows" / "coverage-main.yml"
GENERATE_ACTION = "leynos/shared-actions/.github/actions/generate-coverage"
UPLOAD_ACTION = "leynos/shared-actions/.github/actions/upload-codescene-coverage"


def _workflow(path: Path) -> dict[str, object]:
    """Load a workflow and normalise PyYAML's YAML 1.1 ``on`` key."""
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict), f"{path} must contain a mapping"
    if True in workflow:
        workflow["on"] = workflow.pop(True)
    return typ.cast("dict[str, object]", workflow)


def _job(workflow: dict[str, object], name: str) -> dict[str, object]:
    """Return a named job after validating its mapping shape."""
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict), "workflow must declare jobs"
    jobs_by_name = typ.cast("dict[str, object]", jobs)
    job = jobs_by_name.get(name)
    assert isinstance(job, dict), f"workflow must declare {name!r}"
    return typ.cast("dict[str, object]", job)


def _step(job: dict[str, object], name: str) -> dict[str, object]:
    """Return a named step after validating the workflow step list."""
    steps = job.get("steps")
    assert isinstance(steps, list), "job must declare steps"
    step = next(
        (
            typ.cast("dict[str, object]", candidate)
            for candidate in steps
            if isinstance(candidate, dict)
            and typ.cast("dict[str, object]", candidate).get("name") == name
        ),
        None,
    )
    assert isinstance(step, dict), f"job must declare {name!r}"
    return typ.cast("dict[str, object]", step)


def _inputs(step: dict[str, object], action: str) -> dict[str, object]:
    """Return inputs after asserting the action is pinned to a commit SHA."""
    uses = step.get("uses")
    assert isinstance(uses, str), "workflow action must declare a uses string"
    assert uses.startswith(f"{action}@"), "workflow action must use the expected path"
    reference = uses.rsplit("@", maxsplit=1)[1]
    assert len(reference) == 40, "workflow action must be pinned to a full SHA"
    assert all(character in "0123456789abcdef" for character in reference), (
        "workflow action SHA must use lowercase hexadecimal"
    )
    inputs = step.get("with")
    assert isinstance(inputs, dict), "workflow action must declare inputs"
    return typ.cast("dict[str, object]", inputs)


def test_pull_request_coverage_is_local_and_ratcheted() -> None:
    """Keep pull-request coverage free of CodeScene credentials and tools."""
    workflow = _workflow(CI_PATH)
    triggers = workflow.get("on")
    assert isinstance(triggers, dict), "ci.yml must declare trigger mappings"
    assert "pull_request" in triggers, "ci.yml must run on pull requests"
    workflow_environment = workflow.get("env", {})
    assert isinstance(workflow_environment, dict), "ci.yml env must be a mapping"
    assert "CS_ACCESS_TOKEN" not in workflow_environment

    lint_test = _job(workflow, "lint-test")
    environment = lint_test.get("env", {})
    assert isinstance(environment, dict), "lint-test env must be a mapping"
    assert "CS_ACCESS_TOKEN" not in environment
    coverage = _step(lint_test, "Generate coverage")
    assert coverage.get("if") == "github.event_name == 'pull_request'"
    inputs = _inputs(coverage, GENERATE_ACTION)
    assert inputs.get("python-source") == "./repo_local_tools"
    assert inputs.get("pytest-workers") == ""
    assert inputs.get("with-ratchet") == "true"
    assert "cs-coverage" not in CI_PATH.read_text(encoding="utf-8")
    assert "codescene.io" not in CI_PATH.read_text(encoding="utf-8")


def test_main_coverage_publishes_the_local_measurement() -> None:
    """Require main-only publication and explicit CodeScene upload mode."""
    workflow = _workflow(MAIN_PATH)
    assert workflow.get("on") == {
        "push": {"branches": ["main"]},
        "workflow_dispatch": None,
    }
    coverage_upload = _job(workflow, "coverage-upload")
    inputs = _inputs(_step(coverage_upload, "Generate coverage"), GENERATE_ACTION)
    assert inputs.get("python-source") == "./repo_local_tools"
    assert inputs.get("pytest-workers") == ""
    assert inputs.get("with-ratchet") == "true"
    upload_inputs = _inputs(
        _step(coverage_upload, "Upload coverage data to CodeScene"), UPLOAD_ACTION
    )
    assert upload_inputs.get("mode") == "upload"
