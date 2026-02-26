#!/usr/bin/env python3
"""
sample_corpus.py
----------------
Sample 400k documents from the full PubMed corpus based on BioASQ Synergy round snapshots

Sampling strategy:
- Uses PubMed snapshot dates to assign documents to rounds
- Round 1: Documents published <= 2026-01-09
- Round 2: Documents published between 2026-01-09 and 2026-01-22
- Round 3: Documents published between 2026-01-22 and 2026-02-08
- Round 4: Documents published between 2026-02-08 and 2025-02-19
- Fetches publication dates from PubMed for accurate round assignment

Usage:
    python scripts/sample_corpus.py \
        --input /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus.jsonl \
        --output /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_400k.jsonl \
        --sample-size 200000 \
        --round1-date 2026-01-09 \
        --round2-date 2026-01-22 \
        --round3-date 2026-02-08 \
        --round4-date 2025-02-19 \
        --email jgibson2@andrew.cmu.edu
"""

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import PubMed fetcher from the project
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.core.pubmed_fetcher import PubMedFetcher


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        logger.warning(f"Could not parse date: {date_str}")
        return None


def get_pmid_publication_dates(
    pmids: List[str],
    fetcher: PubMedFetcher,
    batch_size: int = 100
) -> Dict[str, Optional[str]]:
    """
    Fetch publication dates for PMIDs from PubMed
    
    Args:
        pmids: List of PubMed IDs
        fetcher: PubMedFetcher instance
        batch_size: Batch size for fetching
    
    Returns:
        Dict mapping PMID -> pub_date (YYYY-MM-DD or None)
    """
    
    dates = {}
    total = len(pmids)
    
    logger.info(f"Fetching publication dates for {total:,} documents...")
    
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i+batch_size]
        try:
            articles = fetcher.fetch_abstracts(batch)
            for pmid in batch:
                if pmid in articles:
                    pub_date = articles[pmid].get('pub_date')
                    dates[pmid] = pub_date
                else:
                    dates[pmid] = None
            
            if i % 1000 == 0:
                logger.info(f"Fetched dates for {min(i+batch_size, total):,}/{total:,} documents...")
        except Exception as e:
            logger.warning(f"Error fetching batch {i//batch_size}: {e}")
            for pmid in batch:
                dates[pmid] = None
    
    return dates


def assign_to_rounds(
    pmids: List[str],
    pub_dates: Dict[str, Optional[str]],
    round1_date: str,
    round2_date: str,
    round3_date: str,
    round4_date: str
) -> Tuple[List[str], List[str], List[str]]:
    """
    Assign PMIDs to rounds based on publication dates
    
    Args:
        pmids: List of PubMed IDs
        pub_dates: Dict mapping PMID -> pub_date
        round1_date: Round 1 snapshot date (YYYY-MM-DD)
        round2_date: Round 2 snapshot date (YYYY-MM-DD)
        round3_date: Round 3 snapshot date (YYYY-MM-DD)
        round4_date: Round 4 snapshot date (YYYY-MM-DD)
    
    Returns:
        Tuple of (round1_pmids, round2_pmids, round3_pmids, round4_pmids)
    """
    round1_cutoff = parse_date(round1_date)
    round2_cutoff = parse_date(round2_date)
    round3_cutoff = parse_date(round3_date)
    round4_cutoff = parse_date(round4_date)
    round1_pmids = []
    round2_pmids = []
    round3_pmids = []
    round4_pmids = []
    unassigned = []
    for pmid in pmids:
        pub_date_str = pub_dates.get(pmid)
        if not pub_date_str:
            unassigned.append(pmid)
            continue
        try:
            pub_date = parse_date(pub_date_str)
            if not pub_date:
                unassigned.append(pmid)
                continue
            if pub_date <= round1_cutoff:
                round1_pmids.append(pmid)
            elif pub_date <= round2_cutoff:
                round2_pmids.append(pmid)
            elif pub_date <= round3_cutoff:
                round3_pmids.append(pmid)
            elif pub_date <= round4_cutoff:
                round4_pmids.append(pmid)
            else:
                round4_pmids.append(pmid)
        except Exception as e:
            logger.warning(f"Error parsing date for {pmid}: {e}")
            unassigned.append(pmid)
    if unassigned:
        random.shuffle(unassigned)
        split1 = len(unassigned) // 4
        split2 = 2 * len(unassigned) // 4
        split3 = 3 * len(unassigned) // 4
        round1_pmids.extend(unassigned[:split1])
        round2_pmids.extend(unassigned[split1:split2])
        round3_pmids.extend(unassigned[split2:split3])
        round4_pmids.extend(unassigned[split3:])
        logger.info(f"Assigned {len(unassigned)} documents with missing dates")
    return round1_pmids, round2_pmids, round3_pmids, round4_pmids


