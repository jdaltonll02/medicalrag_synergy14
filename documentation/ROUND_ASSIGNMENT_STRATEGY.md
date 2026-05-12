# BioASQ Synergy Round Assignment Strategy

## Overview

This document explains how the 200K sampled corpus is divided between BioASQ Synergy Round 1 and Round 2 using publication date information from PubMed.

## BioASQ Snapshot Dates

BioASQ Synergy uses official PubMed snapshots as the source for each round's document collection:

- **Round 1 Snapshot**: January 9, 2026 (PubMed version effective as of 2026-01-09)
- **Round 2 Snapshot**: January 22, 2026 (PubMed version effective as of 2026-01-22)

Each snapshot includes the Annual Baseline Repository for 2026 plus all daily updates up to and including the snapshot date.

## Document Assignment Logic

Documents are assigned to rounds based on their **publication date** (when the document was published, not when it was indexed):

```
Round 1: publication_date <= 2026-01-09
Round 2: 2026-01-09 < publication_date <= 2026-01-22
```

This ensures:
1. Documents in Round 1 were available in the official PubMed snapshot for Round 1
2. Documents in Round 2 were new additions between the two snapshots
3. No document appears in both rounds
4. The temporal distribution reflects actual BioASQ evaluation conditions

## Implementation Details

### Data Source
Publication dates are fetched from the NCBI Entrez API using PubMedFetcher, which:
- Queries PubMed for document metadata
- Extracts the official publication date
- Handles various date formats (YYYY-MM-DD, YYYY-MM, YYYY)
- Uses batched requests with rate limiting to respect API quotas

### Sampling Process
1. **Random Sample**: 200,000 documents are randomly selected from the full 33M corpus
2. **Date Fetching**: Publication dates are retrieved for all sampled documents (40-55 minutes)
3. **Round Assignment**: Documents are assigned based on comparison with snapshot dates
4. **Metadata Enrichment**: Round information is added to each document record

### Timeline
- Sampling operation: 40-55 minutes
  - ~2-3 minutes: Load and sample PMIDs
  - ~35-50 minutes: Fetch publication dates from PubMed API
  - ~1-2 minutes: Assign rounds and write output

## Why This Approach

The original corpus file contains only `pmid`, `title`, and `abstract` fields—no publication date metadata. Therefore:

1. **Publication dates cannot be inferred from document position**: Unlike some corpora, PMIDs are not sequentially issued by publication date
2. **External data source required**: PubMed is the authoritative source for publication dates
3. **Accuracy over speed**: 40-55 minutes ensures correct round assignment, which is critical for fair evaluation

## API Requirements

To run the sampling process:
- **Email address**: Required by NCBI Entrez API for identification and rate limiting
- **Internet connection**: Must communicate with PubMed servers
- **API key** (optional): Can improve rate limits if provided

Pass email with `--email your.email@example.com` when running the setup script.

## Verification

After sampling, verify round distribution:

```bash
python scripts/verify_setup.py --config configs/pipeline_config.yaml
```

Expected output includes:
- Round 1 document count (approximately 100,000)
- Round 2 document count (approximately 100,000)
- Publication date ranges for each round

## Related Files

- `scripts/sample_corpus.py` - Implementation of sampling with date-based round assignment
- `src/core/pubmed_fetcher.py` - PubMedFetcher class for API access
- `setup_200k_corpus.sh` - Master orchestration script
- `SETUP_200K_CORPUS.md` - Complete setup guide
