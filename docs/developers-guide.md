# Developers' guide

This guide records internal conventions for maintaining repo-local-tools.

## Coverage publication

Pull-request CI generates coverage for the `./repo_local_tools` package, the
scope the earlier Slipcover step measured, with the ratchet
(`with-ratchet: 'true'`) against the baseline that `coverage-main.yml` writes
on pushes to `main`, and publishes no coverage artefact
(`publish-artefact: 'false'`). Nothing a pull request runs invokes CodeScene,
runs `cs-coverage`, receives `CS_ACCESS_TOKEN`, or names the CodeScene host.

`coverage-main.yml` is the single publisher. It runs on pushes to `main` and on
manual dispatch, reports whether `CS_ACCESS_TOKEN` is set from a
`codescene-token` check step that binds nothing, passes the secret to the
upload action as `access-token` (never in any `env`, which the composite action
hands to its nested steps), guards the upload on exactly
`steps.codescene-token.outputs.available == 'true' && github.ref == 'refs/heads/main'`
so a dispatch from another branch cannot upload, uploads with `mode: upload`,
and declares a concurrency group keyed on the ref alone that never cancels:
GitHub keeps one pending run per group, so triggered runs (push and dispatch)
never overlap and the newest one's coverage lands last. A manual re-run of an
older run is an operator action that republishes that commit's coverage and
baseline until the next push supersedes it. The uploader pins the CodeScene CLI
through its own manifest, so no checksum input or `CODESCENE_CLI_SHA256`
variable is used.

Dependabot automerge merges are made with `GITHUB_TOKEN`, which fires no push
workflow, so they are a known exception: their coverage is published by the
next push to `main` or a manual dispatch. A dispatch that replaces a pending
push leaves the ratchet baseline one commit behind until the next push, because
only a push saves it. Both are tracked as issue 518 in leynos/shared-actions.

The reason is the call, not the artefact: the CLI talks to CodeScene's API,
whose answers have changed shape and failed every pull request at once, and a
fork cannot read the token anyway. The ratchet applies the same gate from this
repository's own baseline.

### Workflow contract helpers

`tests/test_codescene_coverage_contract.py` holds the rule over this
repository's workflows. `tests/test_codescene_closure_cases.py` and
`tests/test_codescene_publisher_cases.py` drive the same readings over
constructed documents, one breach each, so every clause is shown to catch what
it names. The readings live in `tests/helpers/`:

- `workflow_reading.py` parses workflows and local actions with a loader that
  refuses duplicate keys, reads `on:` in scalar, sequence, and mapping form
  under either key, and walks every key and value of a document.
- `workflow_closure.py` computes the pull-request surface: workflows triggered
  by `pull_request`, `pull_request_target`, `pull_request_review`,
  `pull_request_review_comment`, `merge_group`, `issue_comment`, or
  `workflow_run`, or by a push to any branch other than `main`, and every local
  workflow or composite action they reach through `./` or `$/` references. It
  refuses qualified self-calls and local references carrying `@ref`.
- `codescene_reach.py`, `codescene_publisher.py`, and `codescene_binding.py`
  hold the CodeScene clauses.

The two generic modules know nothing about CodeScene and may be reused by any
workflow contract in this repository. They are test support only: nothing under
`repo_local_tools/` may import them.
