# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a batch MusicGen generation system designed to generate multiple long-form audio files (3-5+ minutes) from text prompts using AWS cloud infrastructure. The system prioritizes cost-effectiveness by using EC2 spot instances and is designed for batch processing rather than real-time interaction.

## Key Architecture Components

### 1. Local Control Script (`launcher.py`)
- **Purpose**: Manages EC2 spot instance lifecycle
- **Key Functions**:
  - Checks for existing instances with tag `musicgen-batch-worker`
  - Displays current spot pricing before requesting instances
  - Submits spot requests with user-defined max price
  - Uses boto3 for AWS API interactions

### 2. Cloud Worker Instance (AWS EC2)
- **Instance Type**: g4dn.xlarge (NVIDIA T4 GPU) or equivalent
- **Pricing**: Spot instances with configurable max price (e.g., $0.40/hr)
- **AMI Requirements**: Custom AMI based on AWS Deep Learning AMI (Ubuntu) with:
  - NVIDIA drivers and CUDA
  - Python 3, Git
  - Required libraries: torch, transformers, boto3
- **IAM Role**: Minimum permissions for s3:PutObject and s3:HeadObject

### 3. Worker Script (`worker.py`)
- **Purpose**: Core audio generation logic
- **Key Features**:
  - Loads MusicGen model into GPU memory
  - Processes jobs from `prompts.txt` with idempotency checks
  - Implements chunking/continuation for long audio generation
  - Tracks generation time and calculates costs
  - Uploads results to S3 with cleanup

### 4. Job Definition (`prompts.txt`)
- **Format**: Plain text with structure: `PROMPT_TEXT ; DURATION_IN_SECONDS ; FILE_NAME`
- **Location**: Repository root
- **Features**: Supports comments with `#` prefix

### 5. Storage and Reporting
- **S3 Bucket**: Stores .wav files and cost reports
- **Cost Report**: CSV with columns: s3_filename, prompt, requested_duration_s, generation_time_s, estimated_cost_usd

## Development Guidelines

### Cost Management
- The `HOURLY_COST_USD` variable in `worker.py` must match the max spot price in `launcher.py`
- Cost calculations use max spot price as upper bound, not actual AWS charges
- All cost estimates are included in the final `cost_report.csv`

### Error Handling
- Wrap generation logic in try-except blocks to handle model crashes
- Implement idempotency checks to prevent duplicate work on restarts
- Skip processing if output files already exist in S3

### AWS Configuration
- Use spot instances exclusively for cost savings
- Implement proper IAM roles with minimal required permissions
- Tag EC2 instances with `musicgen-batch-worker` for identification

### File Processing
- Parse `prompts.txt` line by line, ignoring comment lines
- Generate deterministic output filenames for idempotency
- Use temporary local storage before S3 upload, then cleanup

## Key Implementation Considerations

### Risk Mitigations
1. **Spot Instance Interruption**: Implement idempotency to resume from interruptions
2. **Model Crashes**: Use exception handling to continue processing remaining prompts
3. **Cost Overruns**: Manual EC2 shutdown required (biggest operational risk)
4. **Race Conditions**: S3 checks provide basic locking for concurrent executions

### Out of Scope (v1.1)
- Automated EC2 shutdown
- Web UI or API interfaces  
- Real-time spot price querying for cost calculations

## Testing Instructions
Manual testing is preferred for this system:
1. Test launcher.py with dry-run spot requests
2. Verify worker.py processes sample prompts correctly
3. Confirm S3 uploads and cost report generation
4. Test idempotency by running worker.py multiple times with same prompts

## Development Commands
This is a Python project managed with uv. Typical commands include:
- `uv sync` - Install/sync dependencies 
- `uv run python launcher.py` - Start the batch generation process
- `uv run python worker.py` - Run worker script (typically executed on EC2)
- AWS CLI commands for managing S3 buckets and EC2 instances

## Project Structure
This project uses uv for dependency management:
- `pyproject.toml` - Project configuration and dependencies
- `uv.lock` - Locked dependency versions
- `.venv/` - Virtual environment (created by uv)

## Environment Considerations
- **DO NOT** attempt to run AWS console commands or Python scripts from within Claude Code
- **DO NOT** run git commands (add, commit, push) - the user handles all git operations
- This code is developed in WSL, but the user runs AWS and application work from Windows in a separate console
- Claude should focus on code editing, analysis, and planning rather than execution