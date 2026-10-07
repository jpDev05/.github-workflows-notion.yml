# AI DevOps Architecture Memory

## Purpose
Describe the system boundaries, important modules, and invariants that reviewers must preserve.

## Architecture
<!-- Keep this section short and factual. -->

## Invariants
- Do not expose secrets in logs.
- Do not execute untrusted pull request code with privileged credentials.
- Keep security findings evidence-backed.
- Prefer least-privilege GitHub permissions.

## Boundaries
<!-- Example: API, persistence, UI, workers, integrations. -->

## Important Decisions
See `.ai-devops/decisions.md`.

## Review Notes
<!-- Add project-specific constraints here. -->
