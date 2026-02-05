# CMU Babel SLURM Submission - Quick Start

## Quick Commands

### Submit Job with Email
```bash
sbatch --export=EMAIL=your.email@cmu.edu submit_200k_setup.sh
```

### Submit and Get Job ID
```bash
job_id=$(sbatch --export=EMAIL=your.email@cmu.edu submit_200k_setup.sh | awk '{print $4}')
echo "Job submitted: $job_id"
```

### Monitor Job
```bash
squeue -j <JOB_ID>           # Check job status
tail -f logs/slurm/bioasq_200k_setup_<JOB_ID>.log  # Follow logs
```

## SLURM Script Details

**File**: `submit_200k_setup.sh`  
**Time**: 90 minutes  
**Resources**: 1 node, 4 CPUs, 16 GB RAM  
**Partition**: general  

## Required Parameter

**Email** (for PubMed API): Pass via environment variable
```bash
sbatch --export=EMAIL=your.email@cmu.edu submit_200k_setup.sh
```

## What It Does

1. Activates Python virtual environment
2. Validates prerequisites (email, Elasticsearch connectivity)
3. Runs 200K corpus setup (50-60 minutes):
   - Samples 200K documents with publication date fetching
   - Deletes old Elasticsearch index
   - Ingests sampled corpus
4. Reports summary with execution time

## After Job Completes

Verify setup:
```bash
python scripts/verify_setup.py --config configs/pipeline_config.yaml
```

## Logs Location

- Main output: `logs/slurm/bioasq_200k_setup_<JOB_ID>.log`
- Error output: `logs/slurm/bioasq_200k_setup_<JOB_ID>.err`

## More Information

See [SLURM_SETUP.md](SLURM_SETUP.md) for detailed documentation.
