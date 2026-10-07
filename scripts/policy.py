"""Minimal dependency-free parser for the AI DevOps repository policy file.

The supported schema intentionally covers the stable public configuration surface
without requiring PyYAML in consuming repositories.
"""

import os
import re


DEFAULT_POLICY = {
    "review": {
        "language": "pt-BR",
        "profile": "professional",
        "max_inline_findings": 8,
        "min_score": 0,
        "fail_on_high_risk": False,
    },
    "security": {
        "evidence_first": True,
        "report_hypotheses_as_findings": False,
    },
    "pull_request": {
        "event": "COMMENT",
    },
    "paths": {
        "ignore": [],
    },
}


def _scalar(value):
    value = value.strip()

    if not value:
        return ""

    if value.startswith(("'", '"')) and value.endswith(value[0]):
        return value[1:-1]

    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_policy(path=None):
    policy = {
        "review": dict(DEFAULT_POLICY["review"]),
        "security": dict(DEFAULT_POLICY["security"]),
        "pull_request": dict(DEFAULT_POLICY["pull_request"]),
        "paths": {"ignore": list(DEFAULT_POLICY["paths"]["ignore"])},
    }

    path = path or os.environ.get(
        "AI_DEVOPS_POLICY_FILE",
        ".ai-devops.yml",
    )

    if not os.path.isfile(path):
        return policy

    section = None
    subsection = None

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip()
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip(" "))

            if indent == 0 and stripped.endswith(":"):
                section = stripped[:-1].strip()
                subsection = None
                continue

            if indent == 0 and ":" in stripped:
                key, value = stripped.split(":", 1)
                if key.strip() == "version":
                    continue
                section = key.strip()
                subsection = None
                continue

            if indent == 2 and stripped.endswith(":"):
                subsection = stripped[:-1].strip()
                continue

            if indent == 2 and ":" in stripped and section:
                key, value = stripped.split(":", 1)
                target = policy.setdefault(section, {})
                target[key.strip()] = _scalar(value)
                continue

            if indent == 4 and ":" in stripped and section and subsection:
                key, value = stripped.split(":", 1)
                target = policy.setdefault(section, {}).setdefault(
                    subsection, {}
                )
                target[key.strip()] = _scalar(value)
                continue

            if indent == 4 and stripped.startswith("- ") and section == "paths":
                policy.setdefault("paths", {}).setdefault("ignore", []).append(
                    _scalar(stripped[2:])
                )

    return policy


def review_config(policy):
    return policy.get("review", {})


def security_config(policy):
    return policy.get("security", {})


def pr_config(policy):
    return policy.get("pull_request", {})


def ignored_paths(policy):
    return policy.get("paths", {}).get("ignore", [])