def sample_corpus(
    input_path: str,
    output_path: str,
    sample_size: int = 400000,
    round1_size: int = 100000,
    round2_size: int = 100000,
    round3_size: int = 100000,
    round4_size: int = 100000,
    round1_date: str = "2026-01-09",
    round2_date: str = "2026-01-22",
    round3_date: str = "2026-02-08",
    round4_date: str = "2025-02-19",
    email: Optional[str] = None,
    api_key: Optional[str] = None
) -> Tuple[int, int, int, int, int, int]:
    """
    Sample documents from corpus based on BioASQ Synergy round snapshots
    
    Args:
        input_path: Path to input JSONL corpus
        output_path: Path to output JSONL corpus
        sample_size: Total documents to sample (default 400k)
        round1_size: Documents for round 1 (default 100K)
        round1_date: Round 1 snapshot date (YYYY-MM-DD)
        round2_date: Round 2 snapshot date (YYYY-MM-DD)
        round3_date: Round 3 snapshot date (YYYY-MM-DD)
        round4_date: Round 4 snapshot date (YYYY-MM-DD)
        email: Email for PubMed API
        api_key: Optional NCBI API key
    
    Returns:
        Tuple of (total_sampled, round1_count, round2_count, round3_count, round4_count, documents_written)
    """
    
    logger.info("=== BioASQ Synergy Corpus Sampling ===")
    logger.info(f"Round 1 snapshot date: {round1_date}")
    logger.info(f"Round 2 snapshot date: {round2_date}")
    logger.info(f"Round 3 snapshot date: {round3_date}")
    logger.info(f"Round 4 snapshot date: {round4_date}")
    logger.info(
        "Target sample sizes: "
        f"{round1_size} round 1 + {round2_size} round 2 + {round3_size} round 3 + {round4_size} round 4"
    )
    logger.info("")
    
    # Initialize PubMed fetcher
    if not email:
        logger.error("Email is required for PubMed API access")
        return 0, 0, 0, 0
    
    fetcher = PubMedFetcher(email=email, api_key=api_key)
    
    # Pass 1: Count total documents
    logger.info(f"Counting documents in {input_path}...")
    total_docs = 0
    with open(input_path, 'r') as f:
        for idx, line in enumerate(f):
            if idx % 1000000 == 0 and idx > 0:
                logger.info(f"Counted {idx:,} documents...")
            total_docs += 1
    
    logger.info(f"Total documents in corpus: {total_docs:,}")
    logger.info("")
    
    # Generate random line indices to sample
    logger.info(f"Generating {sample_size:,} random sample indices...")
    sample_indices = set(random.sample(range(total_docs), min(sample_size, total_docs)))
    logger.info(f"Will sample documents at {len(sample_indices):,} positions")
    logger.info("")
    
    # Pass 2: Read only sampled documents
    logger.info(f"Reading sampled documents from {input_path}...")
    sampled_docs = []
    sampled_pmids = []
    
    with open(input_path, 'r') as f:
        for idx, line in enumerate(f):
            if idx in sample_indices:
                doc = json.loads(line)
                pmid = doc.get('pmid')
                if pmid:
                    sampled_pmids.append(pmid)
                    sampled_docs.append(doc)
            
            if idx % 1000000 == 0 and idx > 0:
                logger.info(f"Processed {idx:,} documents, found {len(sampled_docs):,} samples...")
    
    logger.info(f"Sampled {len(sampled_docs):,} documents")
    logger.info("")
    
    # Fetch publication dates
    pub_dates = get_pmid_publication_dates(sampled_pmids, fetcher)
    logger.info(f"Successfully fetched dates for {sum(1 for d in pub_dates.values() if d)} documents")
    logger.info("")
    
    # Assign to rounds based on publication dates
    logger.info("Assigning documents to rounds based on publication dates...")
    round1_pmids, round2_pmids, round3_pmids, round4_pmids = assign_to_rounds(
        sampled_pmids,
        pub_dates,
        round1_date,
        round2_date,
        round3_date,
        round4_date
    )
    logger.info(f"Round 1 documents: {len(round1_pmids):,}")
    logger.info(f"Round 2 documents: {len(round2_pmids):,}")
    logger.info(f"Round 3 documents: {len(round3_pmids):,}")
    logger.info(f"Round 4 documents: {len(round4_pmids):,}")
    logger.info("")
    
    # Write sampled documents
    logger.info(f"Writing documents to {output_path}...")
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    round1_set = set(round1_pmids)
    round2_set = set(round2_pmids)
    round3_set = set(round3_pmids)
    round4_set = set(round4_pmids)
    docs_written = 0
    # Create a map of PMID -> doc for quick lookup
    pmid_to_doc = {doc['pmid']: doc for doc in sampled_docs}
    with open(output_path, 'w') as outfile:
        for pmid in sampled_pmids:
            if pmid in pmid_to_doc:
                doc = pmid_to_doc[pmid]
                # Add round assignment based on publication date
                if pmid in round1_set:
                    doc['snapshot_round'] = 1
                elif pmid in round2_set:
                    doc['snapshot_round'] = 2
                elif pmid in round3_set:
                    doc['snapshot_round'] = 3
                elif pmid in round4_set:
                    doc['snapshot_round'] = 4
                else:
                    doc['snapshot_round'] = -1  # Should not happen
                outfile.write(json.dumps(doc, ensure_ascii=False) + '\n')
                docs_written += 1
    
    logger.info(f"Successfully wrote {docs_written} documents to {output_path}")
    logger.info("")
    return len(sampled_pmids), len(round1_pmids), len(round2_pmids), len(round3_pmids), len(round4_pmids), docs_written


