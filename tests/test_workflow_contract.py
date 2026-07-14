"""Contract tests for the mutation-testing caller workflow.

The executable logic lives in the ``leynos/shared-actions`` reusable
workflow, which carries its own unit and integration tests; this
repository's caller is declarative configuration. These tests parse the
caller with PyYAML and assert the contract it must uphold, so drift
(repointing the reference at a branch, widening permissions, or losing
the layout configuration) fails CI on the pull request rather than
surfacing in a scheduled or manual run.

The caller must reference the correct reusable workflow at a commit
SHA. Dependabot owns the SHA value and bumps it independently, so these
tests assert the shape of the reference (the workflow path pinned to a
full 40-hex commit SHA) rather than a specific pinned value.
"""

from __future__ import annotations

import re
import typing as typ
from pathlib import Path

import pytest
import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "mutation-testing.yml"
)

pytestmark = pytest.mark.skipif(
    not WORKFLOW_PATH.exists(),
    reason=(
        "workflow file not present in this working copy (for example "
        "inside mutmut's mutants/ sandbox, which does not copy .github/)"
    ),
)

#: Matches the mutation-mutmut reusable workflow pinned to a full
#: 40-hex commit SHA. Dependabot owns the SHA value; this pattern
#: guards against repointing the caller at a mutable branch or tag
#: without asserting which commit is currently referenced.
USES_RE = re.compile(
    r"^leynos/shared-actions/\.github/workflows/mutation-mutmut\.yml@[0-9a-f]{40}$"
)

#: The exact caller configuration for this repository: flat package
#: layout, so change detection watches repo_local_tools/ and no src/
#: prefix is stripped during module-glob translation. The runner Python
#: matches pyproject's requires-python (>= 3.14).
EXPECTED_WITH = {
    "paths": "repo_local_tools/",
    "module-prefix-strip": "",
    "python-version": "3.14",
}


def _as_mapping(value: object, message: str) -> dict[object, object]:
    """Assert ``value`` is a mapping and narrow its type for ty."""
    assert isinstance(value, dict), message
    return typ.cast("dict[object, object]", value)


def _load() -> dict[object, object]:
    """Parse the workflow file."""
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return _as_mapping(workflow, "the workflow must parse to a mapping")


def _triggers(workflow: dict[object, object]) -> dict[object, object]:
    """Return the ``on:`` mapping (PyYAML parses the bare key as True)."""
    triggers = workflow.get("on", workflow.get(True))
    return _as_mapping(triggers, "the workflow must declare an on: mapping")


def _mutation_job(workflow: dict[object, object]) -> dict[object, object]:
    """Return the single calling job."""
    jobs = _as_mapping(workflow.get("jobs"), "the workflow must declare jobs")
    assert jobs, "the workflow must declare at least one job"
    assert list(jobs) == ["mutation"], (
        f"expected a single job named 'mutation', found {sorted(jobs)}"
    )
    return _as_mapping(jobs["mutation"], "jobs.mutation must be a mapping")


def test_uses_reference_is_pinned_to_a_commit_sha() -> None:
    """The job must call mutation-mutmut.yml pinned to a full commit SHA.

    The exact SHA is not asserted: Dependabot owns that value and bumps
    it independently, so this test only checks the reusable-workflow
    path and that the ref is a 40-hex commit SHA rather than a mutable
    branch or tag.
    """
    uses = _mutation_job(_load()).get("uses")
    assert isinstance(uses, str), "jobs.mutation.uses is missing"
    assert USES_RE.match(uses), (
        f"jobs.mutation.uses must reference mutation-mutmut.yml pinned to a "
        f"full 40-hex commit SHA, not a branch or tag: {uses!r}"
    )


def test_job_permissions_are_exactly_least_privilege() -> None:
    """The job grants contents: read and id-token: write, nothing broader."""
    permissions = _mutation_job(_load()).get("permissions")
    assert permissions == {"contents": "read", "id-token": "write"}, (
        "jobs.mutation.permissions must be exactly "
        f"{{'contents': 'read', 'id-token': 'write'}}, got {permissions!r}"
    )


def test_workflow_default_permissions_are_empty() -> None:
    """The workflow-level default token scope is empty."""
    workflow = _load()
    assert workflow.get("permissions") == {}, (
        f"top-level permissions must be an empty mapping, got "
        f"{workflow.get('permissions')!r}"
    )


def test_concurrency_serializes_per_ref_without_cancelling() -> None:
    """Runs queue per ref instead of cancelling one another."""
    concurrency = _as_mapping(
        _load().get("concurrency"), "the workflow must declare concurrency"
    )
    assert concurrency.get("group") == "mutation-testing-${{ github.ref }}", (
        f"concurrency.group must key on the triggering ref, got "
        f"{concurrency.get('group')!r}"
    )
    assert concurrency.get("cancel-in-progress") is False, (
        f"concurrency.cancel-in-progress must be false, got "
        f"{concurrency.get('cancel-in-progress')!r}"
    )


def test_triggers_keep_schedule_and_plain_dispatch() -> None:
    """The daily schedule stays; dispatch declares no inputs."""
    triggers = _triggers(_load())
    schedule = triggers.get("schedule")
    assert schedule == [{"cron": "35 7 * * *"}], (
        f"on.schedule must be the daily 07:35 UTC cron, got {schedule!r}"
    )
    assert "workflow_dispatch" in triggers, "on.workflow_dispatch is missing"
    dispatch = triggers.get("workflow_dispatch")
    if dispatch is not None:
        inputs = _as_mapping(
            dispatch, "on.workflow_dispatch must be a mapping when non-empty"
        ).get("inputs")
        assert not inputs, (
            f"on.workflow_dispatch must declare no inputs; the Actions "
            f"run-workflow control selects the ref, got {inputs!r}"
        )


def test_with_block_carries_the_caller_configuration() -> None:
    """The caller passes exactly the flat-layout configuration."""
    with_block = _mutation_job(_load()).get("with")
    assert isinstance(with_block, dict), "jobs.mutation.with is missing"
    assert with_block == EXPECTED_WITH, (
        f"jobs.mutation.with must be exactly {EXPECTED_WITH!r}, got {with_block!r}"
    )
