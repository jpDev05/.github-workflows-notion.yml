# Contributing to AI DevOps

Thank you for contributing.

## Development principles

1. Evidence before opinion.
2. Never expose secrets in logs, fixtures or tests.
3. Prefer deterministic validation around AI output.
4. Keep GitHub permissions least-privileged.
5. Do not use pull_request_target to expose secrets to untrusted code.
6. Add a regression fixture for every important false positive or false negative.
7. Keep provider-specific code behind a small interface whenever possible.

## Before opening a pull request

Run:

    python -m compileall -q pr-review scripts tests

and, when available:

    python -m pytest -q

For workflow changes, validate YAML syntax.

## Pull request checklist

- [ ] Tests or evaluation fixture added.
- [ ] Security implications considered.
- [ ] AI findings remain evidence-backed.
- [ ] Documentation updated.
- [ ] No secrets committed.
- [ ] Permissions are minimal.

## Commit style

Use conventional prefixes when practical:

- feat:
- fix:
- security:
- test:
- docs:
- refactor:
- chore:
