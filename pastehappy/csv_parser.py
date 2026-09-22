from __future__ import annotations

import csv
import io

ALIASES = {
    "groupName": {"group name", "group_name", "group", "name"},
    "groupUrl": {"group url", "group_url", "url", "link"},
    "postText": {"post text", "post_text", "post", "ad", "ad text", "message"},
}


def parse_csv(value: str) -> list[dict[str, str]]:
    reader = csv.reader(io.StringIO(str(value or "").lstrip("\ufeff"), newline=""))
    records = list(reader)
    if len(records) < 2:
        return []
    headers = [_normalize(item) for item in records[0]]
    indexes = {
        key: next((index for index, header in enumerate(headers) if header in aliases), -1)
        for key, aliases in ALIASES.items()
    }
    rows = []
    for record in records[1:]:
        row = {key: _value(record, index) for key, index in indexes.items()}
        if any(row.values()):
            rows.append(row)
    return rows


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _value(row: list[str], index: int) -> str:
    return row[index].strip() if 0 <= index < len(row) else ""
