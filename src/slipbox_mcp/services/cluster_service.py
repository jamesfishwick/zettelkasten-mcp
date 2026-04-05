"""Service for detecting emergent knowledge clusters in the Zettelkasten."""
import json
import logging
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from slipbox_mcp.models.cluster_models import (
    CO_OCCURRENCE_THRESHOLD,
    MIN_CLUSTER_SIZE,
    REPORT_PATH,
    ClusterCandidate,
    ClusterReport,
)
from slipbox_mcp.models.schema import Note, NoteType
from slipbox_mcp.services.zettel_service import ZettelService

logger = logging.getLogger(__name__)


class ClusterService:
    """Service for detecting and managing knowledge clusters."""

    def __init__(self, zettel_service: Optional[ZettelService] = None, report_path: Optional[Path] = None):
        self.zettel_service = zettel_service or ZettelService()
        self.report_path = Path(report_path) if report_path is not None else REPORT_PATH

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

        # Higher-frequency pairs form cluster seeds.
        for (tag_a, tag_b), count in sorted(cooccurrence.items(), key=lambda x: -x[1]):
            cluster_a = tag_to_cluster.get(tag_a)
            cluster_b = tag_to_cluster.get(tag_b)

            if cluster_a is None and cluster_b is None:
                new_cluster = {tag_a, tag_b}
                clusters.append(new_cluster)
                tag_to_cluster[tag_a] = new_cluster
                tag_to_cluster[tag_b] = new_cluster
            elif cluster_a is None:
                cluster_b.add(tag_a)
                tag_to_cluster[tag_a] = cluster_b
            elif cluster_b is None:
                cluster_a.add(tag_b)
                tag_to_cluster[tag_b] = cluster_a
            elif cluster_a is not cluster_b:
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
        """Count notes with no links at all (no outgoing or incoming within the cluster)."""
        all_target_ids = {link.target_id for note in notes for link in note.links}
        return sum(
            1 for note in notes
            if not note.links and note.id not in all_target_ids
        )

    def score_cluster(self, notes: List[Note]) -> Optional[Dict[str, Any]]:
        """Calculate cluster urgency score."""
        note_count = len(notes)
        if note_count < MIN_CLUSTER_SIZE:
            return None

        orphan_count = self.count_orphans(notes)
        internal_links = self.count_internal_links(notes)

        max_links = note_count * (note_count - 1)
        density = internal_links / max_links if max_links > 0 else 0

        newest = max(n.updated_at for n in notes)
        days_old = (datetime.now() - newest).days

        # Scoring formula:
        # - count_score: More notes = more urgent, bonus if >15
        # - orphan_ratio: Higher orphan ratio = more urgent
        # - density: Lower density = more urgent (needs structure)
        # - freshness: Recent activity = more urgent

        count_score = min(note_count / 10, 1.5)
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

    def detect_clusters(self, notes: Optional[List[Note]] = None) -> ClusterReport:
        """Run full cluster detection analysis."""
        all_notes = notes if notes is not None else self.zettel_service.get_all_notes()
        cooccurrence = self.build_tag_cooccurrence(all_notes)
        tag_clusters = self.find_tag_clusters(cooccurrence)

        results: List[ClusterCandidate] = []
        for tags in tag_clusters:
            if self.has_structure_note(all_notes, tags):
                continue

            cluster_notes = self.get_cluster_notes(all_notes, tags)

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

        results.sort(key=lambda x: -x.score)

        # Build target-ID set once for O(n) orphan counting instead of O(n^2).
        all_target_ids = {link.target_id for n in all_notes for link in n.links}
        total_orphans = sum(
            1 for n in all_notes
            if not n.links and n.id not in all_target_ids
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
        self.report_path.parent.mkdir(parents=True, exist_ok=True)

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
            "stats": report.stats,
            "dismissed_cluster_ids": report.dismissed_cluster_ids
        }

        self.report_path.write_text(json.dumps(data, indent=2))
        return self.report_path

    def load_report(self) -> Optional[ClusterReport]:
        """Load cluster report from JSON file."""
        if not self.report_path.exists():
            return None

        try:
            data = json.loads(self.report_path.read_text())
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
                stats=data["stats"],
                dismissed_cluster_ids=data.get("dismissed_cluster_ids", [])
            )
        except Exception as e:
            logger.error("Failed to load cluster report: %s", e)
            return None

    def dismiss_cluster(self, cluster_id: str) -> None:
        """Mark cluster as dismissed; hides it from maintenance suggestions."""
        report = self.load_report()
        if report:
            if cluster_id not in report.dismissed_cluster_ids:
                report.dismissed_cluster_ids.append(cluster_id)
            self.save_report(report)
