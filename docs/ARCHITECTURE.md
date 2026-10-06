# AI DevOps Architecture

## Overview

AI DevOps is split into two automation surfaces:

- Push/commit review: Groq analysis, quality scoring, Step Summary and Notion.
- Pull Request Intelligence: Groq analysis, evidence validation and GitHub review.

Architecture:

    GitHub event
       |
       +-- Push
       |     +-- Core Action
       |            +-- Git diff
       |            +-- Project context
       |            +-- Groq Structured Output
       |            +-- Quality / Security / Risk
       |            +-- Notion + Step Summary
       |
       +-- Pull Request
             +-- PR Review Action
                    +-- PR diff
                    +-- Groq Structured Output
                    +-- Finding validation
                    +-- Inline review comments
                    +-- Quality gate

## Trust boundaries

1. Repository code is treated as data during review.
2. AI output is untrusted until validated against a strict schema.
3. Findings must be anchored to evidence.
4. GitHub write permissions are limited to the PR workflow.
5. The PR workflow uses the pull_request event, not pull_request_target, by default.
6. Fork pull requests normally do not receive repository secrets, so the Groq
   review is skipped when GROQ_API_KEY is absent.

GitHub warns that privileged workflows must not check out and execute
untrusted pull request code. AI DevOps therefore does not execute the reviewed
project's build scripts as part of the PR review.

## AI boundary

Groq receives:

- repository identifier;
- selected project context;
- pull request metadata;
- bounded diff.

Groq does not receive:

- GitHub tokens;
- Notion tokens;
- repository secrets;
- arbitrary command output unless the workflow explicitly adds it.

## Review lifecycle

    diff
      |
      v
    structured AI review
      |
      v
    schema validation
      |
      v
    line-anchor validation
      |
      v
    GitHub review
      |
      v
    optional quality gate

An AI finding that cannot be mapped to an added line is not published as an
inline comment.

## Review decisions

The PR action supports:

- COMMENT: safest default.
- REQUEST_CHANGES: explicit opt-in for teams that want AI findings to block
  merge workflows.
- APPROVE: supported, but automatically downgraded to COMMENT when the AI
  identifies high-severity or high-risk findings.

## Extension points

Future providers can implement the same normalized review contract:

- summary;
- scores;
- risk;
- confidence;
- findings.

This keeps the GitHub publishing layer independent from a specific model.
