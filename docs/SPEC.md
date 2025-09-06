# **Batch MusicGen Generation System Specification v1.1**

## **1\. Objective**

To define a simple, cost-effective system for generating multiple, long-form (3-5+ minute) audio files from a static list of text prompts. The system will use cloud GPU spot instances to minimize cost and will be designed for batch processing, not real-time interaction. A key output will be a cost report estimating the compute expense for each generated file.

## **2\. System Overview**

The system consists of two primary components: a **Local Control Script** and a **Cloud Worker Instance**. The workflow is initiated locally. The control script ensures a cloud worker is active, which then pulls a job list from a version-controlled text file, generates the audio, calculates the cost, and pushes the outputs to cloud storage.

**Workflow:**

1. **Local:** A user runs launcher.py.  
2. **Cloud API:** The script requests an EC2 Spot Instance if one isn't already running.  
3. **EC2 Worker:** The instance boots, pulls the latest code and prompts.txt from a git repository.  
4. **Generation:** The worker.py script executes, processing each prompt from the file. It times each generation.  
5. **Storage:** The script uploads each completed audio file to an S3 bucket.  
6. **Reporting:** After all prompts are processed, the script uploads a final cost\_report.csv to S3.  
7. **Completion:** The worker script exits, but the EC2 instance remains active.

## **3\. Component Specifications**

### **3.1. Local Control Script (launcher.py)**

* **Language:** Python 3  
* **Libraries:** boto3  
* **Responsibilities:**  
  * Check AWS for any running or pending EC2 instances with a specific tag (e.g., musicgen-batch-worker).
  * If no instance is found, the launcher should check the current costs of spot instances and print that out. Once the user says yes, submit a request for a new EC2 Spot Instance using a pre-defined configuration. This configuration **must include the max spot price** the user is willing to pay.  
  * The spot request must include a UserData script to bootstrap the worker instance on its first boot.  
  * The script's role is complete once the spot request is successfully submitted.

### **3.2. Cloud Worker Instance (AWS EC2)**

* **Instance Type:** g4dn.xlarge (NVIDIA T4 GPU) or equivalent.  
* **Pricing Model:** On-demand Instance for predictable availability and pricing.  
* **AMI (Amazon Machine Image):** A custom, pre-built AMI must be used.  
  * **Base:** AWS Deep Learning AMI (Ubuntu).  
  * **Pre-installed Dependencies:** NVIDIA drivers, CUDA, Python 3, Git, uv package manager, and all required Python libraries (torch, transformers, boto3, etc.).  
  * **Storage Requirements:** 80GB EBS volume to accommodate AMI requirements (~22GB), CUDA/PyTorch libraries (~13GB), MusicGen model (~8GB), and temporary audio files with comfortable headroom
* **IAM Role:** The instance must be launched with an IAM role granting it, at minimum, s3:PutObject and s3:HeadObject permissions on the target S3 bucket.

### **3.3. Job Definition File (prompts.txt)**

* **Format:** Plain text (.txt).  
* **Location:** Stored in the root of the project's git repository.  
* **Syntax:** Each line represents one song to be generated.  
  * Format: PROMPT\_TEXT ; DURATION\_IN\_SECONDS ; FILE\_NAME 
  * Example: cinematic trailer music with epic drums;180;cinema.wav  
  * Lines beginning with \# will be ignored as comments.

### **3.4. Worker Script (worker.py)**

* **Language:** Python 3  
* **Configuration:** The script must contain a configurable variable for the instance's hourly cost (e.g., HOURLY\_COST\_USD), which should match the max spot price set in launcher.py.  
* **Responsibilities:**  
  1. **Initialization:** Load the MusicGen model into GPU memory. Initialize an empty list to store reporting data.  
  2. **Job Parsing:** Read and parse prompts.txt.  
  3. **Loop:** Iterate through each valid line in the prompt file.  
  4. **Idempotency Check:** For each prompt, generate a deterministic output filename. Before generation, check if this filename already exists in the S3 bucket. If it exists, skip to the next prompt.  
  5. **Timing:** Record the system time before starting generation.  
  6. **Generation:** Generate the full audio using a chunking/continuation loop.  
  7. **Timing & Cost Calculation:** Record the system time after generation. Calculate the elapsed time in seconds. Estimate the cost: cost \= (elapsed\_seconds / 3600\) \* HOURLY\_COST\_USD.  
  8. **Output:** Save the final audio locally as a temporary .wav file.  
  9. **Upload:** Upload the temporary file to the S3 bucket.  
  10. **Data Logging:** Append a record to the reporting data list containing: s3\_filename, prompt, requested\_duration\_s, generation\_time\_s, estimated\_cost\_usd.  
  11. **Cleanup:** Delete the local temporary file.  
  12. **Final Report:** After the loop, generate a cost\_report.csv from the reporting data and upload it to the S3 bucket.  
  13. **Termination:** The script will exit gracefully after the last prompt has been processed.

