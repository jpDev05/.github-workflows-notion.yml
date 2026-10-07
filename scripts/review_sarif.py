#!/usr/bin/env python3
"""Convert the AI DevOps review JSON into GitHub SARIF."""
import json, os
from pathlib import Path

src=Path(os.environ.get("AI_DEVOPS_REVIEW_JSON","ai-devops-review.json"))
out=Path(os.environ.get("AI_DEVOPS_SARIF","ai-devops.sarif"))
if not src.exists():
    raise SystemExit("Review JSON not found")
data=json.loads(src.read_text(encoding="utf-8"))
rules=[]
results=[]
for i,p in enumerate(data.get("problemas_encontrados",[]),1):
    level={"Alta":"error","Média":"warning","Baixa":"note"}.get(p.get("severidade"),"warning")
    rule_id=f"AI{str(i).zfill(3)}"
    rules.append({"id":rule_id,"name":p.get("problema","AI DevOps finding"),"shortDescription":{"text":p.get("problema","AI DevOps finding")}})
    result={"ruleId":rule_id,"level":level,"message":{"text":p.get("evidencia","Evidence-backed AI finding")}}
    file=p.get("arquivo")
    line=str(p.get("linha",""))
    if file and file!="N/A":
        loc={"physicalLocation":{"artifactLocation":{"uri":file}}}
        try: loc["physicalLocation"]["region"]={"startLine":max(1,int(line))}
        except (TypeError,ValueError): pass
        result["locations"]=[loc]
    results.append(result)
sarif={"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json","runs":[{"tool":{"driver":{"name":"AI DevOps","version":"3.0.0","rules":rules}},"results":results}]}
out.write_text(json.dumps(sarif,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Wrote {out} with {len(results)} findings")
