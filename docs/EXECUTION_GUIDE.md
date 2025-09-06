# MusicGen Batch System - Step-by-Step Execution Guide

## ⚠️ IMPORTANT: Cost Control Notice

This guide involves launching real AWS EC2 instances that incur charges. Follow each step carefully and verify before proceeding. **You must manually terminate instances when complete** to avoid ongoing charges.

## 🎯 Quick Reference: Easy Monitoring Commands

Once your worker is running, use these simple commands from your local machine:

```bash
uv run python monitor_worker.py status    # Show instance status
uv run python monitor_worker.py logs      # Show recent worker logs  
uv run python monitor_worker.py tail      # Follow logs in real-time ⭐
uv run python monitor_worker.py ssh       # SSH to worker instance
uv run python monitor_worker.py s3        # Show current S3 outputs
```

**Most useful:** `uv run python monitor_worker.py tail` - shows live progress!

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] AWS credentials configured (run `aws sts get-caller-identity`)
- [ ] S3 bucket created and accessible
- [ ] EC2 key pair exists for SSH access
- [ ] IAM role created with S3 permissions
- [ ] AMI ID updated in `.env` file (Deep Learning AMI with GPU support)
- [ ] Git repository URL updated in `config.py` line 94
- [ ] Completed `uv run python check_aws_readiness.py` successfully

## Phase 1: Pre-Launch Verification (SAFE - No AWS Resources Created)

### Step 1.1: Test Configuration Loading

**Command:**
```bash
uv run python -c "from config import config; print(f'S3 Bucket: {config.aws.s3_bucket_name}'); print(f'Max Price: ${config.aws.max_spot_price}'); print(f'Region: {config.aws.region}'); print(f'AMI: {config.aws.ami_id}')"
```

**Expected Output:**
```
S3 Bucket: musicgen-batch-output-564186
Max Price: $0.4
Region: us-west-2
AMI: ami-xxxxxxxxx
```

**Verification:** All values should match your `.env` file. No errors should occur.

---

### Step 1.2: Test AWS Permissions

**Command:**
```bash
uv run python check_aws_readiness.py
```

**Expected Output:**
```
✅ AWS credentials are configured
✅ S3 bucket 'musicgen-batch-output-564186' is accessible
✅ EC2 permissions are sufficient
✅ IAM role 'arn:aws:iam::311141564186:role/musicgen-worker-role' exists
✅ All AWS resources are ready
```

**Verification:** All items should show green checkmarks. If any fail, fix before proceeding.

---

### Step 1.3: Dry-Run Launcher (SAFE - No Resources Created)

**Command:**
```bash
uv run python launcher.py
```

**What You'll See:**
1. Configuration loading messages
2. Check for existing instances (likely none found)
3. Current spot pricing display for your region
4. Cost warning and confirmation prompt

**At the prompt, type `no` to exit safely**

**Verification Steps:**
- [ ] No existing instances reported (or expected instances shown correctly)
- [ ] Spot prices displayed for multiple availability zones
- [ ] Some zones should show green ✅ (under your max price)
- [ ] Cost estimates shown (1hr, 4hr, 8hr scenarios)
- [ ] Typing 'no' exits without creating resources

---

## Phase 2: First Launch Attempt (CREATES AWS RESOURCES - $$ COST ALERT $$)

### Step 2.1: Launch with Minimal Test

**Before proceeding:**
- [ ] Backup your current `prompts.txt` 
- [ ] Create test version with only 1-2 short prompts (30-60 seconds max)

**Edit prompts.txt for testing:**
```bash
cp prompts.txt prompts.txt.backup
```

Create minimal test version:
```
# Test run - minimal prompts
upbeat electronic dance music with heavy bass ; 30 ; test_dance
relaxing acoustic guitar melody ; 45 ; test_acoustic
```

---

### Step 2.2: Launch Instance

**Command:**
```bash
uv run python launcher.py
```

**At the confirmation prompt, carefully review:**
- Max hourly cost matches your expectation
- You understand manual shutdown requirement
- **Type `yes` only if ready to incur charges**

**Expected Immediate Output:**
```
✅ Security group 'musicgen-worker-sg' ready
📤 Submitting spot request with max price: $0.400/hour
✅ Spot request submitted: sir-xxxxxxxxx
📋 Request Status: pending-evaluation
   Max Price: $0.400/hour
   Instance Type: g4dn.xlarge
```