### **3.5. Output Storage (AWS S3)**

* A standard S3 bucket to store the final .wav audio files and the cost\_report.csv.  
* Public access must be disabled. Access is granted via the EC2 instance's IAM Role.

### **3.6. Cost Report (cost\_report.csv)**

* **Format:** Comma-Separated Values (.csv).  
* **Columns:**  
  * s3\_filename: The name of the generated audio file in S3.  
  * prompt: The full text prompt used for generation.  
  * requested\_duration\_s: The target song duration in seconds.  
  * generation\_time\_s: The actual wall-clock time in seconds the script took to generate the song.  
  * estimated\_cost\_usd: The calculated cost for the generation, based on the time taken and the configured hourly rate.

## **4\. Red Teaming & Risk Analysis**

* **Risk: Cost Calculation is an Estimate.**  
  * **Impact:** The reported cost may not match the final AWS bill exactly.  
  * **Mitigation (v1.1):** The cost is based on the *on-demand hourly rate* for the instance type. This should be clearly documented. The estimate serves as an upper bound for the cost of each job.  
* **Risk: Manual Instance Termination Required.**  
  * **Impact:** If the user forgets to terminate the instance, costs will continue to accrue.  
  * **Mitigation (v1.1):** Clear warnings are displayed during launch. The idempotency check ensures that restarts only process remaining work.  
* **Risk: Instance Is Not Shut Down.**  
  * **Impact:** Significant cost overrun.  
  * **Mitigation (v1.1):** This remains a manual process. The user is responsible for stopping the EC2 instance. This is the biggest operational risk.  
* **Risk: A Prompt Causes a Model Crash.**  
  * **Impact:** The entire generation process could halt.  
  * **Mitigation (v1.1):** The worker.py script must wrap the generation logic for each song in a try...except block to ensure it continues to the next prompt. Failed songs will not be included in the final cost report.  
* **Risk: Race Conditions.**  
  * **Impact:** If two launcher.py scripts are run simultaneously, two instances could be launched.  
  * **Mitigation (v1.1):** The S3 check provides a basic locking mechanism. The second instance will skip already-completed songs. However, two separate and incomplete cost\_report.csv files might be generated. This is a low-risk for a single-user system.

## **5\. Detailed Execution Flow & Verification**

### **5.1 Launcher Script Execution Flow**

**Step 1: Pre-flight Checks**
- Load configuration from `.env` file and validate all required settings
- Initialize AWS clients and test permissions (EC2 describe-instances, spot-price-history, S3 list-buckets)
- **Verification**: Configuration validation passes without errors

**Step 2: Instance Discovery**
- Search for existing EC2 instances tagged with `Name=musicgen-batch-worker`
- Display any found instances with state, type, launch time, and IP addresses
- **Verification**: Check AWS Console → EC2 → Instances for matching instances

**Step 3: Spot Pricing Analysis**
- Query current spot prices for configured instance type across all availability zones
- Compare prices against configured max spot price ($0.40/hour default)
- Display cost estimates for 1, 4, and 8-hour scenarios
- **Verification**: Compare displayed prices with EC2 Console → Spot Requests → Pricing History

**Step 4: User Confirmation**
- Display cost warning showing max hourly rate
- Warn about manual shutdown requirement
- Prompt for user confirmation to proceed
- **Verification**: Review warning message accuracy before confirming

**Step 5: Spot Instance Launch (if confirmed)**
- Create/verify security group `musicgen-worker-sg` with SSH access from current IP
- Submit spot instance request with full configuration (AMI, IAM role, key pair, UserData script)
- Report spot request ID and initial status
- **Verification**: Check AWS Console → EC2 → Spot Requests for new request

