#!/usr/bin/env python3
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from slipbox_mcp.services.cluster_service import ClusterService
from slipbox_mcp.services.zettel_service import ZettelService

def main():
    print("Starting cluster detection...")
    zettel_service = ZettelService()
    cluster_service = ClusterService(zettel_service)
    report = cluster_service.detect_clusters()
    path = cluster_service.save_report(report)
    
    print(f"Report saved to: {path}")
    print(f"Total notes: {report.stats['total_notes']}")
    print(f"Orphaned notes: {report.stats['total_orphans']}")
    print(f"Clusters needing structure: {report.stats['clusters_needing_structure']}")
    
    if report.clusters:
        print("\nTop clusters:")
        for c in report.clusters[:5]:
            print(f"  {c.score:.2f} | {c.suggested_title} ({c.note_count} notes)")

if __name__ == "__main__":
    main()
