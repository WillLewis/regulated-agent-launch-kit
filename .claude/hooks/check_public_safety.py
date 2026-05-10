#!/usr/bin/env python3
"""Warn on likely public-safety issues in Claude Code file edits."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


RISK_PATTERNS = [
    re.compile(r"\b(real|actual)\s+(customer|user)\s+(data|identifier|workflow)\b", re.I),
    re.compile(r"\bproduction\s+(threshold|control|rule|url|credential|secret)\b", re.I),
    re.compile(r"\bSAR\b|\bsuspicious activity report\b", re.I),
    re.compile(r"\bcredit bureau schema\b", re.I),
    re.compile(r"\bfraud typolog(y|ies)\b", re.I),
]


def iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(iter_strings(item))
        return strings
    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(iter_strings(item))
        return strings
    return []


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = raw

    body = "\n".join(iter_strings(payload))
    matches = sorted({pattern.pattern for pattern in RISK_PATTERNS if pattern.search(body)})
    if matches:
        print(
            "Public-safety hook warning: edit may mention real regulated-finance data or controls. "
            "Keep repo content synthetic and public-safe.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