def main():
    parser = argparse.ArgumentParser(
        description="Sample 200K documents from PubMed corpus using BioASQ Synergy snapshot dates"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input JSONL corpus (full corpus)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output JSONL corpus (sampled 200K)"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=300000,
        help="Total documents to sample (default 300000)"
    )
    parser.add_argument(
        "--round1-size",
        type=int,
        default=100000,
        help="Documents to sample for round 1 (default 100000)"
    )
    parser.add_argument(
        "--round2-size",
        type=int,
        default=100000,
        help="Documents to sample for round 2 (default 100000)"
    )
    parser.add_argument(
        "--round1-date",
        default="2026-01-09",
        help="Round 1 snapshot date (YYYY-MM-DD, default 2026-01-09)"
    )
    parser.add_argument(
        "--round2-date",
        default="2026-01-22",
        help="Round 2 snapshot date (YYYY-MM-DD, default 2026-01-22)"
    )
    parser.add_argument(
        "--round3-date",
        default="2026-02-08",
        help="Round 3 snapshot date (YYYY-MM-DD, default 2026-02-08)"
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email for PubMed API access"
    )
    parser.add_argument(
        "--api-key",
        help="Optional NCBI API key for faster PubMed access"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default 42)"
    )
    
    args = parser.parse_args()
    
    # Set random seed for reproducibility
    random.seed(args.seed)
    logger.info(f"Using random seed: {args.seed}")
    logger.info("")
    
    try:
        sampled, round1, round2, round3, written = sample_corpus(
            args.input,
            args.output,
            args.sample_size,
            args.round1_size,
            args.round2_size,
            args.round1_date,
            args.round2_date,
            args.round3_date,
            args.email,
            args.api_key
        )
        logger.info(f"\n=== Sampling Complete ===")
        logger.info(f"Documents sampled: {sampled:,}")
        logger.info(f"  Round 1 (≤ {args.round1_date}): {round1:,}")
        logger.info(f"  Round 2 ({args.round1_date} < date ≤ {args.round2_date}): {round2:,}")
        logger.info(f"  Round 3 ({args.round2_date} < date ≤ {args.round3_date}): {round3:,}")
        logger.info(f"Documents written: {written:,}")
        logger.info(f"Output file: {args.output}")
        
    except Exception as e:
        logger.error(f"Error during sampling: {e}")
        raise


if __name__ == "__main__":
    main()
