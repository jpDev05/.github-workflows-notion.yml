#!/usr/bin/env python3
"""Detect and execute an obvious test command for common projects."""
from __future__ import annotations
import json, os, subprocess
from pathlib import Path
ROOT=Path(os.environ.get("GITHUB_WORKSPACE",".")).resolve()
def choose():
    if (ROOT/"pytest.ini").exists() or (ROOT/"pyproject.toml").exists() or (ROOT/"tests").is_dir(): return ["python","-m","pytest","-q"]
    if (ROOT/"package.json").exists(): return ["npm","test"]
    if (ROOT/"pom.xml").exists(): return ["./mvnw","test"] if (ROOT/"mvnw").exists() else ["mvn","test"]
    if (ROOT/"gradlew").exists(): return ["./gradlew","test"]
    if (ROOT/"build.gradle").exists() or (ROOT/"build.gradle.kts").exists(): return ["gradle","test"]
    if (ROOT/"go.mod").exists(): return ["go","test","./..."]
    if (ROOT/"Cargo.toml").exists(): return ["cargo","test"]
    return None
def main():
    command=choose()
    if command is None:
        print(json.dumps({"status":"not_detected","command":None,"exit_code":None})); return
    print("🧪 Executando:", " ".join(command))
    code=subprocess.run(command,cwd=ROOT,text=True).returncode
    result={"status":"passed" if code==0 else "failed","command":command,"exit_code":code}
    print(json.dumps(result,ensure_ascii=False))
    output=os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output,"a",encoding="utf-8") as f:
            f.write(f"status={result['status']}\nexit-code={code}\n")
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as f:
            f.write("## Test Intelligence\\n\\n")
            f.write(f"- Status: **{result['status']}**\\n")
            f.write(f"- Command: {' '.join(command)}\\n")
            f.write(f"- Exit code: `{code}`\\n")
    raise SystemExit(code)
if __name__=="__main__": main()
