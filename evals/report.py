#!/usr/bin/env python3
"""Summarize eval results: python3 evals/report.py [results.json ...]"""
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"

files = sys.argv[1:] or sorted(glob.glob(str(RESULTS / "*.json")))
rows = []
for f in files:
    try:
        rows.extend(json.loads(Path(f).read_text()))
    except Exception as e:
        print(f"skip {f}: {e}")

by_model = defaultdict(list)
for r in rows:
    by_model[r["model"]].append(r)

print(f"{'model':45s} {'task':4s} {'ok':3s} {'calls':5s} {'tools':30s} {'tok':>10s} {'time':>6s}")
print("-" * 110)
for model, rs in sorted(by_model.items()):
    for r in sorted(rs, key=lambda x: (x["task"], x["run"])):
        ok = "PASS" if r["correct"] else "FAIL"
        tools = ",".join(r.get("tools_used", []))[:30]
        tok = r.get("tokens", {})
        toks = f"{tok.get('total', 0):,}" if tok else "-"
        print(
            f"{model[:45]:45s} {r['task']:4s} {ok:3s} {r.get('tool_calls', 0):<5} "
            f"{tools:30s} {toks:>10s} {r.get('duration_s', 0):>5.0f}s"
        )
    passed = sum(1 for r in rs if r["correct"])
    avg_calls = sum(r.get("tool_calls", 0) for r in rs) / max(1, len(rs))
    avg_tok = sum(r.get("tokens", {}).get("total", 0) for r in rs) / max(1, len(rs))
    print(f"  -> {model}: {passed}/{len(rs)} correct, avg {avg_calls:.1f} calls, avg {avg_tok:,.0f} tokens")
    print()
