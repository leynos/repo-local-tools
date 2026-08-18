# repo-local-tools developers' guide

This guide covers the internal workings, testing strategy, and maintenance
workflows for contributors to `repo-local-tools`.

## Mutation-testing workflow contract tests

This repository runs scheduled, informational mutation testing through a thin
caller workflow,
[`.github/workflows/mutation-testing.yml`](../.github/workflows/mutation-testing.yml),
which delegates to the shared reusable workflow
`leynos/shared-actions/.github/workflows/mutation-mutmut.yml`. The heavy lifting
— running `mutmut`, and summarizing survivors — lives in `shared-actions`; this
repository carries only declarative configuration. The run is **informational
only**: it never gates a pull request. Survivors are reported through the job
summary and downloadable artefacts so they can be triaged into tests, not
enforced as a blocking check. The mutation targets and test selection
themselves are configured in `[tool.mutmut]` in `pyproject.toml`
(`source_paths`, `pytest_add_cli_args_test_selection`, `also_copy`, and
`do_not_mutate`).

The workflow runs in two modes. A **daily schedule** fires a change-scoped run
that mutates only the source files touched within the detection window, so
quiet days are cheap no-ops. A **manual dispatch** (the Actions "Run workflow"
control) mutates the whole package; select a branch in that control to exercise
a feature branch.

The caller passes a small set of configuration inputs, each carrying intent:

- `paths` — the change-detection root (`repo_local_tools/`) that decides whether
  a scheduled run has anything to mutate, bounding the scheduled run to real
  source changes.
- `module-prefix-strip` — the leading path prefix removed when translating
  changed files to module globs. It is empty here because the package uses a
  flat layout with no `src/` prefix to strip.
- `python-version` — the interpreter the run uses (`3.14`), matching
  `pyproject.toml`'s `requires-python` (`>= 3.14`). The shared workflow's
  default of 3.13 would hard-error against this repository.

The `uses:` reference pins the shared workflow to a full 40-character commit
SHA rather than a branch or tag, so a force-push upstream cannot silently
change what runs here. The contract test asserts only that the pin is a full
commit SHA, not a particular value, so Dependabot bumps it automatically
without any accompanying test edit.

Because the caller is configuration rather than code, a contract test pins the
shape it must uphold, failing the pull request when the caller drifts —
repointing the pin at a branch, widening the token scope, or dropping a
configuration input — rather than letting the breakage surface only in a
scheduled run. The test module self-skips when the workflow file is absent
(mutmut copies the sources into a sandbox that omits `.github/`, so the contract
test does not run there). Run it locally with
`uv run pytest tests/test_workflow_contract.py -v`. The test validates:

- the `uses:` reference targets `mutation-mutmut.yml` pinned to a full commit
  SHA;
- the `with:` block carries exactly the expected configuration (`paths`,
  `module-prefix-strip`, and `python-version` above);
- job permissions are least-privilege (`contents: read`, `id-token: write`) and
  the workflow-level default token scope is empty;
- `concurrency` serializes runs per ref without cancelling one in progress; and
- the triggers keep the daily schedule and a plain `workflow_dispatch` with no
  legacy branch input.
