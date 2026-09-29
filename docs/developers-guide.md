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

Both coverage lanes set up Python 3.14 with `actions/setup-python`, inside the
project's `requires-python` (`>=3.14`). generate-coverage chooses its
interpreter from its `python-version` input, then `UV_PYTHON`, then
`.python-version`, then the `python3` on `PATH`, which is the most recent
`setup-python` step before the call in its job; `uv sync` refuses an
interpreter outside `requires-python`. `tests/test_coverage_python_version.py`,
with its reader in `tests/coverage_python_sources.py`, requires every
generate-coverage call in the pull-request lane and the publisher to declare at
least one of those sources, every declared source to name the same version,
that version to be inside `requires-python`, and both lanes to measure on that
one version. A `setup-python` step guarded by `if:` or allowed to fail with
`continue-on-error` declares nothing. The ratchet baseline key already carries
the interpreter (`ratchet-baseline-<os>-py<major.minor>-`), so a lane on
another Python would miss its baseline rather than compare against the wrong
one; the contract turns that silent restart into a failure. It uses
`packaging`, a development dependency.

### Workflow contracts

`make test-workflow-contracts`, which `ci.yml` runs as its own step, holds the
CodeScene coverage shape over this repository's workflows and local actions by
running `cv005-contracts check`, the shared contract library in
`leynos/shared-actions`, from the full commit named by `CV005_CONTRACTS_REF` in
the Makefile; a fix to the rules is a pin bump. The library reads workflows
with a loader that refuses duplicate keys, follows the pull-request surface
through local `./` and `$/` calls and composite actions, and drives every
clause against breaching fixtures in its own suite, so this repository keeps no
copy of the readers. The repository's parameters are in `.github/cv005.toml`:
`repository`, and the publisher's exact `[selection]`, so a change made to the
generators and the uploader together is still a reviewed change.
