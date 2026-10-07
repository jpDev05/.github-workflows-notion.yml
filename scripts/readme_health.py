#!/usr/bin/env python3
from pathlib import Path
p=Path("README.md")
s=p.read_text(encoding="utf-8")
start="<!-- AI-DEVOPS-HEALTH:START -->"
end="<!-- AI-DEVOPS-HEALTH:END -->"
managed="""<!-- AI-DEVOPS-HEALTH:START -->
## 📊 AI DevOps Health

![AI DevOps Quality](docs/quality-badge.svg)

- **Review engine:** Structured Outputs + evidence-first analysis
- **Security:** deterministic scanner + CodeQL + SARIF
- **Tests:** Test Intelligence with workflow evidence
- **Architecture:** repository-local memory under `.ai-devops/`
- **Automation:** AI Fix proposals, changelog generation and quality history
- **Providers:** Groq and OpenAI-compatible endpoints

<!-- AI-DEVOPS-HEALTH:END -->"""
if start in s and end in s:
    a=s.index(start); b=s.index(end)+len(end)
    s=s[:a]+managed+s[b:]
else:
    s=s.rstrip()+"\n\n"+managed+"\n"
p.write_text(s,encoding="utf-8")
print("README health section updated.")
