# 🤖 AI DevOps

**AI-powered code review, security analysis, quality scoring and technical documentation for GitHub.**

AI DevOps turns a normal GitHub repository into an automated engineering review pipeline:

```text
Commit / Push
     │
     ▼
GitHub Actions
     │
     ▼
Project Context + Git Diff
     │
     ▼
Groq GPT-OSS 20B
     │
     ├── 🧠 Technical review
     ├── 🐛 Bug detection
     ├── 🔐 Security analysis
     ├── 🧪 Test recommendations
     ├── ⚡ Performance analysis
     ├── ♻️ Regression analysis
     └── 📊 Quality scoring
     │
     ▼
Strict JSON Schema validation
     │
     ├── GitHub Step Summary
     └── Notion documentation
```

## ✨ Why AI DevOps?

The goal is not to make an AI that sounds intelligent.

The goal is to build an AI reviewer that is:

- **evidence-first**
- **deterministic**
- **structured**
- **security-aware**
- **explicit about uncertainty**
- **resistant to hallucinated findings**
- **easy to install**
- **configurable**
- **provider-friendly**

The review uses Groq Structured Outputs with a strict JSON Schema. The current default model is `openai/gpt-oss-20b`, which supports strict structured outputs on Groq.

## 🚀 Quick start

### 1. Add the secrets

In your repository:

**Settings → Secrets and variables → Actions**

Create:

- `GROQ_API_KEY`
- `NOTION_TOKEN` — only required if Notion synchronization is enabled.

### 2. Create the workflow

Create:

`.github/workflows/ai-devops.yml`

```yaml
name: AI DevOps

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: AI DevOps Review
        uses: jpDev05/.github-workflows-notion.yml@v1
        with:
          groq-api-key: ${{ secrets.GROQ_API_KEY }}
          notion-token: ${{ secrets.NOTION_TOKEN }}
          notion-enabled: "true"
```

## 🔐 Security-first defaults

AI DevOps never asks the model to execute repository code.

The model receives:

- commit metadata;
- changed filenames;
- Git diff;
- selected project documentation/configuration;
- explicit review rules.

The action itself only reads the repository unless the consuming workflow grants additional permissions.

For public repositories, do **not** use `pull_request_target` merely to expose secrets to untrusted fork code. Prefer safe event designs and least-privilege permissions.

## 🧠 Evidence-first review

Every finding is expected to contain:

```json
{
  "severidade": "Alta",
  "problema": "Descrição do problema",
  "arquivo": "src/auth.py",
  "linha": "42",
  "evidencia": "Trecho ou comportamento sustentado pelo diff",
  "sugestao": "Correção recomendada",
  "confianca": 0.96
}
```

If there is not enough evidence, the reviewer should say so instead of inventing a vulnerability.

## 🐍 Python f-string protection

The reviewer has an explicit rule for a common false positive:

```python
prompt = f"""
{{"name": "example"}}
"""
```

Inside a Python f-string, `{{` and `}}` can intentionally represent literal braces.

AI DevOps must not classify them as Jinja or as a syntax error without evidence from the actual code.

## 📊 Quality gate

You can optionally fail the workflow when quality falls below a threshold:

```yaml
- name: AI DevOps Review
  uses: jpDev05/.github-workflows-notion.yml@v1
  with:
    groq-api-key: ${{ secrets.GROQ_API_KEY }}
    notion-token: ${{ secrets.NOTION_TOKEN }}
    min-score: "7"
```

Or fail on high risk:

```yaml
fail-on-high-risk: "true"
```

Both controls are disabled by default.

## ⚙️ Inputs

| Input | Default | Description |
|---|---|---|
| `groq-api-key` | required | Groq API key |
| `notion-token` | empty | Notion integration token |
| `notion-data-source` | configured default | Notion data source ID |
| `groq-model` | `openai/gpt-oss-20b` | Groq model |
| `notion-enabled` | `true` | Enable Notion synchronization |
| `min-score` | `0` | Minimum quality/security/maintainability score |
| `fail-on-high-risk` | `false` | Fail on High risk |

