"""config tool: mod-playerbots configuration index.

Indexes the mod's playerbots.conf.dist (setting -> default value + line)
and the C++ code that reads each key (GetOption<...>("Key", default)
call sites) in a single cached pass. Answers the recurring
"what does this setting do / what's its default / where is it used"
questions without reading 900-line conf files or grepping the mod by
hand. The mod (and its conf) are optional - absence is a clean error.

Environment overrides:
  PLAYERBOTS_ROOT  - mod-playerbots source root
                     (default: /root/azerothcore-wotlk/modules/mod-playerbots)
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

_MOD_ROOT_DEFAULT = "/root/azerothcore-wotlk/modules/mod-playerbots"
_CONF_REL = os.path.join("conf", "playerbots.conf.dist")
_GETOPT_RE = re.compile(r'GetOption\s*<\s*[^>]*>\s*\(\s*"([^"]+)"')
_MAX_CODE_REFS = 5
_MAX_RESULTS = 50


def _mod_root() -> str:
    return os.environ.get("PLAYERBOTS_ROOT", _MOD_ROOT_DEFAULT)


class _ConfigIndex:
    """One-pass index of conf settings + code call sites."""

    def __init__(self):
        self.available = False
        self.note = ""
        self.conf_path = ""
        # key -> {"default": str, "line": int}
        self.settings: Dict[str, Dict[str, Any]] = {}
        # key -> [{"file": str, "line": int, "code": str}]
        self.code_refs: Dict[str, List[Dict[str, Any]]] = {}

    def build(self) -> None:
        root = _mod_root()
        conf_path = os.path.join(root, _CONF_REL)
        if not os.path.isfile(conf_path):
            self.note = (
                f"mod-playerbots conf not found at {conf_path} - is the mod "
                f"installed? Set PLAYERBOTS_ROOT to the mod-playerbots source "
                f"root if it lives elsewhere."
            )
            return
        self.conf_path = conf_path

        # ---- conf settings --------------------------------------------------
        try:
            with open(conf_path, "r", encoding="utf-8", errors="replace") as fh:
                for lineno, raw in enumerate(fh, 1):
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    self.settings[key.strip()] = {
                        "default": val.strip(),
                        "line": lineno,
                    }
        except OSError as e:
            self.note = f"could not read {conf_path}: {e}"
            return

        # ---- code call sites (single pass over src/) ------------------------
        src_dir = os.path.join(root, "src")
        refs: Dict[str, List[Dict[str, Any]]] = {}
        if os.path.isdir(src_dir):
            for dirpath, _dirnames, filenames in os.walk(src_dir):
                for fn in filenames:
                    if not fn.endswith((".cpp", ".h", ".cc")):
                        continue
                    path = os.path.join(dirpath, fn)
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="replace") as fh:
                            for lineno, line in enumerate(fh, 1):
                                for m in _GETOPT_RE.finditer(line):
                                    key = m.group(1)
                                    lst = refs.setdefault(key, [])
                                    if len(lst) < _MAX_CODE_REFS:
                                        lst.append({
                                            "file": os.path.relpath(path, root),
                                            "line": lineno,
                                            "code": line.strip()[:200],
                                        })
                    except OSError:
                        continue
        self.code_refs = refs
        self.available = True

    def summary(self) -> Dict[str, Any]:
        prefixes: Dict[str, int] = {}
        for k in self.settings:
            p = k.split(".")[0]
            prefixes[p] = prefixes.get(p, 0) + 1
        return {
            "conf_file": self.conf_path,
            "setting_count": len(self.settings),
            "code_ref_count": len(self.code_refs),
            "prefixes": dict(sorted(prefixes.items(),
                                    key=lambda kv: -kv[1])),
        }


def config_tools(server) -> Dict[str, Any]:
    args = server.args or {}

    # (re)build when the environment says the mod moved
    key = args.get("key")
    search = args.get("search")
    force = bool(args.get("rebuild"))

    # (re)build when forced, first call, or a previous failed build
    need_build = bool(args.get("rebuild")) or not hasattr(server, "_config_index")
    if need_build:
        server._config_index = _ConfigIndex()
    idx: _ConfigIndex = server._config_index
    if need_build or not idx.available:
        idx.build()

    if not idx.available:
        return {"error": idx.note or "mod-playerbots config index unavailable.",
                "isError": True}

    # ---- single key ---------------------------------------------------------
    if isinstance(key, str) and key:
        entry = idx.settings.get(key)
        if entry is None:
            import difflib
            close = difflib.get_close_matches(key, idx.settings.keys(), n=10)
            return {
                "error": f"Setting '{key}' not found in playerbots.conf.dist.",
                **({"did_you_mean": close} if close else {}),
                "isError": True,
            }
        refs = idx.code_refs.get(key, [])
        out: Dict[str, Any] = {
            "key": key,
            "default": entry["default"],
            "conf_line": entry["line"],
            "code_refs": refs,
            "metadata": {
                "conf_file": idx.conf_path,
                "note": "default is the conf.dist value; code refs show where "
                        "the key is read (type + fallback default in C++).",
            },
        }
        if not refs:
            out["metadata"]["note"] += (
                " No GetOption call site found - the key may be read via a "
                "different API or be dead."
            )
        return out

    # ---- search / summary ----------------------------------------------------
    if isinstance(search, str) and search:
        s = search.lower()
        hits = []
        for k, v in idx.settings.items():
            if s in k.lower():
                hits.append({"key": k, "default": v["default"],
                             "line": v["line"]})
        hits.sort(key=lambda h: h["key"])
        return {
            "search": search,
            "match_count": len(hits),
            "settings": hits[:_MAX_RESULTS],
            "metadata": {
                "note": f"case-insensitive substring match on key names; "
                        f"capped at {_MAX_RESULTS}."
                        + (" Use key=... for details + code refs." if hits else "")
            },
        }

    return {
        "summary": idx.summary(),
        "metadata": {
            "note": (
                "Use config(search='...') to find settings or "
                "config(key='AiPlayerbot.X') for details and code refs. "
                "rebuild=true re-scans the mod source."
            ),
        },
    }


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "config",
        "description": (
            "mod-playerbots configuration index: list/inspect settings from "
            "playerbots.conf.dist with defaults, conf line numbers and the C++ "
            "GetOption call sites that read each key. config(): summary "
            "(counts by prefix). config(search='travel'): substring match on "
            "key names. config(key='AiPlayerbot.X'): full detail incl. code "
            "refs. Requires the mod-playerbots source tree (PLAYERBOTS_ROOT); "
            "absence is a clean error."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Exact setting key for full detail + code refs."
                },
                "search": {
                    "type": "string",
                    "description": "Case-insensitive substring match on key names."
                },
                "rebuild": {
                    "type": "boolean",
                    "description": "Force re-scanning the mod conf + source (default false)."
                },
            },
        },
    }
