from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: Dict
    embedding: Optional[List[float]] = None


@dataclass
class ParentChunk:
    parent_id: str
    text: str
    metadata: Dict


@dataclass
class ChildChunk:
    child_id: str
    parent_id: str
    text: str
    metadata: Dict
