"""Policy loader bundled with the PR action."""
from __future__ import annotations
import os
DEFAULT={"review":{"min_score":0,"fail_on_high_risk":False,"max_inline_findings":8},"pull_request":{"event":"COMMENT"}}
def _scalar(v):
    v=v.strip()
    if v[:1] in ("'","\"") and v[-1:]==v[:1]: return v[1:-1]
    if v.lower()=="true": return True
    if v.lower()=="false": return False
    try: return float(v) if "." in v else int(v)
    except ValueError: return v
def load(path=None):
    p={k:dict(v) for k,v in DEFAULT.items()}
    path=path or os.environ.get("AI_DEVOPS_POLICY_FILE",".ai-devops.yml")
    if not os.path.isfile(path): return p
    section=None
    for raw in open(path,encoding="utf-8",errors="replace"):
        s=raw.strip(); indent=len(raw)-len(raw.lstrip(" "))
        if not s or s.startswith("#"): continue
        if indent==0 and s.endswith(":"): section=s[:-1]; p.setdefault(section,{}); continue
        if indent==2 and ":" in s and section:
            k,v=s.split(":",1); p.setdefault(section,{})[k.strip()]=_scalar(v)
    return p