### **5.2 Worker Script Execution Flow (Automated on EC2)**

**Phase 1: Environment Bootstrap**
- UserData script installs system packages (git, curl, python3-pip)
- Install uv package manager from astral.sh
- Clone project repository to `/home/ubuntu/musicgen-batch`
- Install Python dependencies via `uv sync`
- **Verification**: SSH to instance and check `/var/log/cloud-init-output.log`

**Phase 2: Model Initialization**
- Check for CUDA/GPU availability (expect Tesla T4 on g4dn.xlarge)
- Download MusicGen model from Hugging Face (`facebook/musicgen-medium`, ~6GB)
- Load model into GPU memory for inference
- **Verification**: Check worker logs for GPU detection and model loading success

**Phase 3: Job Processing**
- Parse `prompts.txt` from repository root (format: `PROMPT ; DURATION ; FILENAME`)
- Skip comment lines (starting with #) and validate duration values
- **Verification**: Worker logs should show "Found X valid prompts to process"

**Phase 4: Generation Loop**
For each prompt:
- Generate deterministic filename using hash for idempotency
- Check S3 bucket for existing file (skip if already exists)
- Generate audio using MusicGen with chunking for long durations (>30s)
- Time the generation process for cost calculation
- Save as temporary .wav file locally
- **Verification**: Monitor GPU utilization with `nvidia-smi` during generation

**Phase 5: S3 Upload & Cleanup**
- Upload .wav file to S3 bucket using deterministic naming
- Calculate generation cost: `(time_seconds / 3600) * hourly_rate`
- Delete local temporary file after successful upload
- **Verification**: Check S3 bucket for appearance of new .wav files

**Phase 6: Cost Reporting**
- Generate `cost_report.csv` with columns: s3_filename, prompt, requested_duration_s, generation_time_s, estimated_cost_usd
- Include only successful generations in final report
- Upload CSV to S3 bucket
- **Verification**: Download and review cost_report.csv content

**Phase 7: Completion**
- Worker script exits (EC2 instance remains running)
- **Manual Action Required**: User must terminate instance via AWS Console

### **5.3 Verification Commands & Checkpoints**

**Pre-Launch Verification:**
```bash
# Test configuration and AWS connectivity
uv run python -c "from config import config; print(f'Bucket: {config.aws.s3_bucket_name}')"
uv run python check_aws_readiness.py

# Dry-run launcher (will show pricing but not launch if you say 'no')
uv run python launcher.py
```

**During Execution Monitoring:**
```bash
# Check spot request status
aws ec2 describe-spot-instance-requests --region us-west-2

# Monitor instance state
aws ec2 describe-instances --filters "Name=tag:Name,Values=musicgen-batch-worker" --region us-west-2

# SSH to instance for debugging
ssh -i your-key.pem ubuntu@[INSTANCE_IP]

# Check bootstrap logs on instance
sudo cat /var/log/cloud-init-output.log

# Monitor worker progress
tail -f /var/log/musicgen-worker.log

# Check GPU utilization during generation
nvidia-smi
```

**Post-Execution Verification:**
```bash
# List generated files in S3
aws s3 ls s3://your-bucket-name/

# Download cost report
aws s3 cp s3://your-bucket-name/cost_report.csv ./cost_report.csv

# Verify instance termination
aws ec2 describe-instances --instance-ids i-xxxxxxxxx --region us-west-2
```

### **5.4 Expected Timeline & Costs**

**Typical execution for 4 prompts (30-90 seconds each):**
- Bootstrap phase: 5-10 minutes (includes 6GB model download on first run)
- Generation phase: 2-5 minutes per prompt depending on duration and complexity
- Total runtime: 15-30 minutes
- Estimated cost: $0.10-$0.20 (at $0.40/hour max spot price)

**Success criteria:**
- All AWS permission checks pass
- Spot instance launches successfully
- Worker detects GPU and loads model
- Each prompt generates audio file in S3
- Cost report uploaded with accurate calculations
- Manual instance termination completes cleanup

## **6\. Out of Scope for v1.1**

* Automated shutdown of the EC2 instance upon script completion.  
* A web UI or API for submitting jobs.  
* Querying the actual, real-time spot price via AWS APIs for cost calculation.