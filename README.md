# MusicGen Batch Generation System

Generate multiple AI music files from text prompts using AWS cloud infrastructure. Cost-effective batch processing with GPU on-demand instances.

## 🚀 Quick Start

### 1. Prerequisites Setup
```bash
# Install dependencies
uv sync

# Test AWS connectivity  
uv run python check_aws_readiness.py
```

### 2. Configuration
- Update `.env` file with your AWS settings
- **CRITICAL**: Update `config.py` line 94 with your git repository URL
- Edit `prompts.txt` with your music prompts

### 3. Launch & Monitor
```bash
# Launch worker (shows pricing first, asks for confirmation)
uv run python launcher.py

# Monitor progress in real-time ⭐
uv run python monitor_worker.py system

# Check outputs
uv run python monitor_worker.py s3
```

### 4. Cleanup
**⚠️ CRITICAL**: Manually terminate EC2 instance when complete to avoid charges!
- Go to AWS Console → EC2 → Instances → Terminate

## 📋 What It Does

1. **Launcher** shows on-demand pricing and launches GPU instance
2. **Worker** downloads MusicGen model, processes prompts, uploads .wav files to S3
3. **Cost Report** tracks generation time and estimated costs per file

## 💰 Expected Costs

- **Test run** (2-4 short prompts): $0.20 - $0.50
- **Full batch** (10+ prompts): $1.00 - $3.00
- Based on $0.526/hour on-demand rate for g4dn.xlarge

## 📁 Project Structure

```
├── launcher.py          # Launch on-demand instances
├── worker.py           # Generate music on EC2
├── monitor_worker.py   # Log monitoring with sub-commands
├── prompts.txt         # Your music prompts
├── config.py          # AWS configuration
├── .env               # Your AWS credentials
└── docs/
    ├── EXECUTION_GUIDE.md    # Detailed step-by-step
    ├── LOGGING_GUIDE.md      # Monitoring & troubleshooting
    └── SPEC.md              # Technical specification
```

## 🎵 Prompt Format

Edit `prompts.txt` with this format:
```
# Comments start with #
upbeat electronic dance music with heavy bass ; 30 ; dance_track
cinematic orchestral music with epic drums ; 180 ; epic_movie
relaxing acoustic guitar melody ; 60 ; chill_guitar
```

Format: `PROMPT_TEXT ; DURATION_IN_SECONDS ; FILENAME`

## 🎯 Easy Monitoring Commands

Once your worker is running:

### Basic Monitoring
```bash
uv run python monitor_worker.py status      # Instance status
uv run python monitor_worker.py logs        # Recent worker logs
uv run python monitor_worker.py tail        # Live worker logs ⭐
uv run python monitor_worker.py s3          # Check outputs
uv run python monitor_worker.py ssh         # SSH access
```

### Monitoring Different Phases

**🚀 For System Setup/Bootstrap:**
```bash
uv run python monitor_worker.py bootstrap   # Bootstrap completion status
uv run python monitor_worker.py system      # Live system logs (uv sync, model download)
```

**🎵 For Music Generation:**
```bash
uv run python monitor_worker.py tail        # Live worker logs (generation progress)
```

### Monitoring Guide

**During Launch Phase:** 
- `monitor_worker.py system` - Shows uv setup, git clone, model download
- `monitor_worker.py bootstrap` - Check if bootstrap completed successfully

**During Generation Phase:**
- `monitor_worker.py tail` - Shows music generation progress, timings, costs
- `monitor_worker.py s3` - Check generated files in S3 bucket

**For Troubleshooting:**
- `monitor_worker.py bootstrap` - Debug startup/setup issues
- `monitor_worker.py logs` - Recent worker logs without live follow

## ⚡ Quick Test Run

1. **Safe test first** (no AWS resources):
   ```bash
   uv run python launcher.py
   # Shows pricing, type 'no' to exit safely
   ```

2. **Minimal test** (creates resources):
   ```bash
   # Edit prompts.txt to have only 1-2 short prompts (30-60s)
   uv run python launcher.py
   # Type 'yes' to launch, then monitor with:
   uv run python monitor_worker.py system  # Shows bootstrap → worker transition
   ```

3. **Remember to terminate** instance when complete!

## 🔧 Configuration Files

### `.env` (your AWS settings)
```bash
AWS_ACCOUNT_ID=your-account-id
AWS_REGION=us-west-2
S3_BUCKET_NAME=your-bucket-name
KEY_PAIR_NAME=your-key-pair
INSTANCE_TYPE=g4dn.xlarge
IAM_ROLE_NAME=your-iam-role
AMI_ID=ami-xxxxxxxxx
```

### Requirements
- AWS account with EC2 and S3 access
- S3 bucket for outputs
- EC2 key pair for SSH access  
- IAM role with S3 permissions
- Deep Learning AMI (Ubuntu) with GPU support

## 📊 Outputs

All files go to your S3 bucket:
- `*.wav` - Generated music files  
- `cost_report.csv` - Generation times and costs

Example cost report:
```csv
s3_filename,prompt,requested_duration_s,generation_time_s,estimated_cost_usd
abc123_dance.wav,upbeat electronic music,30,45.2,0.005
def456_epic.wav,cinematic orchestral,180,234.7,0.026
```

## 🚨 Important Warnings

- **Manual shutdown required** - EC2 instances don't auto-terminate
- **First run slower** - Downloads 6GB model (~10 minutes)
- **Cost estimates** - Based on fixed on-demand pricing

## 🔍 Troubleshooting

### Common Issues

**Launcher fails:**
```bash
uv run python check_aws_readiness.py  # Verify permissions
```

**Worker crashes:**
```bash
uv run python monitor_worker.py logs       # Check recent error messages
uv run python monitor_worker.py bootstrap  # Check startup/setup issues
uv run python monitor_worker.py system     # Follow live system logs
uv run python monitor_worker.py ssh        # SSH for debugging
```

**No outputs:**
- Check worker logs for generation errors
- Verify S3 bucket permissions
- Ensure prompts.txt format is correct

### Getting Help

1. Check `docs/LOGGING_GUIDE.md` for detailed troubleshooting
2. Run `uv run python monitor_worker.py status` for quick diagnostics
3. Review worker logs with `uv run python monitor_worker.py logs`

## 🎼 Example Workflow

```bash
# 1. Test configuration
uv run python check_aws_readiness.py

# 2. Dry run (safe, no charges)
uv run python launcher.py  # type 'no' to exit

# 3. Real launch with minimal test
# Edit prompts.txt to have 1-2 short samples first
uv run python launcher.py  # type 'yes' to launch

# 4. Monitor progress (system setup → worker)
uv run python monitor_worker.py system

# 5. Check results  
uv run python monitor_worker.py s3

# 6. ⚠️ TERMINATE INSTANCE when complete
# AWS Console → EC2 → Instances → Terminate
```

## 📚 Documentation

- **`docs/EXECUTION_GUIDE.md`** - Detailed step-by-step instructions
- **`docs/LOGGING_GUIDE.md`** - Monitoring and troubleshooting  
- **`docs/SPEC.md`** - Technical architecture and verification

## 🎯 Success Criteria

✅ System working correctly when:
- Launcher shows on-demand pricing
- Instance launches successfully  
- Worker detects GPU and loads MusicGen model
- Prompts generate .wav files in S3
- Cost report uploaded with accurate calculations
- Manual instance termination completes cleanup

**Ready to generate AI music at scale!** 🎵