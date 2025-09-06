# MusicGen Worker - Logging & Monitoring Guide

## 📍 Where Logs Are Stored

### Worker Logs (Main Application)
- **Location:** `/var/log/musicgen-worker.log` on EC2 instance
- **Content:** All worker activity - model loading, job processing, S3 uploads, errors
- **Format:** `2025-01-XX XX:XX:XX - LEVEL - MESSAGE`

### Bootstrap Logs (System Setup)
- **Location:** `/var/log/cloud-init-output.log` on EC2 instance  
- **Content:** UserData script execution - package installs, git clone, dependency setup
- **Format:** Raw command output and system messages

## 🎯 Easy Monitoring (RECOMMENDED)

### Use the Monitor Script
```bash
# Show instance status and quick commands
uv run python monitor_worker.py status

# View last 50 log lines
uv run python monitor_worker.py logs

# Follow logs in real-time (best for monitoring progress!)
uv run python monitor_worker.py tail

# SSH to instance for manual debugging
uv run python monitor_worker.py ssh

# Check current S3 outputs
uv run python monitor_worker.py s3
```

### What Each Command Does

**`status`** - Shows:
- Instance ID, state, IP address, type
- Quick SSH command for manual access
- Suggested next commands

**`logs`** - Shows:
- Recent worker log entries (last 50 lines)
- Current worker status
- Any recent errors or progress

**`tail`** - Shows:
- Live log streaming as worker runs
- Real-time progress updates
- Best way to monitor active generation
- Press Ctrl+C to stop following

**`ssh`** - Opens:
- Direct SSH connection to worker instance
- Full shell access for debugging
- Manual log file access

**`s3`** - Lists:
- All files currently in S3 bucket
- File sizes and creation dates
- Shows generation progress

## 📋 Manual Monitoring (Alternative)

If you prefer manual commands or troubleshooting:

### Find Your Worker Instance
```bash
aws ec2 describe-instances \
  --region us-west-2 \
  --filters "Name=tag:Name,Values=musicgen-batch-worker" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]' \
  --output table
```

### SSH to Instance
```bash
ssh -i keys/your-key-pair.pem ubuntu@[INSTANCE_IP]
```

### View Logs Manually (once SSH'd)
```bash
# Worker logs (main application)
tail -f /var/log/musicgen-worker.log

# Bootstrap logs (system setup)  
tail -f /var/log/cloud-init-output.log

# Recent worker activity
tail -50 /var/log/musicgen-worker.log

# Search for errors
grep -i error /var/log/musicgen-worker.log
```

## 🔍 What to Look For in Logs

### Normal Startup Sequence
```
Worker logs will be written to: /var/log/musicgen-worker.log
Monitor logs with: tail -f /var/log/musicgen-worker.log
INFO - Worker initialized - S3 bucket: your-bucket, Hourly cost: $0.40
INFO - Initializing MusicGen model...
INFO - Using GPU: Tesla T4
INFO - Loading facebook/musicgen-medium...
INFO - Model initialization complete
INFO - Found X valid prompts to process
```

### During Job Processing
```
INFO - Processing prompt 1/4: upbeat electronic music...
INFO - Checking if abc123_test_file.wav exists in S3...
INFO - File not found, proceeding with generation...
INFO - Generating audio for 30s...
INFO - Audio generated successfully, duration: 30 seconds
INFO - Generation time: 45.2 seconds, Cost: $0.005
INFO - Uploading abc123_test_file.wav to S3...
INFO - Upload successful
INFO - Job complete: abc123_test_file.wav (45.1s, $0.005)
```

### Final Summary
```
INFO - MUSICGEN WORKER COMPLETED
INFO - Successful jobs: 4/4
INFO - Total generation time: 180.5s (3.0m)
INFO - Estimated total cost: $0.020
INFO - Cost report uploaded: ✅
```

### Error Indicators
Look out for:
- `ERROR` level messages
- `Failed to` messages  
- `❌` emoji indicators
- CUDA/GPU errors
- S3 upload failures
- Model loading failures

## 🚨 Troubleshooting Common Issues

### Worker Not Starting
**Check:** `/var/log/cloud-init-output.log`
- Look for package installation failures
- Check git clone errors
- Verify dependency installation

### Model Loading Fails
**Check:** Worker logs for:
```
ERROR - Failed to initialize model: [error details]
CUDA not available, using CPU (will be very slow)
```
**Solutions:**
- Verify instance type has GPU (g4dn.* family)
- Check AMI includes NVIDIA drivers
- Ensure sufficient disk space (~10GB)

### S3 Upload Fails
**Check:** Worker logs for:
```
ERROR - Failed to upload [filename]: [error details]
```
**Solutions:**
- Verify IAM role attached to instance
- Check S3 bucket permissions
- Test S3 access manually: `aws s3 ls s3://your-bucket/`

### Generation Stalls
**Check:** GPU usage with `nvidia-smi`
- Should show GPU memory usage during generation
- If stuck at 0%, model may have crashed
- Check for out-of-memory errors

## ⏱️ Expected Timing

### First Run (includes model download)
- Bootstrap: 5-10 minutes
- Model download: 5-10 minutes  
- Generation: 2-5 minutes per prompt

### Subsequent Runs (model cached)
- Bootstrap: 3-5 minutes
- Model loading: 1-2 minutes
- Generation: 2-5 minutes per prompt

## 💡 Pro Tips

1. **Use `tail` command**: Most effective for monitoring active generation
2. **Check S3 frequently**: Files appear immediately after generation
3. **Monitor GPU usage**: Use `nvidia-smi` to verify GPU utilization
4. **Save important logs**: Download logs before terminating instance
5. **Multiple terminals**: Run `tail` in one, `s3` checks in another

## 📞 Getting Help

If worker fails:
1. Check both worker and bootstrap logs
2. Note exact error messages  
3. Check instance type, AMI, and permissions
4. Verify S3 bucket access
5. Test with minimal prompts first