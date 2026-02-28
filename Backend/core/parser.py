"""
Robust section parser for research papers.

Handles all common formats from PDF, DOCX, TXT and LaTeX:
  - Standalone header line:     "Introduction" / "METHODOLOGY" / "II. Results"
  - Header + colon + content:   "Title: My Paper" / "Keywords: ML, AI"
  - Header + em/en-dash inline: "Abstract—We present..." / "Keywords–ML, AI"
  - Mixed (IEEE PDF style):     roman numerals, em-dash abstracts, etc.
  - Title as first non-blank line when no explicit title header exists
"""

import re
from .normalizer import normalize_section_name, SECTION_MAP

_KNOWN_HEADERS = sorted(SECTION_MAP.keys(), key=len, reverse=True)
_HEADERS_RE    = '|'.join(re.escape(h) for h in _KNOWN_HEADERS)

# Matches ANY section marker line — standalone or inline (colon / em-dash / en-dash)
# Groups:  header, sep (the separator char), body (optional inline text after sep)
_MARKER = re.compile(
    r'^'
    r'(?:[IVXivx]{1,4}[\.\)]\s*|\d+[\.\)]\s*)?'   # optional numbering
    r'(?P<header>' + _HEADERS_RE + r')'             # section name
    r'(?P<sep>\s*[—–:]\s*|\s*$)'                   # separator OR end-of-line
    r'(?P<body>.*)$',                               # optional inline body
    re.IGNORECASE | re.MULTILINE,
)


def parse_sections(raw_text: str) -> dict:
    raw_text = raw_text.replace('\r\n', '\n').replace('\r', '\n')
    sections: dict = {}

    matches = list(_MARKER.finditer(raw_text))

    for idx, match in enumerate(matches):
        normalized = normalize_section_name(match.group('header').strip())
        if not normalized:
            continue

        inline_body = (match.group('body') or '').strip()
        sep         = (match.group('sep') or '').strip()

        # Collect block content that follows this header line
        block_start = match.end()
        block_end   = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
        block_body  = raw_text[block_start:block_end].strip()

        # Combine: inline body first, then block body
        if inline_body and block_body:
            content = inline_body + '\n' + block_body
        else:
            content = inline_body or block_body

        _set_if_longer(sections, normalized, content)

    # ── Infer title from first non-blank line if still missing ───────────────
    if 'title' not in sections:
        for line in raw_text.split('\n'):
            line = line.strip()
            if line and 5 < len(line) < 200 and not _MARKER.match(line):
                sections['title'] = line
                break

    return sections


def _set_if_longer(sections: dict, key: str, value: str) -> None:
    if value and (key not in sections or len(value) > len(sections[key])):
        sections[key] = value
