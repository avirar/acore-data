#!/usr/bin/env python3
"""LLM tool-calling eval for the acore-data MCP server via `opencode run`.

Each task is run with `opencode run --format json` in a clean temp dir; the
global opencode config provides the acore_data MCP server. We parse the JSON
event stream, extract tool calls + final answer, and score against known
deterministic answers.

Usage:
  python3 evals/run_eval.py --model vllm/Qwen3.8-27B-NVFP4 [--tasks T1 T2] [--runs 1]
  python3 evals/report.py   # pretty summary of results
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals" / "results"
def _opencode_db_path() -> Path:
    env = os.environ.get("OPENCODE_DB", "")
    p = Path(env)
    if p.is_absolute():
        return p if p.exists() else Path.home() / ".local/share/opencode" / p.name
    # bare filename (relative to opencode's storage dir)
    cand = Path.home() / ".local/share/opencode" / p.name
    return cand if cand.exists() else Path.home() / ".local/share/opencode" / "opencode-production.db"


OPENCODE_DB = _opencode_db_path()

TASKS = {
    "T1": {
        "prompt": "What are the base level and mechanic of spell 118 (Polymorph) in this WotLK world?",
        # expected: BaseLevel 8, Mechanic 17
        "check": lambda a: re.search(r"\b8\b", a) and re.search(r"\b17\b", a),
        "note": "DBC single lookup (query Spell id=118)",
    },
    "T2": {
        "prompt": "Item entry 118 (Minor Healing Potion) references a spell via the spellid_1 column of item_template. What is the name of that spell?",
        # expected: Healing Potion (spell 439)
        "check": lambda a: re.search(r"healing\s+potion", a, re.I),
        "note": "SQL -> DBC multi-hop (item_template.spellid_1 -> Spell)",
    },
    "T3": {
        "prompt": "How many creature spawns with id 32820 exist in map 0, and what is the template name of that creature?",
        # expected: 3125 spawns, Wild Turkey
        "check": lambda a: re.search(r"3[\s\u00a0\u202f]?125", a) and re.search(r"wild\s+turkey", a, re.I),
        "note": "SQL count + creature_template join",
    },
    "T4": {
        "prompt": "Use the query tool to get the 'Name' field of spell 118. (The field may be named differently - find the right one.)",
        # expected: Polymorph
        "check": lambda a: re.search(r"polymorph", a, re.I),
        "note": "strict field-error recovery (Name -> spellname)",
    },
}


def parse_stream(raw: str):
    """Extract sessionID from the --format json event stream."""
    sid = None
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = ev.get("sessionID") or sid
        if sid:
            break
    return sid


def read_session_parts(session_id: str):
    """Read the full structured record from opencode's sqlite store.

    The --format json stream does not flush the final text part, so the
    database is the source of truth: assistant text parts, tool parts with
    input/status/error, and token usage from step-finish parts.
    """
    if not OPENCODE_DB.exists():
        return [], "", {}, []
    con = sqlite3.connect(OPENCODE_DB)
    cur = con.cursor()
    cur.execute(
        "SELECT p.data FROM part p JOIN message m ON m.id = p.message_id "
        "WHERE p.session_id = ? AND json_extract(m.data, '$.role') = 'assistant' "
        "ORDER BY p.time_created",
        (session_id,),
    )
    tools, texts, errors = [], [], []
    tokens = {"input": 0, "output": 0, "reasoning": 0, "total": 0}
    for (d,) in cur.fetchall():
        try:
            p = json.loads(d)
        except json.JSONDecodeError:
            continue
        ptype = p.get("type")
        if ptype == "text":
            t = (p.get("text") or "").strip()
            if t:
                texts.append(t)
        elif ptype == "tool":
            state = p.get("state") or {}
            tools.append(
                {
                    "tool": p.get("tool"),
                    "input": state.get("input"),
                    "error": state.get("status") == "error",
                }
            )
            if state.get("status") == "error":
                errors.append(str(state.get("error"))[:300])
        elif ptype == "step-finish":
            tk = p.get("tokens") or {}
            for k in tokens:
                tokens[k] += tk.get(k, 0) or 0
    con.close()
    return tools, "\n\n".join(texts).strip(), tokens, errors


def run_one(model: str, task_id: str, idx: int, timeout: int = 300) -> dict:
    task = TASKS[task_id]
    workdir = Path(f"/tmp/acoredata-eval-{task_id}-{idx}")
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    t0 = time.time()
    try:
        proc = subprocess.run(
            ["opencode", "run", "--model", model, "--format", "json", task["prompt"]],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        dur = time.time() - t0
        sid = parse_stream(proc.stdout)
        tools, answer, tokens, errors = ([], "", {}, [])
        if sid:
            tools, answer, tokens, errors = read_session_parts(sid)
        correct = bool(answer) and bool(task["check"](answer))
        result = {
            "model": model,
            "task": task_id,
            "run": idx,
            "session_id": sid,
            "correct": correct,
            "answer_tail": answer[-400:],
            "tool_calls": len(tools),
            "tools_used": sorted({t["tool"] for t in tools if t["tool"]}),
            "tool_inputs": [
                {"tool": t["tool"], "input": t["input"], "error": t["error"]}
                for t in tools
            ],
            "error_messages": errors,
            "tokens": tokens,
            "duration_s": round(dur, 1),
            "exit_code": proc.returncode,
            "stderr_tail": (proc.stderr or "")[-300:],
        }
    except subprocess.TimeoutExpired:
        result = {
            "model": model, "task": task_id, "run": idx, "correct": False,
            "error": f"timeout after {timeout}s", "duration_s": timeout,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tasks", nargs="*", default=list(TASKS))
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    all_results = []
    for t in args.tasks:
        for i in range(1, args.runs + 1):
            r = run_one(args.model, t, i, args.timeout)
            all_results.append(r)
            tag = "PASS" if r["correct"] else "FAIL"
            print(
                f"[{tag}] {args.model} {t} run{i}: "
                f"{r.get('tool_calls', '?')} tool calls, "
                f"{r.get('duration_s', '?')}s, tools={r.get('tools_used', [])}",
                flush=True,
            )
            if r.get("error_messages"):
                for e in r["error_messages"][:2]:
                    print(f"       err: {e[:150]}", flush=True)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = RESULTS / f"{re.sub(r'[^A-Za-z0-9]+', '_', args.model)}-{stamp}.json"
    out.write_text(json.dumps(all_results, indent=2))
    print(f"\nsaved -> {out}")
    passed = sum(1 for r in all_results if r["correct"])
    print(f"score: {passed}/{len(all_results)}")


if __name__ == "__main__":
    main()
