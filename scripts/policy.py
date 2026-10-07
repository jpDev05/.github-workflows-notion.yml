"""Small dependency-free YAML subset loader for AI DevOps policy files."""
from __future__ import annotations
import os

DEFAULT_POLICY = {
    "review": {"language":"pt-BR","profile":"professional","min_score":0,"fail_on_high_risk":False,"max_inline_findings":8},
    "pull_request": {"event":"COMMENT"},
    "security": {"evidence_first":True,"sarif":True},
    "tests": {"enabled":True},
    "architecture": {"enabled":True},
    "history": {"enabled":True},
}

def _scalar(value):
    value=value.strip()
    if not value: return ""
    if value[:1] in ("'", '"') and value[-1:]==value[:1]: return value[1:-1]
    low=value.lower()
    if low=="true": return True
    if low=="false": return False
    if low in ("null","~"): return None
    try: return float(value) if "." in value else int(value)
    except ValueError: return value

def load_policy(path=None):
    policy={k:(dict(v) if isinstance(v,dict) else v) for k,v in DEFAULT_POLICY.items()}
    path=path or os.environ.get("AI_DEVOPS_POLICY_FILE",".ai-devops.yml")
    if not os.path.isfile(path): return policy
    section=None
    with open(path,encoding="utf-8",errors="replace") as fh:
        for raw in fh:
            line=raw.rstrip()
            s=line.strip()
            if not s or s.startswith("#"): continue
            indent=len(line)-len(line.lstrip(" "))
            if indent==0 and s.endswith(":"):
                section=s[:-1].strip(); policy.setdefault(section,{}); continue
            if indent==2 and ":" in s and section:
                k,v=s.split(":",1); policy.setdefault(section,{})[k.strip()]=_scalar(v)
    return policy
