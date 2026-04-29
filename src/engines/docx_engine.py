from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocxParseResult:
    raw_text: str
    raw_tables: list[dict]
    doc_structure: dict


class DocxEngine:
    def parse(self, file_path: str) -> DocxParseResult:
        path = Path(file_path)
        return DocxParseResult(
            raw_text=f"Parsing pending for: {path.name}",
            raw_tables=[],
            doc_structure={"headings": [], "tables": []},
        )
