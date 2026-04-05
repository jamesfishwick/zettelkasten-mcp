"""Domain models and constants for cluster detection."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

MIN_CLUSTER_SIZE = 5
CO_OCCURRENCE_THRESHOLD = 3
REPORT_PATH = Path("~/.local/share/mcp/slipbox/cluster-analysis.json").expanduser()


@dataclass
class ClusterCandidate:
    """A detected cluster that may need a structure note."""
    id: str
    suggested_title: str
    tags: List[str]
    notes: List[Dict[str, str]]  # [{id, title}, ...]
    note_count: int
    orphan_count: int
    internal_links: int
    density: float
    score: float
    newest_date: Optional[datetime] = None


@dataclass
class ClusterReport:
    """Full cluster analysis report."""
    generated_at: datetime
    clusters: List[ClusterCandidate]
    stats: Dict[str, Any]
    dismissed_cluster_ids: List[str] = field(default_factory=list)
