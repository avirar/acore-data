#!/usr/bin/env python3
"""Capture MCP tool output sizes (baseline vs after-change comparisons).

Run:
  python3 scripts/capture_output_sizes.py /tmp/opencode/baseline
  python3 scripts/capture_output_sizes.py /tmp/opencode/after
  python3 scripts/capture_output_sizes.py --compare /tmp/opencode/baseline /tmp/opencode/after

Each scenario starts a fresh server process (server.py over stdio JSON-RPC)
so the server always reflects the current tree.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

WORKDIR = Path(__file__).resolve().parent.parent
ENV = {**os.environ, "PYTHONPATH": str(WORKDIR)}

# Prefer the repo venv (has pymysql) so probe conditions match the live server.
_VENV_PY = WORKDIR / ".venv" / "bin" / "python3"
PY = str(_VENV_PY) if _VENV_PY.exists() else sys.executable

SCENARIOS = {
    "query_spell_118": {
        "tool": "query",
        "args": {"name": "Spell", "id": 118, "limit": 1},
    },
    "query_quest_murloc_fields": {
        "tool": "query",
        "args": {
            "name": "quest_template",
            "filter": {"LogTitle": {"$ilike": "%murloc%"}},
            "fields": ["LogTitle", "MinLevel"],
            "limit": 3,
        },
    },
    "query_map_filter_name": {
        "tool": "query",
        "args": {"name": "Map", "filter": {"name[0]": "Eastern Kingdoms"}},
    },
    "query_creature_100": {
        "tool": "query",
        "args": {"name": "creature_template", "id": 100, "limit": 1},
    },
    "query_bad_store": {
        "tool": "query",
        "args": {"name": "BogusStoreName"},
    },
    "query_quest_46_links": {
        "tool": "query",
        "args": {"name": "quest_template", "id": 46, "limit": 1, "links": True},
    },
    "lookup_spellentry_schema": {
        "tool": "lookup",
        "args": {"query": "SpellEntry", "detail": "schema"},
    },
    "lookup_quests_summary": {
        "tool": "lookup",
        "args": {"query": "quest_template", "detail": "summary"},
    },
    "list_dbc_backed": {
        "tool": "list",
        "args": {"category": "dbc_backed"},
    },
}


def call_once(tool, args):
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "size-probe", "version": "0"},
        },
    }
    call = {
        "jsonrpc": "2.0",
        "id": 99,
        "method": "tools/call",
        "params": {"name": tool, "arguments": args},
    }
    stdin_data = json.dumps(init) + "\n" + json.dumps(call) + "\n"
    proc = subprocess.run(
        [PY, "server.py"],
        input=stdin_data,
        capture_output=True,
        text=True,
        cwd=WORKDIR,
        env=ENV,
        timeout=90,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    # The tools/call response is the line containing id 99
    for ln in lines:
        try:
            msg = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == 99:
            return msg
    raise RuntimeError(
        f"no tools/call response; stderr tail:\n{proc.stderr[-2000:]}"
    )


def capture(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for sc_name, sc in SCENARIOS.items():
        try:
            msg = call_once(sc["tool"], sc["args"])
            if "error" in msg:
                text = json.dumps(msg["error"])
                is_err = True
            else:
                result = msg["result"]
                text = result["content"][0]["text"]
                is_err = bool(result.get("isError"))
            body = text if is_err else text
            size = len(body.encode("utf-8"))
            summary[sc_name] = {"bytes": size, "isError": is_err}
            (out_dir / f"{sc_name}.json").write_text(
                json.dumps({"args": sc["args"], "mcp": msg}, indent=2)
            )
            print(f"  {sc_name:28s} {size:>8,} bytes  isError={is_err}")
        except Exception as e:
            summary[sc_name] = {"bytes": None, "error": str(e)[:200]}
            print(f"  {sc_name:28s} ERROR: {str(e)[:120]}")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    total = sum(v.get("bytes") or 0 for v in summary.values())
    print(f"  TOTAL {len(summary)} scenarios: {total:,} bytes")
    return summary


def compare(before: Path, after: Path):
    a = json.loads((before / "summary.json").read_text())
    b = json.loads((after / "summary.json").read_text())
    rows = []
    for k in a:
        av = a[k].get("bytes")
        bv = b.get(k, {}).get("bytes")
        if av and bv:
            delta = ((bv - av) / av) * 100
            rows.append((k, av, bv, delta))
        else:
            rows.append((k, av, bv, float("nan")))
    rows.sort(key=lambda r: -(r[1] or 0))
    print(f"{'scenario':28s} {'before':>10s} {'after':>10s} {'delta':>8s}")
    for k, av, bv, delta in rows:
        d = f"{delta:+.0f}%" if delta == delta else "  n/a"
        print(f"{k:28s} {av or 0:>10,} {bv or 0:>10,} {d:>8s}")
    ta = sum(r[1] or 0 for r in rows)
    tb = sum(r[2] or 0 for r in rows)
    if ta:
        print(f"{'TOTAL':28s} {ta:>10,} {tb:>10,} {((tb-ta)/ta*100):+.0f}%")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/opencode/baseline")
        capture(out)