**Immediate Verification (AWS Console):**
1. Go to EC2 Console → Spot Requests
2. Find your request ID (`sir-xxxxxxxxx`)  
3. Status should be `pending-evaluation` or `pending-fulfillment`
4. Should NOT be `failed` or `cancelled`

---

### Step 2.3: Monitor Spot Request Fulfillment

**Command to check status:**
```bash
aws ec2 describe-spot-instance-requests --region us-west-2 --spot-instance-request-ids sir-xxxxxxxxx
```

**Wait for status to change to `active` (usually 1-3 minutes)**

**Alternative: Watch in AWS Console:**
- EC2 → Spot Requests → Refresh until status = `active`
- Note the Instance ID when created (e.g., `i-abcdef123456`)

---

### Step 2.4: Verify Instance Launch

**Command to check instance:**
```bash
aws ec2 describe-instances --region us-west-2 --filters "Name=tag:Name,Values=musicgen-batch-worker" --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress,InstanceType]' --output table
```

**Expected Output:**
```
-------------------------------------------------------------
|                    DescribeInstances                      |
+---------------+----------+------------------+--------------+
|  i-abcdef123  | running  |   44.123.45.67   | g4dn.xlarge |
+---------------+----------+------------------+--------------+
```

**Verification Checkpoints:**
- [ ] Instance state is `running` (may take 2-3 minutes)
- [ ] Public IP address assigned
- [ ] Instance type matches configuration
- [ ] Name tag shows `musicgen-batch-worker`

---

## Phase 3: Monitor Bootstrap Process

### Step 3.1: Easy Log Monitoring (RECOMMENDED)

**🎯 Use the monitoring script for easy access:**
```bash
# Check instance status and get monitoring commands
uv run python monitor_worker.py status

# View recent worker logs
uv run python monitor_worker.py logs

# Follow logs in real-time (most useful!)
uv run python monitor_worker.py tail
```

**Alternative - Manual SSH:**
```bash
# SSH to instance manually
ssh -i /path/to/your-key.pem ubuntu@[PUBLIC_IP_ADDRESS]

# Check bootstrap logs once connected
sudo tail -f /var/log/cloud-init-output.log
```

**Expected Log Progression:**
1. System package updates
2. Git and Python installation  
3. UV package manager installation
4. Repository cloning
5. Python dependency installation
6. Environment variable setup
7. Worker script execution start

---

### Step 3.2: Monitor Worker Startup

**🎯 Easy way (from your local machine):**
```bash
# Follow worker logs in real-time
uv run python monitor_worker.py tail
```

**Alternative - Manual SSH:**
```bash
# SSH first, then check logs
uv run python monitor_worker.py ssh
# Once connected: tail -f /var/log/musicgen-worker.log
```

**Expected Log Progression:**
```
2025-01-XX XX:XX:XX - INFO - Worker initialized - S3 bucket: musicgen-batch-output-564186, Hourly cost: $0.40
2025-01-XX XX:XX:XX - INFO - Initializing MusicGen model...
2025-01-XX XX:XX:XX - INFO - Using GPU: Tesla T4
2025-01-XX XX:XX:XX - INFO - Loading facebook/musicgen-medium...
[Model download progress - may take 5-10 minutes first time]
2025-01-XX XX:XX:XX - INFO - Model initialized successfully
2025-01-XX XX:XX:XX - INFO - Found 2 valid prompts to process
```

**⏱️ Model Download Time:** First run downloads ~6GB model. This takes 5-10 minutes.

**Monitor GPU usage:**
```bash
nvidia-smi
```

**During model download, you should see GPU memory usage increase.**

---

## Phase 4: Monitor Generation Process

### Step 4.1: Watch Job Processing

**Worker log should show progression through each prompt:**
```
2025-01-XX XX:XX:XX - INFO - Processing prompt 1/2: upbeat electronic dance music with heavy bass
2025-01-XX XX:XX:XX - INFO - Checking if [hash]_test_dance.wav exists in S3...
2025-01-XX XX:XX:XX - INFO - File not found, proceeding with generation...
2025-01-XX XX:XX:XX - INFO - Generating audio for: upbeat electronic dance music with heavy bass
2025-01-XX XX:XX:XX - INFO - Audio generated successfully, duration: 30 seconds
2025-01-XX XX:XX:XX - INFO - Generation time: 45.2 seconds, Cost: $0.005
2025-01-XX XX:XX:XX - INFO - Uploading [hash]_test_dance.wav to S3...
2025-01-XX XX:XX:XX - INFO - Upload successful
```

