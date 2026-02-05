# CMU Babel Cluster - SLURM Job Submission

## Overview

The `submit_200k_setup.sh` script is a SLURM job submission script for running the 200K corpus setup on CMU's Babel cluster compute nodes.

## Job Specifications

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Partition** | general | Standard compute resources |
| **Nodes** | 1 | Single-node job (no MPI needed) |
| **CPUs** | 4 | Sufficient for document processing + PubMed API calls |
| **Memory** | 16 GB | Safe margin for corpus sampling and ingestion |
| **Time Limit** | 90 minutes | Accounts for 50-60 min execution + overhead |
| **Output Log** | logs/slurm/bioasq_200k_setup_*.log | SLURM job logs |
| **Error Log** | logs/slurm/bioasq_200k_setup_*.err | Separate error output |

## Usage

### Method 1: Command-Line Argument
```bash
sbatch submit_200k_setup.sh your.email@example.com
```

### Method 2: Environment Variable
```bash
sbatch --export=EMAIL=your.email@example.com submit_200k_setup.sh
```

### Method 3: Combined Options
```bash
sbatch --partition=general --mem=16GB --export=EMAIL=your.email@example.com submit_200k_setup.sh
```

## Email Parameter

**IMPORTANT**: The `--email` parameter is required by the PubMed API for rate limiting.

Provide your email in one of these ways:
- Pass as first argument: `sbatch submit_200k_setup.sh your.email@cmu.edu`
- Set environment variable: `export EMAIL=your.email@cmu.edu`
- Use SLURM export: `--export=EMAIL=your.email@cmu.edu`

## What the Script Does

1. **Validation** (< 1 min)
   - Checks email parameter is provided
   - Verifies Python environment
   - Checks Elasticsearch connectivity
   
2. **Setup Execution** (50-60 min)
   - Activates Python virtual environment
   - Runs `setup_200k_corpus.sh` with proper parameters
   - Tracks execution time
   
3. **Summary** (< 1 min)
   - Reports success/failure
   - Shows total execution time
   - Provides next steps

## Monitoring the Job

### Check Job Status
```bash
# View all your jobs
squeue -u $USER

# View specific job
squeue -j <JOB_ID>

# Check job details
sinfo -s
```

### View Logs While Running
```bash
# Follow main log
tail -f logs/slurm/bioasq_200k_setup_<JOB_ID>.log

# Follow error log
tail -f logs/slurm/bioasq_200k_setup_<JOB_ID>.err
```

### View Logs After Job Completes
```bash
# View complete logs
cat logs/slurm/bioasq_200k_setup_<JOB_ID>.log
cat logs/slurm/bioasq_200k_setup_<JOB_ID>.err
```

## Email Notifications

The script is configured to send email notifications:
- `BEGIN`: When job starts
- `END`: When job completes successfully
- `FAIL`: If job fails

Email is sent to the address provided via `--mail-user` SLURM parameter (uses EMAIL environment variable by default).

## Resource Customization

### For Faster Processing (if partition available)
```bash
sbatch --partition=high-priority --cpus-per-task=8 \
    --export=EMAIL=your.email@cmu.edu submit_200k_setup.sh
```

### For Lower Resource Usage
```bash
sbatch --mem=8GB --cpus-per-task=2 \
    --export=EMAIL=your.email@cmu.edu submit_200k_setup.sh
```

Note: Reducing resources may increase execution time.

## Troubleshooting

### Job Fails with "Email not specified"
**Solution**: Provide email address using one of the methods above:
```bash
sbatch --export=EMAIL=your.email@cmu.edu submit_200k_setup.sh
```

### Elasticsearch Not Accessible
**Problem**: Job proceeds but ingestion fails because Elasticsearch isn't running
**Solution**: Start Elasticsearch before submitting job (check with your cluster administrators)

### Job Exceeds Time Limit
**Problem**: Job killed after 90 minutes
**Solution**: Request longer time with:
```bash
sbatch --time=120:00 --export=EMAIL=your.email@cmu.edu submit_200k_setup.sh
```

### Out of Memory
**Problem**: Job killed due to memory constraints
**Solution**: Request more memory:
```bash
sbatch --mem=32GB --export=EMAIL=your.email@cmu.edu submit_200k_setup.sh
```

## After Job Completes

Once the SLURM job finishes successfully:

1. **Verify Setup**
   ```bash
   python scripts/verify_setup.py --config configs/pipeline_config.yaml
   ```

2. **Check Corpus Statistics**
   ```bash
   curl http://localhost:9200/medical_docs/_count
   ```

3. **View Sample Document**
   ```bash
   curl http://localhost:9200/medical_docs/_search?size=1
   ```

## Example Full Workflow

```bash
# 1. Set email environment variable
export EMAIL="your.email@cmu.edu"

# 2. Submit job
job_id=$(sbatch --export=EMAIL=$EMAIL submit_200k_setup.sh | awk '{print $4}')
echo "Submitted job: $job_id"

# 3. Monitor job
watch -n 10 "squeue -j $job_id"

# 4. View logs once complete
cat logs/slurm/bioasq_200k_setup_${job_id}.log

# 5. Verify setup
python scripts/verify_setup.py --config configs/pipeline_config.yaml
```

## Files Created/Modified

| File | Purpose |
|------|---------|
| `submit_200k_setup.sh` | SLURM job submission script |
| `SLURM_SETUP.md` | This documentation |
| `logs/slurm/` | Job output logs directory (created at runtime) |

## Related Documentation

- [QUICK_START_200K.md](QUICK_START_200K.md) - Quick reference for local execution
- [SETUP_200K_CORPUS.md](SETUP_200K_CORPUS.md) - Comprehensive setup guide
- [ROUND_ASSIGNMENT_STRATEGY.md](ROUND_ASSIGNMENT_STRATEGY.md) - Round assignment explanation

## Support

For Babel cluster-specific issues:
- Contact: CMU HPC Support (https://www.cmu.edu/computing/)
- Check cluster status: `sinfo`
- Partition availability: `sinfo -N`

For medrag-specific issues:
- See [SETUP_200K_CORPUS.md](SETUP_200K_CORPUS.md)
- Contact: Project maintainer
