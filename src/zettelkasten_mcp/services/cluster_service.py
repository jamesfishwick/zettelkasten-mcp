"""Service for detecting emergent knowledge clusters in the Zettelkasten."""
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from zettelkasten_mcp.config import config
from zettelkasten_mcp.models.schema import Note, NoteType
from zettelkasten_mcp.services.zettel_service import ZettelService

logger = logging.getLogger(__name__)

# Configuration
MIN_CLUSTER_SIZE = 5
CO_OCCURRENCE_THRESHOLD = 3
REPORT_PATH = Path("~/.local/share/mcp/zettelkasten/cluster-analysis.json").expanduser()


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


class ClusterService:
    """Service for detecting and managing knowledge clusters."""
    
    def __init__(self, zettel_service: Optional[ZettelService] = None):
        self.zettel_service = zettel_service or ZettelService()
    
    def build_tag_cooccurrence(self, notes: List[Note]) -> Dict[Tuple[str, str], int]:
        """Build matrix of tag pairs that appear together on notes."""
        cooccurrence = defaultdict(int)
        for note in notes:
            tag_names = sorted([tag.name for tag in note.tags])
            for tag_a, tag_b in combinations(tag_names, 2):
                cooccurrence[(tag_a, tag_b)] += 1
        
        # Filter by threshold
        return {k: v for k, v in cooccurrence.items() if v >= CO_OCCURRENCE_THRESHOLD}
    
    def find_tag_clusters(self, cooccurrence: Dict[Tuple[str, str], int]) -> List[Set[str]]:
        """Group tags that frequently co-occur using union-find approach."""
        tag_to_cluster: Dict[str, Set[str]] = {}
        clusters: List[Set[str]] = []
        
        # Process pairs in order of frequency (highest first)
        for (tag_a, tag_b), count in sorted(cooccurrence.items(), key=lambda x: -x[1]):
            cluster_a = tag_to_cluster.get(tag_a)
            cluster_b = tag_to_cluster.get(tag_b)
            
            if cluster_a is None and cluster_b is None:
                # Both tags are new - create new cluster
                new_cluster = {tag_a, tag_b}
                clusters.append(new_cluster)
                tag_to_cluster[tag_a] = new_cluster
                tag_to_cluster[tag_b] = new_cluster
            elif cluster_a is None:
                # tag_a is new, add to tag_b's cluster
                cluster_b.add(tag_a)
                tag_to_cluster[tag_a] = cluster_b
            elif cluster_b is None:
                # tag_b is new, add to tag_a's cluster
                cluster_a.add(tag_b)
                tag_to_cluster[tag_b] = cluster_a
            elif cluster_a is not cluster_b:
                # Merge clusters
                cluster_a.update(cluster_b)
                for tag in cluster_b:
                    tag_to_cluster[tag] = cluster_a
                clusters.remove(cluster_b)
        
        return [c for c in clusters if len(c) >= 2]
    
    def get_cluster_notes(self, all_notes: List[Note], tags: Set[str]) -> List[Note]:
        """Get notes that have at least 2 tags from the cluster."""
        return [n for n in all_notes if len(set(t.name for t in n.tags) & tags) >= 2]
    
    def has_structure_note(self, all_notes: List[Note], tags: Set[str]) -> bool:
        """Check if a structure note already covers this cluster."""
        for note in all_notes:
            if note.note_type == NoteType.STRUCTURE:
                note_tags = set(t.name for t in note.tags)
                if len(note_tags & tags) >= 2:
                    return True
        return False
    
    def count_internal_links(self, notes: List[Note]) -> int:
        """Count links between notes in the cluster."""
        note_ids = {n.id for n in notes}
        count = 0
        for note in notes:
            for link in note.links:
                if link.target_id in note_ids:
                    count += 1
        return count
    
    def count_orphans(self, notes: List[Note]) -> int:
        """Count notes with no links at all."""
        orphan_count = 0
        for note in notes:
            # Get incoming links by checking all notes
            has_incoming = False
            for other in notes:
                if other.id != note.id:
                    for link in other.links:
                        if link.target_id == note.id:
                            has_incoming = True
                            break
                if has_incoming:
                    break
            
            if not note.links and not has_incoming:
                orphan_count += 1
        
        return orphan_count
    
    def score_cluster(self, notes: List[Note]) -> Optional[Dict[str, Any]]:
        """Calculate cluster urgency score."""
        note_count = len(notes)
        if note_count < MIN_CLUSTER_SIZE:
            return None
        
        orphan_count = self.count_orphans(notes)
        internal_links = self.count_internal_links(notes)
        
        # Calculate density
        max_links = note_count * (note_count - 1)
        density = internal_links / max_links if max_links > 0 else 0
        
        # Get newest note date
        newest = max(n.updated_at for n in notes)
        days_old = (datetime.now() - newest).days
        
        # Scoring formula:
        # - count_score: More notes = more urgent, bonus if >15
        # - orphan_ratio: Higher orphan ratio = more urgent
        # - density: Lower density = more urgent (needs structure)
        # - freshness: Recent activity = more urgent
        
        count_score = min(note_count / 7, 1.0) * (1.5 if note_count > 15 else 1.0)
        orphan_ratio = orphan_count / note_count
        urgency_score = orphan_ratio * 2
        freshness = max(0, 1 - (days_old / 90))
        
        final_score = (
            (count_score * 0.3) + 
            (urgency_score * 0.4) + 
            ((1 - density) * 0.2) + 
            (freshness * 0.1)
        )
        
        return {
            "note_count": note_count,
            "orphan_count": orphan_count,
            "internal_links": internal_links,
            "density": round(density, 3),
            "score": round(min(final_score, 1.0), 3),
            "newest_date": newest
        }
    
    def suggest_title(self, tags: Set[str]) -> str:
        """Generate structure note title from tags."""
        # Heuristic: longest/most specific tag first
        sorted_tags = sorted(tags, key=lambda t: (-len(t), t))
        primary = sorted_tags[0].replace("-", " ").title()
        return f"{primary} Knowledge Map"
    
    def detect_clusters(self) -> ClusterReport:
        """Run full cluster detection analysis."""
        # Get all notes
        all_notes = self.zettel_service.get_all_notes()
        
        # Build co-occurrence matrix
        cooccurrence = self.build_tag_cooccurrence(all_notes)
        
        # Find tag clusters
        tag_clusters = self.find_tag_clusters(cooccurrence)
        
        # Analyze each cluster
        results: List[ClusterCandidate] = []
        for tags in tag_clusters:
            # Skip if already has structure note
            if self.has_structure_note(all_notes, tags):
                continue
            
            # Get notes in cluster
            cluster_notes = self.get_cluster_notes(all_notes, tags)
            
            # Score the cluster
            metrics = self.score_cluster(cluster_notes)
            if metrics and metrics["score"] >= 0.4:
                cluster_id = "-".join(sorted(tags)[:3])
                results.append(ClusterCandidate(
                    id=cluster_id,
                    suggested_title=self.suggest_title(tags),
                    tags=sorted(tags),
                    notes=[{"id": n.id, "title": n.title} for n in cluster_notes],
                    note_count=metrics["note_count"],
                    orphan_count=metrics["orphan_count"],
                    internal_links=metrics["internal_links"],
                    density=metrics["density"],
                    score=metrics["score"],
                    newest_date=metrics["newest_date"]
                ))
        
        # Sort by score
        results.sort(key=lambda x: -x.score)
        
        # Calculate stats
        total_orphans = sum(
            1 for n in all_notes 
            if not n.links and not any(
                link.target_id == n.id 
                for other in all_notes 
                for link in other.links
            )
        )
        
        return ClusterReport(
            generated_at=datetime.now(),
            clusters=results[:20],
            stats={
                "total_notes": len(all_notes),
                "total_orphans": total_orphans,
                "clusters_detected": len(tag_clusters),
                "clusters_needing_structure": len(results)
            }
        )
    
    def save_report(self, report: ClusterReport) -> Path:
        """Save cluster report to JSON file."""
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable dict
        data = {
            "generated_at": report.generated_at.isoformat(),
            "clusters": [
                {
                    "id": c.id,
                    "suggested_title": c.suggested_title,
                    "tags": c.tags,
                    "notes": c.notes,
                    "note_count": c.note_count,
                    "orphan_count": c.orphan_count,
                    "internal_links": c.internal_links,
                    "density": c.density,
                    "score": c.score,
                    "newest_date": c.newest_date.isoformat() if c.newest_date else None
                }
                for c in report.clusters
            ],
            "stats": report.stats
        }
        
        REPORT_PATH.write_text(json.dumps(data, indent=2))
        return REPORT_PATH
    
    def load_report(self) -> Optional[ClusterReport]:
        """Load cluster report from JSON file."""
        if not REPORT_PATH.exists():
            return None
        
        try:
            data = json.loads(REPORT_PATH.read_text())
            return ClusterReport(
                generated_at=datetime.fromisoformat(data["generated_at"]),
                clusters=[
                    ClusterCandidate(
                        id=c["id"],
                        suggested_title=c["suggested_title"],
                        tags=c["tags"],
                        notes=c["notes"],
                        note_count=c["note_count"],
                        orphan_count=c["orphan_count"],
                        internal_links=c["internal_links"],
                        density=c["density"],
                        score=c["score"],
                        newest_date=datetime.fromisoformat(c["newest_date"]) if c.get("newest_date") else None
                    )
                    for c in data["clusters"]
                ],
                stats=data["stats"]
            )
        except Exception as e:
            logger.error(f"Failed to load cluster report: {e}")
            return None
