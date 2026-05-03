"""
Resolver modules for acore-data.

Splits type resolution logic from monolithic type_resolver.py into table-specific
modules, each importing shared helpers and enums from their common parent.

Resolve functions are registered via RESOLVERS dict (table_name -> resolver func).
The resolve_type_fields dispatcher calls the right module per SQL table.
"""

from typing import Any, Dict, List, Optional

# Registry of table_name -> resolver function
RESOLVERS: Dict[str, Any] = {}


def register_resolver(table_name: str, resolver_func):
    """Register a resolver function for a specific SQL table."""
    RESOLVERS[table_name] = resolver_func


def get_resolver(table_name: str):
    """Get registered resolver for a table, or None."""
    return RESOLVERS.get(table_name)


# Import and auto-register resolvers (after function defs to avoid circular import)
from . import gameobject, smart_scripts, quest

register_resolver("gameobject_template", gameobject.resolve_gameobject_fields)
register_resolver("smart_scripts", smart_scripts.resolve_smart_scripts)
register_resolver("quest_template", quest.resolve_quest_fields)
