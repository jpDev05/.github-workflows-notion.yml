# Architecture Decisions

Use this file as lightweight architectural memory.

## ADR-001 — Evidence-first review
AI findings must be supported by repository evidence.

## ADR-002 — Human approval for automated fixes
AI-generated fixes may propose or open a PR, but must not merge directly to protected branches.

## ADR-003 — Least privilege
Workflows request only the permissions required for their job.