## 📤 Outputs

The action exposes:

- `quality`
- `security`
- `maintainability`
- `risk`
- `confidence`

Example:

```yaml
- name: AI DevOps Review
  id: review
  uses: jpDev05/.github-workflows-notion.yml@v1
  with:
    groq-api-key: ${{ secrets.GROQ_API_KEY }}
    notion-enabled: "false"

- name: Print result
  run: |
    echo "Quality: ${{ steps.review.outputs.quality }}"
    echo "Security: ${{ steps.review.outputs.security }}"
    echo "Risk: ${{ steps.review.outputs.risk }}"
```

## 🧠 Pull Request Intelligence

AI DevOps v2 adds a dedicated PR review action that can:

- analyze the pull request diff with Groq Structured Outputs;
- publish a professional review directly in the PR;
- create inline findings only on verified added lines;
- expose quality, security, maintainability, risk and confidence;
- use COMMENT, REQUEST_CHANGES or guarded APPROVE;
- enforce an optional quality gate.

Example:

```yaml
name: AI DevOps PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    env:
      GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - uses: jpDev05/.github-workflows-notion.yml/pr-review@v2
        with:
          groq-api-key: ${{ secrets.GROQ_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          review-event: COMMENT
```

Use `REQUEST_CHANGES` only when your team explicitly wants the AI review to
participate in merge blocking. `APPROVE` is guarded and is downgraded to
`COMMENT` when high-risk or high-severity findings exist.

### 🔒 Fork security

The default PR workflow uses `pull_request` and least-privilege permissions.
GitHub does not provide repository secrets to workflows triggered by fork PRs
under normal policy, so the example skips the Groq review when the key is not
available. Do not switch this to `pull_request_target` just to expose secrets
to untrusted code.

### ⚙️ Repository policy

Copy `config/.ai-devops.yml` to the root of a consuming repository as
`.ai-devops.yml` and adapt the review policy for the project.

## 📚 Notion

When enabled, AI DevOps creates or updates the project's Notion page with:

- executive summary;
- technical explanation;
- impact;
- compatibility;
- regression risk;
- performance;
- security;
- tests;
- improvements;
- evidence-based findings;
- quality scores;
- confidence;
- changed files;
- commit statistics.

## 🏗️ Architecture

The product now has separate commit and pull-request automation surfaces.

See the detailed trust boundaries and review lifecycle in `docs/ARCHITECTURE.md`.

```text
Push → Core Action → Groq → Scores → Step Summary + Notion

PR   → PR Review Action → Groq → Finding validation → GitHub review
```
## 🛣️ Roadmap

### v1 — Foundation
- [x] GitHub Actions
- [x] Groq integration
- [x] Notion synchronization
- [x] Structured AI review
- [x] Evidence-first rules
- [x] Quality scoring
- [x] GitHub Step Summary

### v2 — Engineering Platform
- [x] Pull Request review
- [x] Inline findings
- [x] COMMENT / REQUEST_CHANGES / guarded APPROVE
- [x] PR quality gate
- [x] Architecture documentation
- [x] Repository policy template
- [ ] Test execution evidence
- [ ] Repository architecture memory
- [ ] Changelog automation
- [ ] README automation
- [ ] More output providers

### v3 — Open Source Platform
- [ ] Multiple AI providers
- [ ] Versioned review policies
- [ ] Review profiles
- [ ] Dashboard
- [ ] GitHub Marketplace publication
## 🤝 Contributing

Pull requests are welcome.

When changing the reviewer engine:

1. preserve evidence-first behavior;
2. avoid adding unsupported assumptions;
3. keep secrets out of logs;
4. maintain strict structured output;
5. add or update documentation for new inputs.

## 📄 License

MIT — see [LICENSE](LICENSE).
