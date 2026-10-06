#!/usr/bin/env python3
"""Small dependency-free high-signal security scanner for AI DevOps itself."""
from __future__ import annotations
import json, os, re
from pathlib import Path

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "coverage", ".pytest_cache", "__pycache__"}
TEXT_EXTENSIONS = {".py",".js",".jsx",".ts",".tsx",".java",".kt",".go",".rs",".rb",".php",".cs",".cpp",".c",".h",".hpp",".yml",".yaml",".json",".toml",".ini",".cfg",".env",".sh",".ps1"}
PATTERNS = [
    ("HIGH", "Possível segredo hardcoded", re.compile(r"(?i)\b(api[_-]?key|secret|access[_-]?token|private[_-]?key)\b\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
    ("HIGH", "Possível chave privada PEM", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("HIGH", "Possível token GitHub", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("HIGH", "Possível token Slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("MEDIUM", "Execução dinâmica potencialmente perigosa em Python", re.compile(r"\b(?:eval|exec)\s*\(")),
    ("MEDIUM", "Shell com interpolação direta pode exigir validação", re.compile(r"\bos\.system\s*\(")),
    ("MEDIUM", "SQL construído por concatenação/interpolação", re.compile(r"(?i)(?:select|insert|update|delete)\b.{0,120}(?:\+|f['\"]|\.format\s*\(")),
]
def iter_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not any(part in SKIP_DIRS for part in path.parts):
            if path.suffix.lower() in TEXT_EXTENSIONS or path.name in {".env", "Dockerfile"}:
                yield path
def main():
    findings=[]
    for path in iter_files():
        try: lines=path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError: continue
        for number,line in enumerate(lines,1):
            for severity,title,pattern in PATTERNS:
                if pattern.search(line):
                    findings.append({"severity":severity,"file":str(path.relative_to(ROOT)),"line":number,"title":title,"evidence":"Pattern de alto sinal detectado; validação humana recomendada."})
    result={"scanner":"ai-devops-security-scan","findings":findings,"count":len(findings),"high":sum(x["severity"]=="HIGH" for x in findings),"medium":sum(x["severity"]=="MEDIUM" for x in findings)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if os.environ.get("FAIL_ON_SECURITY_FINDINGS","false").lower()=="true" and findings: raise SystemExit(2)
if __name__=="__main__": main()
