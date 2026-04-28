"""
WDBC file reader for World of Warcraft DBC files.

This module provides functionality to read and parse WDBC format files
used in WoW 3.3.5 (WotLK).

WDBC File Format:
    Header (20 bytes):
        - Signature: 4 bytes ('WDBC')
        - RecordCount: 4 bytes (number of rows)
        - FieldCount: 4 bytes (number of columns)
        - RecordSize: 4 bytes (size of each record in bytes)
        - StringBlockSize: 4 bytes (size of string table)
    Data Section: RecordCount * RecordSize bytes
    String Table: StringBlockSize bytes (null-terminated strings)
"""

import struct
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class WDBCReader:
    """Reader for WDBC format DBC files."""

    WDBC_SIGNATURE = b'WDBC'

    def __init__(self, dbc_path: str, format_string: str):
        """
        Initialize WDBC reader.

        Args:
            dbc_path: Path to .dbc file
            format_string: Format string for this DBC type
        """
        self.dbc_path = Path(dbc_path)
        self.format_string = format_string

        # Header fields
        self.signature = None
        self.record_count = 0
        self.field_count = 0
        self.record_size = 0
        self.string_block_size = 0

        # Data
        self.data = None
        self.string_table = None
        self.records: List[Dict[int, Any]] = []
        
        # ID index for O(1) lookups: Dict[id_value -> row_index]
        self._id_index: Dict[int, int] = {}

    def read(self) -> bool:
        """
        Read and parse the DBC file.

        Returns:
            True if successful, False otherwise
        """
        if not self.dbc_path.exists():
            raise FileNotFoundError(f"DBC file not found: {self.dbc_path}")

        with open(self.dbc_path, 'rb') as f:
            # Read header
            if not self._read_header(f):
                return False

            # Validate format
            if not self._validate_format():
                return False

            # Read data section
            self.data = f.read(self.record_count * self.record_size)

            # Read string table
            self.string_table = f.read(self.string_block_size)

        # Parse records and build ID index
        self._parse_records()

        return True

    def _read_header(self, f) -> bool:
        """Read and parse the WDBC header."""
        header = f.read(20)
        if len(header) < 20:
            return False

        self.signature = header[0:4]
        if self.signature != self.WDBC_SIGNATURE:
            raise ValueError(f"Invalid signature: {self.signature}. Expected WDBC.")

        self.record_count = struct.unpack('<I', header[4:8])[0]
        self.field_count = struct.unpack('<I', header[8:12])[0]
        self.record_size = struct.unpack('<I', header[12:16])[0]
        self.string_block_size = struct.unpack('<I', header[16:20])[0]

        return True

    def _validate_format(self) -> bool:
        """Validate that the format string matches the DBC header."""
        format_field_count = len(self.format_string)

        if format_field_count != self.field_count:
            raise ValueError(
                f"Format field count mismatch: format={format_field_count}, "
                f"dbc={self.field_count}"
            )

        return True

    def _parse_records(self):
        """Parse all records from the data section and build ID index."""
        self.records = []
        self._id_index = {}
        offset = 0

        for row_idx in range(self.record_count):
            record = self._parse_record(offset)
            self.records.append(record)
            
            # Build ID index (field 0 is always the ID)
            id_value = record.get(0)
            if id_value is not None:
                self._id_index[id_value] = row_idx
            
            offset += self.record_size

    def _parse_record(self, offset: int) -> Dict[int, Any]:
        """
        Parse a single record.

        Args:
            offset: Byte offset in data section

        Returns:
            Dictionary mapping field index to value
        """
        record = {}
        field_offset = offset

        for field_idx, fmt_char in enumerate(self.format_string):
            if fmt_char in ('i', 'n', 'd', 'l'):  # uint32
                value = struct.unpack_from('<I', self.data, field_offset)[0]
                record[field_idx] = value
                field_offset += 4

            elif fmt_char == 'f':  # float
                value = struct.unpack_from('<f', self.data, field_offset)[0]
                record[field_idx] = value
                field_offset += 4

            elif fmt_char == 's':  # string (offset into string table)
                string_offset = struct.unpack_from('<I', self.data, field_offset)[0]
                string_value = self._read_string(string_offset)
                record[field_idx] = string_value
                field_offset += 4

            elif fmt_char == 'b':  # uint8
                value = struct.unpack_from('<B', self.data, field_offset)[0]
                record[field_idx] = value
                field_offset += 1

            elif fmt_char == 'x':  # skip 4 bytes
                record[field_idx] = None
                field_offset += 4

            elif fmt_char == 'X':  # skip 1 byte
                record[field_idx] = None
                field_offset += 1

        return record

    def _read_string(self, offset: int) -> str:
        """
        Read a null-terminated string from the string table.

        Args:
            offset: Offset into string table

        Returns:
            Decoded string
        """
        if offset >= len(self.string_table):
            return ""

        # Find null terminator
        end = offset
        while end < len(self.string_table) and self.string_table[end] != 0:
            end += 1

        # Decode string
        try:
            return self.string_table[offset:end].decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            return self.string_table[offset:end].decode('latin-1', errors='ignore')

    def get_record(self, row_id: int) -> Optional[Dict[int, Any]]:
        """
        Get a record by row index.

        Args:
            row_id: Row index (0-based)

        Returns:
            Record dictionary or None if not found
        """
        if 0 <= row_id < len(self.records):
            return self.records[row_id]
        return None

    def get_record_by_id(self, id_value: int) -> Optional[Dict[int, Any]]:
        """
        Get a record by ID field value (assumes field 0 is ID).
        
        Uses O(1) ID index lookup.

        Args:
            id_value: Value of ID field to search for

        Returns:
            Record dictionary or None if not found
        """
        row_idx = self._id_index.get(id_value)
        if row_idx is not None:
            return self.records[row_idx]
        return None

    def query(
        self,
        filter_dict: Optional[Dict[int, Any]] = None,
        columns: Optional[List[int]] = None
    ) -> List[Dict[int, Any]]:
        """
        Query records with optional filtering and column selection.

        Args:
            filter_dict: Dictionary of field_index -> value to filter by
            columns: List of field indices to include in results (None = all)

        Returns:
            List of matching records
        """
        results = []

        for record in self.records:
            # Apply filter
            if filter_dict:
                match = True
                for field_idx, value in filter_dict.items():
                    if record.get(field_idx) != value:
                        match = False
                        break
                if not match:
                    continue

            # Apply column selection
            if columns:
                filtered_record = {idx: record.get(idx) for idx in columns}
                results.append(filtered_record)
            else:
                results.append(record.copy())

        return results

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the DBC file.

        Returns:
            Dictionary with file information
        """
        return {
            'file': str(self.dbc_path.name),
            'signature': self.signature.decode('ascii') if self.signature else None,
            'record_count': self.record_count,
            'field_count': self.field_count,
            'record_size': self.record_size,
            'string_block_size': self.string_block_size,
            'format': self.format_string
        }
