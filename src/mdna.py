"""Split MD&A plaintext (which embeds raw HTML tables) into paragraphs and parsed tables, and pick relevant excerpts."""
import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from typing import List, Sequence, Union

_TABLE_RE = re.compile(r"<table\b.*?</table>", re.S | re.I)
_PARA_SPLIT = re.compile(r"\s{3,}")
_JOIN_NEXT = {"$", "("}
_JOIN_PREV = {"%", ")", ")%", "%)"}


@dataclass
class Table:
    rows: List[List[str]] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(" | ".join(r) for r in self.rows)


Block = Union[str, Table]


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: List[List[str]] = []
        self._row: List[str] = []
        self._cell: List[str] = []
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._in_cell, self._cell = True, []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            self._row.append(" ".join("".join(self._cell).split()))
            self._in_cell = False
        elif tag == "tr":
            self.rows.append(self._row)

    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(data)


def _merge_cells(cells: Sequence[str]) -> List[str]:
    out: List[str] = []
    carry = ""
    for cell in cells:
        if not cell:
            continue
        if cell in _JOIN_NEXT:
            carry += cell
            continue
        if cell in _JOIN_PREV and out:
            out[-1] += cell
            continue
        out.append(carry + cell)
        carry = ""
    return out


def parse_table(html: str) -> Table:
    parser = _TableParser()
    parser.feed(html)
    rows = [r for r in (_merge_cells(r) for r in parser.rows) if r]
    if not rows:
        return Table()
    width = max(len(r) for r in rows)
    # Header rows (years) lack the leading label column; left-pad them, right-pad everything else.
    padded = [([""] * (width - len(r)) + r) if i == 0 and len(r) < width else r + [""] * (width - len(r)) for i, r in enumerate(rows)]
    return Table(rows=padded)


def split_blocks(text: str) -> List[Block]:
    blocks: List[Block] = []
    pos = 0
    for match in _TABLE_RE.finditer(text):
        blocks.extend(_paragraphs(text[pos : match.start()]))
        table = parse_table(match.group(0))
        if table.rows:
            blocks.append(table)
        pos = match.end()
    blocks.extend(_paragraphs(text[pos:]))
    return blocks


def _paragraphs(chunk: str) -> List[str]:
    chunk = unescape(re.sub(r"<[^>]+>", " ", chunk))
    return [p.strip() for p in _PARA_SPLIT.split(chunk) if len(p.strip()) > 1]


def relevant_excerpt(text: str, keywords: Sequence[str], max_chars: int = 3000) -> List[Block]:
    """Pick paragraphs mentioning keywords, plus the table right after a matching paragraph."""
    blocks = split_blocks(text)
    keys = [k.lower() for k in keywords]
    picked: List[Block] = []
    used = 0
    for i, block in enumerate(blocks):
        if isinstance(block, Table):
            continue
        if not any(k in block.lower() for k in keys):
            continue
        candidates: List[Block] = [block]
        if i + 1 < len(blocks) and isinstance(blocks[i + 1], Table):
            candidates.append(blocks[i + 1])
        for c in candidates:
            size = len(c.text if isinstance(c, Table) else c)
            if c in picked or used + size > max_chars:
                continue
            picked.append(c)
            used += size
        if used >= max_chars:
            break
    return picked


def blocks_to_text(blocks: Sequence[Block]) -> str:
    return "\n\n".join(b.text if isinstance(b, Table) else b for b in blocks)
