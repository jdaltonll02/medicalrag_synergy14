#!/usr/bin/env python3
"""
merge_dedup_corpus.py
----------------------
Merge multiple PubMed JSONL corpora and de-duplicate by doc_id/pmid.

- Preserves input order by default (first occurrence wins)
- Optionally prefer latest occurrence with --prefer-new
- Writes a stats JSON alongside output

Example usage (fill in your paths):
  python scripts/merge_dedup_corpus.py \
    --input /path/round1.jsonl /path/round2.jsonl /path/round3.jsonl \
    --output /path/rounds_1_3_corpus.jsonl
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, Tuple


def iter_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            yield json.loads(line)


def get_doc_key(doc: Dict) -> Tuple[str, str]:
    """Return (key_type, key_value) for dedupe."""
    doc_id = doc.get("doc_id")
    pmid = doc.get("pmid")
    if doc_id:
        return ("doc_id", str(doc_id))
    if pmid:
        return ("pmid", str(pmid))
    return ("none", "")


def merge_corpora(inputs: list[Path], output: Path, prefer_new: bool = False) -> Dict:
    seen = {}
    stats = {
        "inputs": [str(p) for p in inputs],
        "total_input_docs": 0,
        "unique_docs": 0,
        "duplicates_removed": 0,
        "missing_ids": 0,
        "by_source": {},
    }

    output.parent.mkdir(parents=True, exist_ok=True)

    # Track order: list of keys for stable ordering
    ordered_keys = []

    for path in inputs:
        source_name = path.name
        stats["by_source"].setdefault(source_name, {"input_docs": 0, "kept_docs": 0, "dupes": 0})

        for doc in iter_jsonl(path):
            stats["total_input_docs"] += 1
            stats["by_source"][source_name]["input_docs"] += 1

            key_type, key_val = get_doc_key(doc)
            if key_type == "none":
                stats["missing_ids"] += 1
                # Treat as unique by appending a counter-based key
                key_val = f"__missing__:{stats['missing_ids']}"
                key_type = "missing"

            key = f"{key_type}:{key_val}"

            if key in seen:
                stats["duplicates_removed"] += 1
                stats["by_source"][source_name]["dupes"] += 1
                if prefer_new:
                    seen[key] = doc
                continue

            seen[key] = doc
            ordered_keys.append(key)
            stats["by_source"][source_name]["kept_docs"] += 1

    # Write output in stable order
    with output.open("w", encoding="utf-8") as f:
        for key in ordered_keys:
            doc = seen.get(key)
            if doc is None:
                continue
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    stats["unique_docs"] = len(seen)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Merge and de-duplicate PubMed JSONL corpora")
    parser.add_argument("--input", nargs="+", required=True, help="Input JSONL files (round1, round2, round3)")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--prefer-new", action="store_true", help="Prefer later documents on key collision")
    args = parser.parse_args()

    inputs = [Path(p) for p in args.input]
    output = Path(args.output)

    stats = merge_corpora(inputs, output, prefer_new=args.prefer_new)
    stats_path = output.with_suffix(".stats.json")
    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print("[OK] Merged corpus written to:", output)
    print("[OK] Stats written to:", stats_path)
    print("[INFO] Total input docs:", stats["total_input_docs"])
    print("[INFO] Unique docs:", stats["unique_docs"])
    print("[INFO] Duplicates removed:", stats["duplicates_removed"])
    print("[INFO] Missing IDs:", stats["missing_ids"])


if __name__ == "__main__":
    main()
