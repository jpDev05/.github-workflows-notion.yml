#!/usr/bin/env python3
"""Generate a review-backed fix proposal as a validated unified diff."""
import json, os, urllib.request, urllib.error
from pathlib import Path

api_key=os.environ["GROQ_API_KEY"]
model=os.environ.get("GROQ_MODEL","openai/gpt-oss-20b")
file=os.environ.get("FIX_FILE","")
problem=os.environ.get("FIX_PROBLEM","")
evidence=os.environ.get("FIX_EVIDENCE","")
suggestion=os.environ.get("FIX_SUGGESTION","")
if not file or not problem: raise SystemExit("FIX_FILE and FIX_PROBLEM are required")
source=Path(file).read_text(encoding="utf-8",errors="replace")
schema={"type":"object","properties":{"summary":{"type":"string"},"patch":{"type":"string"},"tests":{"type":"array","items":{"type":"string"}}},"required":["summary","patch","tests"],"additionalProperties":False}
prompt=f"""You are generating a conservative code fix for a finding already identified by AI DevOps.
File: {file}
Problem: {problem}
Evidence: {evidence}
Suggested direction: {suggestion}
Return ONLY a unified diff for this file. Do not change unrelated behavior. Do not invent APIs.
Current file:
--- BEGIN ---
{source[:12000]}
--- END ---
"""
body={"model":model,"messages":[{"role":"system","content":"Produce a minimal, reviewable patch. Never include secrets. If the evidence is insufficient, return an empty patch."},{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":3000,"response_format":{"type":"json_schema","json_schema":{"name":"ai_fix","strict":True,"schema":schema}}}
req=urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",data=json.dumps(body).encode(),method="POST",headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"})
with urllib.request.urlopen(req,timeout=120) as response: result=json.loads(response.read().decode())
review=json.loads(result["choices"][0]["message"]["content"])
patch=review["patch"].strip()
Path("ai-fix.patch").write_text(patch+"\n",encoding="utf-8")
Path("ai-fix.md").write_text("# AI Fix Proposal\n\n"+review["summary"]+"\n\n## Tests suggested\n"+"\n".join("- "+x for x in review["tests"])+"\n",encoding="utf-8")
print("AI fix proposal generated.")
if not patch: raise SystemExit("No safe patch was generated.")
