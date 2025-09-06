# MusicGen Batch Generation System

Generate AI music from text prompts using AWS GPU instances. Cost-effective batch processing.

## 🚀 Quick Start

### 1. Setup
```bash
# Install dependencies
uv sync

# Configure AWS settings in .env file
# Update config.py line 103 with your git repository URL
```

### 2. Create Music Prompts
Edit `prompts.txt` with this format:
```
# Comments start with #
upbeat electronic dance music with heavy bass ; 30 ; dance_track
cinematic orchestral music with epic drums ; 180 ; epic_movie
relaxing acoustic guitar melody ; 60 ; chill_guitar
```

Format: `PROMPT_TEXT ; DURATION_IN_SECONDS ; FILENAME`

### 3. Launch & Monitor
```bash
# Launch GPU instance (shows pricing, asks for confirmation)
uv run python launcher.py

# Monitor system setup (uv, model download)
uv run python monitor_worker.py system

# Monitor music generation 
uv run python monitor_worker.py tail

# Check generated files
uv run python monitor_worker.py s3
```

### 4. Get Your Music
```bash
# List all generated files
aws s3 ls s3://your-bucket-name/

# Download specific file
aws s3 cp s3://your-bucket-name/epic_movie_abc123.wav ./

# Download all files
aws s3 sync s3://your-bucket-name/ ./downloads/

# Download cost report
aws s3 cp s3://your-bucket-name/cost_report_latest.csv ./
```

### 5. Cleanup
**⚠️ CRITICAL**: Manually terminate EC2 instance when complete!
- AWS Console → EC2 → Instances → Select instance → Terminate

## 📊 Expected Costs
- **Short test** (2-3 prompts, 30s each): ~$0.20
- **Full batch** (10 prompts, 60-180s each): ~$1-3
- Based on g4dn.xlarge at $0.526/hour + EBS storage

## 🔍 Monitoring Commands

```bash
# Instance status
uv run python monitor_worker.py status

# System setup logs (first 10 minutes)
uv run python monitor_worker.py system

# Worker logs (music generation)
uv run python monitor_worker.py tail

# Bootstrap troubleshooting
uv run python monitor_worker.py bootstrap

# SSH access
uv run python monitor_worker.py ssh

# Check S3 outputs
uv run python monitor_worker.py s3
```

## 🎵 Output Files

Generated in your S3 bucket:
- `*.wav` - Generated music files with deterministic names
- `cost_report_TIMESTAMP.csv` - Generation times and estimated costs
- `cost_report_latest.csv` - Latest cost report

Example cost report:
```csv
s3_filename,prompt,requested_duration_s,generation_time_s,estimated_cost_usd
dance_track_abc123.wav,"upbeat electronic dance music",30,45.2,0.0065
epic_movie_def456.wav,"cinematic orchestral music",180,234.7,0.0342
```

## ⚠️ Important Notes

- **First run takes longer** - downloads 8GB MusicGen model
- **Manual shutdown required** - instances don't auto-terminate  
- **80GB storage** - sufficient for model + temporary files
- **GPU required** - uses g4dn.xlarge with Tesla T4

## 🛠 Configuration Required

Create `.env` file:
```bash
AWS_ACCOUNT_ID=your-account-id
AWS_REGION=us-west-2  
S3_BUCKET_NAME=your-bucket-name
KEY_PAIR_NAME=your-key-pair
IAM_ROLE_NAME=your-iam-role
AMI_ID=ami-xxxxxxxxx
```

Update `config.py` line 103 with your git repository URL.

## 🔧 Troubleshooting

**Instance won't launch:**
```bash
uv run python check_aws_readiness.py
```

**Worker fails:**
```bash
uv run python monitor_worker.py bootstrap  # Check setup
uv run python monitor_worker.py logs       # Recent errors
uv run python monitor_worker.py ssh        # Debug directly
```

**No outputs:**
- Check `monitor_worker.py tail` for errors
- Verify S3 bucket permissions
- Check `prompts.txt` format

**Ready to generate AI music!** 🎵