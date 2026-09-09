"""Enum index: parse C++ enum definitions from the AzerothCore source.

One cached pass over all .h files under the source root builds
  {enum_name: {"file": str, "members": {value: name}}}
so tools can decode magic numbers (e.g. Spell Mechanic 17 ->
MECHANIC_POLYMORPH) without an agent grepping the tree.

Only named enums are indexed (anonymous enums carry no stable name).
Member values must be plain integer literals (decimal/0x hex/0b);
expression initializers ((1 << 0), X | Y) are skipped but do not break
auto-increment numbering. Bitmask flag "enums" parse fine too - they
are still named value tables.

NOTE: core/enums.py (lookup dictionaries used by type_resolver) is a
different module - this one is the source-scanning index.

Environment override: ACORE_SRC_ROOT (default /root/azerothcore-wotlk).
"""

import os
import re
from typing import Any, Dict, Optional

_SRC_ROOT_DEFAULT = "/root/azerothcore-wotlk"

_ENUM_RE = re.compile(
    r"^\s*enum\s+(?:class\s+)?(?P<name>[A-Za-z_]\w*)?\s*(?::\s*\w+\s*)?\{",
    re.M,
)
_INT_RE = re.compile(r"^(0x[0-9A-Fa-f]+|0b[01]+|-?\d+)$")


def _src_root() -> str:
    return os.environ.get("ACORE_SRC_ROOT", _SRC_ROOT_DEFAULT)


def _parse_value(token: str) -> Optional[int]:
    token = token.strip()
    if _INT_RE.match(token):
        try:
            base = 0
            if token.lower().startswith("0x"):
                base = 16
            elif token.lower().startswith("0b"):
                base = 2
            return int(token, base)
        except ValueError:
            return None
    return None


def _extract_enums_from_text(text: str, file: str,
                             index: Dict[str, Dict[str, Any]]) -> None:
    pos = 0
    while True:
        m = _ENUM_RE.search(text, pos)
        if not m:
            break
        name = m.group("name")
        if not name:
            # anonymous enum - skip to its closing brace
            close = text.find("}", m.end())
            pos = close + 1 if close != -1 else len(text)
            continue
        # find the closing brace (enum bodies contain no nested braces in
        # practice; a stray '}' just truncates the body)
        close = text.find("}", m.end())
        if close == -1:
            break
        body = text[m.end():close]
        # strip comments
        body = re.sub(r"//.*", "", body)
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)

        members: Dict[int, str] = {}
        auto = 0
        for part in body.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                member, _, val = part.partition("=")
                v = _parse_value(val)
                if v is None:
                    # expression initializer: keep the member name out
                    # (do not guess the value); auto numbering continues
                    continue
                members[v] = member.strip()
                auto = v + 1
            else:
                # auto-increment
                members[auto] = part
                auto += 1
        if members and name not in index:
            index[name] = {"file": file, "members": members}
        elif members:
            # duplicate definition (guard/variant) - keep first, top up
            for v, n in members.items():
                index[name]["members"].setdefault(v, n)
        pos = close + 1


def build_enum_index(src_root: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Parse all named enums under src_root. Returns {name: {file, members}}
    where members maps int value -> member name."""
    root = src_root or _src_root()
    src_dir = os.path.join(root, "src")
    index: Dict[str, Dict[str, Any]] = {}
    if not os.path.isdir(src_dir):
        return index
    for dirpath, _dirs, filenames in os.walk(src_dir):
        for fn in filenames:
            if not fn.endswith((".h", ".hpp")):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            _extract_enums_from_text(text, rel, index)
    return index


def find_enums_by_value(index: Dict[str, Dict[str, Any]], value: int,
                        limit: int = 20) -> Dict[str, str]:
    """Map enum_name -> member name for enums containing `value`."""
    out: Dict[str, str] = {}
    for name, info in index.items():
        if value in info["members"]:
            out[name] = info["members"][value]
            if len(out) >= limit:
                break
    return out
