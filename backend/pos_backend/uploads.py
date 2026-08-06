"""Small dependency-free CSV/XLSX upload reader shared by bulk endpoints."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import openpyxl


def _key(value):
    return ''.join(ch for ch in str(value or '').strip().lower() if ch.isalnum())


def read_upload_records(file_obj):
    """Return rows as dictionaries with normalized column names.

    The previous bulk endpoints imported pandas even though it was not in the
    production requirements. Keeping parsing here avoids a hidden runtime
    dependency and gives every importer the same CSV/XLSX behavior.
    """
    name = Path(getattr(file_obj, 'name', '')).suffix.lower()
    if name == '.csv':
        raw = file_obj.read()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(raw))
        return [{_key(k): value for k, value in row.items()} for row in reader]

    if name not in {'.xlsx', '.xlsm'}:
        raise ValueError('Unsupported file format. Use CSV or XLSX.')
    workbook = openpyxl.load_workbook(file_obj, data_only=True, read_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    header_index = next(
        (index for index, row in enumerate(rows) if any(value not in (None, '') for value in row)),
        None,
    )
    if header_index is None:
        return []
    headers = [_key(value) for value in rows[header_index]]
    return [
        dict(zip(headers, row))
        for row in rows[header_index + 1:]
        if any(value not in (None, '') for value in row)
    ]
