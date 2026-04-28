"""
Parser for AzerothCore DBCfmt.h file to extract DBC format strings.

This module reads the DBCfmt.h header file and extracts format string
definitions for each DBC file type.

Format string characters:
    i = uint32 (4 bytes)
    f = float (4 bytes)
    s = string (4-byte offset into string table)
    b = uint8 (1 byte)
    x = skip/unused (4 bytes)
    X = skip/unused (1 byte)
    n = index field (uint32)
    d = sorted index field (uint32)
    l = logical/boolean (uint32)
"""

import re
from typing import Dict, Optional
from pathlib import Path


class FormatParser:
    """Parser for DBCfmt.h format string definitions."""

    # Mapping from DBC filename to format name (when they differ)
    DBC_NAME_MAP = {
        "Spell": "SpellEntry",
        "AreaTable": "AreaTableEntry",
        "ChrClasses": "ChrClasses",
        "ChrRaces": "ChrRaces",
        "CreatureDisplayInfo": "CreatureDisplayInfo",
        "CreatureFamily": "CreatureFamily",
        "Talent": "TalentEntry",
        "TalentTab": "TalentTabEntry",
        # File names with underscores -> Format names without
        "Achievement_Category": "AchievementCategory",
        "Achievement_Criteria": "AchievementCriteria",
        # File names plural -> Format names with Entry suffix
        "LFGDungeons": "LFGDungeonEntry",
        "SpellCastTimes": "SpellCastTime",
        # Abbreviated file names
        "RandPropPoints": "RandomPropertiesPoints",
        # Add more mappings as discovered
    }

    def __init__(self, dbcfmt_path: str):
        """
        Initialize the format parser.

        Args:
            dbcfmt_path: Path to DBCfmt.h file
        """
        self.dbcfmt_path = Path(dbcfmt_path)
        self.formats: Dict[str, str] = {}

    def parse(self) -> Dict[str, str]:
        """
        Parse the DBCfmt.h file and extract all format strings.

        Returns:
            Dictionary mapping DBC name to format string
            Example: {"Spell": "niiiiii...", "SkillLineAbility": "niiiixxiiiiixx"}

        Raises:
            FileNotFoundError: If DBCfmt.h file doesn't exist
        """
        if not self.dbcfmt_path.exists():
            raise FileNotFoundError(f"DBCfmt.h not found at: {self.dbcfmt_path}")

        with open(self.dbcfmt_path, 'r') as f:
            content = f.read()

        # Pattern matches:
        # char constexpr Achievementfmt[] = "niixssssssssssssssssxxxxxxxxxxxxxxxxxxiixixxxxxxxxxxxxxxxxxxii";
        # char constexpr SkillLineAbilityfmt[] = "niiiixxiiiiixx";
        pattern = r'char\s+constexpr\s+(\w+)fmt\[\]\s*=\s*"([^"]+)"'

        matches = re.findall(pattern, content)

        for name, format_string in matches:
            # Convert from "Achievementfmt" -> "Achievement"
            # Convert from "SkillLineAbilityfmt" -> "SkillLineAbility"
            dbc_name = name
            self.formats[dbc_name] = format_string

        return self.formats

    def get_format(self, dbc_name: str) -> Optional[str]:
        """
        Get the format string for a specific DBC file.

        Args:
            dbc_name: Name of the DBC (without .dbc extension)
                     Can be with or without "fmt" suffix
                     Examples: "Spell", "SkillLineAbility", "Spellfmt"

        Returns:
            Format string or None if not found
        """
        if not self.formats:
            self.parse()

        # Try name mapping first (e.g., "Spell" -> "SpellEntry")
        mapped_name = self.DBC_NAME_MAP.get(dbc_name, dbc_name)

        # Try exact match with mapped name
        if mapped_name in self.formats:
            return self.formats[mapped_name]

        # Try exact match with original name
        if dbc_name in self.formats:
            return self.formats[dbc_name]

        # Try with "fmt" suffix removed
        if dbc_name.endswith("fmt"):
            return self.formats.get(dbc_name[:-3])

        # Try with "Entry" suffix
        entry_name = dbc_name + "Entry"
        if entry_name in self.formats:
            return self.formats[entry_name]

        # Try with "fmt" suffix added
        fmt_name = dbc_name + "fmt"
        if fmt_name in self.formats:
            return self.formats[fmt_name]

        # Case-insensitive fallback: search all formats for case-insensitive match
        dbc_name_lower = dbc_name.lower()
        for fmt_key in self.formats:
            if fmt_key.lower() == dbc_name_lower:
                return self.formats[fmt_key]
            # Also check without "Entry" suffix
            if fmt_key.lower() == dbc_name_lower + "entry":
                return self.formats[fmt_key]
            if fmt_key.lower().replace("entry", "") == dbc_name_lower:
                return self.formats[fmt_key]

        return None

    def list_available(self) -> list[str]:
        """
        List all available DBC format names.

        Returns:
            List of DBC names (without "fmt" suffix)
        """
        if not self.formats:
            self.parse()

        return sorted(self.formats.keys())

    def get_field_count(self, format_string: str) -> int:
        """
        Count the number of fields in a format string.

        Args:
            format_string: DBC format string

        Returns:
            Number of fields
        """
        return len(format_string)

    def get_record_size(self, format_string: str) -> int:
        """
        Calculate the record size in bytes for a format string.

        Args:
            format_string: DBC format string

        Returns:
            Record size in bytes
        """
        size = 0
        for char in format_string:
            if char in ('i', 'f', 's', 'n', 'd', 'l', 'x'):
                size += 4  # 4-byte fields
            elif char in ('b', 'X'):
                size += 1  # 1-byte fields
        return size
