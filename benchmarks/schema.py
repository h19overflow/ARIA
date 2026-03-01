from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class QueryCategory(str, Enum):
    NATURAL_LANGUAGE = "natural_language"
    EXACT_LOOKUP = "exact_lookup"
    MULTI_NODE = "multi_node"
    AMBIGUOUS = "ambiguous"
    MISSPELLED = "misspelled"
    PARTIAL_DESCRIPTION = "partial_description"
    WORKFLOW_TEMPLATE = "workflow_template"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class GoldenQuery:
    id: str
    category: QueryCategory
    query: str
    expected_nodes: list[str]       # node_type values, e.g. "n8n-nodes-base.slack"
    expected_doc_type: str = "node"  # "node" or "workflow_template"
    difficulty: Difficulty = Difficulty.MEDIUM


@dataclass
class GoldenDataset:
    version: str = "1.0"
    queries: list[GoldenQuery] = field(default_factory=list)
