# Changelog

## Unreleased

- Added automatic loading of the consumer repository `.ai-devops.yml` policy.
- Added dependency-free policy parsing so consuming repositories do not need PyYAML.
- Added policy-driven PR review event, quality gate defaults and inline finding limits.
- Added regression tests for policy parsing and safe defaults.


All notable changes to AI DevOps are documented here.

## [Unreleased]

### Added
- Security Intelligence scanner.
- CodeQL v4 workflow for Python and GitHub Actions.
- Test Intelligence runner for common ecosystems.
- AI evaluation standard and review fixtures.
- Dependabot configuration.
- Pull Request Intelligence action.
- Inline findings anchored to added lines.
- PR review decisions: COMMENT, APPROVE and REQUEST_CHANGES.
- PR quality gate support.
- Repository architecture documentation.
- Reusable .ai-devops.yml policy template.

### Security
- PR automation uses the pull_request event by default.
- Findings are validated before publication.
- APPROVE is automatically downgraded to COMMENT when high-impact findings exist.
- Fork PRs without a Groq secret are skipped instead of receiving privileged credentials.

## [v1]
- Groq structured code review.
- Notion synchronization.
- Quality/security/maintainability scoring.
- Evidence-first review rules.
- GitHub Step Summary.
- Retry/backoff for Groq rate limits.
- Recovery of near-complete structured responses.
- Reusable GitHub Action.