**Monitor S3 bucket for files appearing:**
```bash
# Easy way
uv run python monitor_worker.py s3

# Manual way  
aws s3 ls s3://your-bucket-name/ --region us-west-2
```

**Each successful generation should create a .wav file in S3**

---

### Step 4.2: Verify Generation Quality

**Download a test file to verify:**
```bash
aws s3 cp s3://your-bucket-name/[filename].wav ./test_output.wav
```

**Check file:**
- File size should be reasonable (30 seconds ≈ 1-2MB)
- Should be playable audio file
- Duration should match requested length

---

## Phase 5: Completion and Cleanup

### Step 5.1: Wait for All Prompts to Complete

**Worker should process all prompts and then show:**
```
2025-01-XX XX:XX:XX - INFO - All prompts processed successfully
2025-01-XX XX:XX:XX - INFO - Generating cost report...
2025-01-XX XX:XX:XX - INFO - Cost report uploaded to S3
2025-01-XX XX:XX:XX - INFO - Worker script completed
```

**Verify final outputs in S3:**
```bash
aws s3 ls s3://your-bucket-name/ --region us-west-2
```

**Should see:**
- One .wav file per successful prompt
- One `cost_report.csv` file

---

### Step 5.2: Download and Review Cost Report

```bash
aws s3 cp s3://your-bucket-name/cost_report.csv ./cost_report.csv
cat cost_report.csv
```

**Expected CSV format:**
```
s3_filename,prompt,requested_duration_s,generation_time_s,estimated_cost_usd
abc123_test_dance.wav,upbeat electronic dance music with heavy bass,30,45.2,0.005
def456_test_acoustic.wav,relaxing acoustic guitar melody,45,62.8,0.007
```

**Verify:**
- [ ] All successful prompts included
- [ ] Generation times seem reasonable
- [ ] Cost calculations correct: `(generation_time / 3600) * 0.40`

---

### Step 5.3: ⚠️ CRITICAL: Terminate Instance

**This step prevents ongoing charges!**

**Method 1: AWS CLI**
```bash
aws ec2 terminate-instances --region us-west-2 --instance-ids i-your-instance-id
```

**Method 2: AWS Console**
1. Go to EC2 Console → Instances
2. Select your `musicgen-batch-worker` instance
3. Instance State → Terminate Instance
4. Confirm termination

**Verification:**
```bash
aws ec2 describe-instances --region us-west-2 --instance-ids i-your-instance-id --query 'Reservations[*].Instances[*].State.Name'
```

**Should show: `shutting-down` then `terminated`**

---

### Step 5.4: Final Cost Review

**Check actual AWS billing:**
1. Go to AWS Console → Billing
2. Look for EC2 charges
3. Compare with cost report estimates

**Expected charges:**
- EC2 spot instance: ~$0.10-$0.30 for 15-45 minute test run
- S3 storage: <$0.01 for a few small files
- Data transfer: <$0.01

---

## Troubleshooting Guide

### Instance Launch Issues

**Spot request failed:**
- Check availability in other zones
- Increase max spot price slightly
- Try different instance type (g4dn.2xlarge, p3.2xlarge)

**Bootstrap fails:**
- SSH to instance and check `/var/log/cloud-init-output.log`
- Verify git repository URL in `config.py`
- Check internet connectivity from instance

**Worker crashes:**
- Check `/var/log/musicgen-worker.log`
- Verify S3 permissions
- Check for insufficient disk space (need ~10GB free)

### Model Loading Issues

**CUDA not available:**
- Verify instance type has GPU (g4dn.* or p3.* family)
- Check AMI includes NVIDIA drivers

**Model download fails:**
- Check internet connectivity
- Verify Hugging Face Hub access
- Check disk space (need ~10GB)

### S3 Upload Issues

**Permission denied:**
- Verify IAM role attached to instance
- Check S3 bucket policy
- Test S3 access: `aws s3 ls s3://your-bucket-name/`

---

## Success Criteria Checklist

Before considering the test successful:

- [ ] Launcher showed accurate spot pricing
- [ ] Spot instance request fulfilled successfully  
- [ ] Instance launched with correct configuration
- [ ] SSH access worked
- [ ] UserData script completed bootstrap
- [ ] Worker detected GPU and loaded model
- [ ] All test prompts generated audio files
- [ ] Files uploaded to S3 successfully
- [ ] Cost report generated and uploaded
- [ ] Instance terminated to stop charges
- [ ] Total cost under $0.50 for test run

**If all items checked: System is ready for production use with your full prompts.txt!**