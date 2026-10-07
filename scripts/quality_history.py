#!/usr/bin/env python3
import json, os
from pathlib import Path

path=Path(os.environ.get("AI_DEVOPS_HISTORY_FILE","docs/quality-history.json"))
path.parent.mkdir(parents=True,exist_ok=True)
try:
    history=json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
except (json.JSONDecodeError,OSError):
    history=[]
entry={
    "sha":os.environ.get("COMMIT_SHA",""),
    "date":os.environ.get("COMMIT_DATE",""),
    "repository":os.environ.get("REPOSITORY",""),
    "quality":float(os.environ.get("QUALITY","0") or 0),
    "security":float(os.environ.get("SECURITY","0") or 0),
    "maintainability":float(os.environ.get("MAINTAINABILITY","0") or 0),
    "risk":os.environ.get("RISK",""),
    "confidence":float(os.environ.get("CONFIDENCE","0") or 0),
}
history=[x for x in history if x.get("sha")!=entry["sha"]]
history.append(entry)
history=history[-200:]
path.write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Recorded quality history: {entry['sha']}")
