# Changelog

All notable changes to AI DevOps are documented here.

## [Unreleased]

### Added
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
