#!/usr/bin/env python3
"""
Audit Log Export Script

Purpose:
    Parse routing_audit JSONL logs and export to CSV or generate summary reports.

Usage:
    python audit_export.py --input data/routing_audit_2025-11-08.jsonl --output report.csv
    python audit_export.py --input data/routing_audit_*.jsonl --summary
"""
import argparse
import json
import csv
import glob
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Any


def parse_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load JSONL file into list of dicts."""
    entries = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception as e:
        print(f"Warning: Failed to parse {file_path}: {e}")
    return entries


def export_to_csv(entries: List[Dict[str, Any]], output_path: str) -> None:
    """Export audit entries to CSV."""
    if not entries:
        print("No entries to export.")
        return
    fieldnames = [
        "timestamp",
        "page_id",
        "batch_id",
        "operator_id",
        "route",
        "severity",
        "doc_type",
        "classification_confidence",
        "avg_field_confidence",
        "reasons",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for entry in entries:
            # Flatten reasons list to comma-separated string
            if "reasons" in entry and isinstance(entry["reasons"], list):
                entry["reasons"] = ";".join(entry["reasons"])
            writer.writerow(entry)
    print(f"Exported {len(entries)} entries to {output_path}")


def generate_summary(entries: List[Dict[str, Any]]) -> None:
    """Print summary statistics."""
    if not entries:
        print("No entries for summary.")
        return
    total = len(entries)
    severity_counts = Counter(e.get("severity") for e in entries)
    route_counts = Counter(e.get("route") for e in entries)
    doc_type_counts = Counter(e.get("doc_type") for e in entries)
    operator_counts = Counter(e.get("operator_id") for e in entries)
    
    # Average confidences (type: ignore for analyzer false positives)
    class_confs = [e.get("classification_confidence") for e in entries if e.get("classification_confidence") is not None]
    field_confs = [e.get("avg_field_confidence") for e in entries if e.get("avg_field_confidence") is not None]
    avg_class = sum(float(c) for c in class_confs) / len(class_confs) if class_confs else 0.0  # type: ignore[arg-type]
    avg_field = sum(float(c) for c in field_confs) / len(field_confs) if field_confs else 0.0  # type: ignore[arg-type]
    
    # Reason frequency
    reason_counter: Counter = Counter()
    for e in entries:
        reasons = e.get("reasons", [])
        if isinstance(reasons, list):
            reason_counter.update(reasons)
    
    print("\n" + "=" * 60)
    print("ROUTING AUDIT SUMMARY")
    print("=" * 60)
    print(f"Total Entries: {total}")
    print("\nSeverity Breakdown:")
    for sev, count in severity_counts.most_common():
        print(f"  {sev}: {count} ({100*count/total:.1f}%)")
    print("\nRoute Breakdown:")
    for route, count in route_counts.most_common():
        print(f"  {route}: {count} ({100*count/total:.1f}%)")
    print("\nDocument Type Breakdown:")
    for dtype, count in doc_type_counts.most_common():
        print(f"  {dtype}: {count} ({100*count/total:.1f}%)")
    print("\nOperator Breakdown:")
    for op, count in operator_counts.most_common():
        print(f"  {op}: {count} ({100*count/total:.1f}%)")
    print(f"\nAverage Classification Confidence: {avg_class:.4f}")
    print(f"Average Field Confidence: {avg_field:.4f}")
    print("\nTop 5 Routing Reasons:")
    for reason, count in reason_counter.most_common(5):
        print(f"  {reason}: {count}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Export and analyze routing audit logs.")
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Input JSONL file(s). Supports wildcards (e.g., data/routing_audit_*.jsonl).",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output CSV file path (required unless --summary used).",
    )
    parser.add_argument(
        "--summary",
        "-s",
        action="store_true",
        help="Print summary statistics instead of exporting CSV.",
    )
    args = parser.parse_args()
    
    # Expand wildcards
    input_files = []
    for pattern in args.input.split():
        input_files.extend(glob.glob(pattern))
    
    if not input_files:
        print(f"No files matched pattern: {args.input}")
        return
    
    print(f"Processing {len(input_files)} file(s)...")
    all_entries = []
    for fpath in input_files:
        entries = parse_jsonl(fpath)
        all_entries.extend(entries)
        print(f"  Loaded {len(entries)} entries from {fpath}")
    
    if args.summary:
        generate_summary(all_entries)
    else:
        if not args.output:
            print("Error: --output required unless --summary specified.")
            return
        export_to_csv(all_entries, args.output)


if __name__ == "__main__":
    main()
