"""
Path helpers that degrade gracefully on inaccessible parents.

pathlib's exists()/is_dir()/is_file() raise PermissionError when an
intermediate directory cannot be stat'ed (e.g. /root on a machine where
the current user has no access - exactly the case on CI runners and any
non-root checkout). These helpers treat any OSError as "absent".
"""

import os
from pathlib import Path


def safe_exists(p) -> bool:
    try:
        return Path(p).exists()
    except OSError:
        return False


def safe_is_dir(p) -> bool:
    try:
        return Path(p).is_dir()
    except OSError:
        return False


def safe_is_file(p) -> bool:
    try:
        return Path(p).is_file()
    except OSError:
        return False


def readable_file(p) -> bool:
    """File exists and is readable (OSError -> False)."""
    try:
        return os.access(p, os.R_OK) and Path(p).is_file()
    except OSError:
        return False
