#!/usr/bin/env python3
"""Generate a concise changelog from conventional commit messages."""
import os, subprocess
from pathlib import Path
limit=int(os.environ.get("CHANGELOG_LIMIT","50"))
try:
    raw=subprocess.check_output(["git","log",f"-{limit}","--pretty=format:%h%x09%s"],text=True)
except subprocess.CalledProcessError:
    raw=""
sections={"feat":"Added","fix":"Fixed","security":"Security","perf":"Performance","docs":"Documentation","refactor":"Changed","test":"Tests","chore":"Maintenance"}
groups={v:[] for v in sections.values()}
for line in raw.splitlines():
    if "\t" not in line: continue
    sha,msg=line.split("\t",1)
    key=msg.split(":",1)[0].lower()
    if key in sections: groups[sections[key]].append(f"- {msg} ({sha})")
lines=["# Changelog","","Generated from recent conventional commits.",""]
for name,items in groups.items():
    if items: lines += [f"## {name}","",*items,""]
Path("CHANGELOG.generated.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("Generated CHANGELOG.generated.md")
