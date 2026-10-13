from dataclasses import dataclass
from pathlib import Path
@dataclass
class MarkdownFile:
    name: str
    path: Path
    content: str
    mtime: float