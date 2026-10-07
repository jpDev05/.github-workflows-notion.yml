#!/usr/bin/env python3
import json, os
from pathlib import Path
history=json.loads(Path("docs/quality-history.json").read_text(encoding="utf-8"))
if not history: raise SystemExit("No quality history")
e=history[-1]
q=float(e.get("quality",0))
label="AI DevOps Quality"
text=f"{q:.1f}/10"
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="170" height="20" role="img" aria-label="{label}: {text}">
<linearGradient id="g" x2="0" y2="100%"><stop offset="0" stop-color="#444"/><stop offset="1" stop-color="#222"/></linearGradient>
<rect width="170" height="20" rx="3" fill="#555"/><rect x="92" width="78" height="20" rx="3" fill="url(#g)"/>
<text x="46" y="14" fill="#fff" font-family="Verdana" font-size="11" text-anchor="middle">{label}</text>
<text x="131" y="14" fill="#fff" font-family="Verdana" font-size="11" text-anchor="middle">{text}</text>
</svg>'''
Path("docs/quality-badge.svg").write_text(svg,encoding="utf-8")
print(f"Badge generated: {text}")
