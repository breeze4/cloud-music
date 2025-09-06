# MusicGen Batch System Setup Tasks

This document outlines the tasks needed to set up the AWS infrastructure and launcher script for the batch MusicGen generation system.

## Phase 1: AWS Account Prerequisites (Manual - Account Owner Tasks)

### 1.1. AWS Account Setup and Permissions
1. Ensure AWS CLI is installed and configured with appropriate credentials
2. Verify account has permissions for EC2, S3, and IAM operations
3. Check account limits for g4dn.xlarge spot instances in desired regions
4. Set up billing alerts to monitor unexpected costs

### 1.2. Create IAM Role for EC2 Instances
1. Create IAM role named `musicgen-worker-role` 
2. Attach policy allowing s3:PutObject and s3:HeadObject permissions on target bucket
3. Add EC2 assume role trust relationship
4. Note the role ARN for launcher configuration

### 1.3. Create S3 Bucket for Storage
1. Create S3 bucket with unique name (e.g., `musicgen-batch-output-{random}`)
2. Disable public access completely
3. Configure appropriate lifecycle policies if desired
4. Note bucket name for launcher configuration

### 1.4. Key Pair Management
1. Create or identify existing EC2 Key Pair for instance access
2. Ensure private key is accessible locally for debugging
3. Note key pair name for launcher configuration

## Phase 2: AMI Preparation (Manual - One-time Setup)

### 2.1. Launch Base Instance for AMI Creation
1. Launch AWS Deep Learning AMI (Ubuntu) on g4dn.xlarge instance
2. Connect via SSH and update system packages
3. Install git and configure for repository access
4. Install additional Python dependencies: transformers, torch, boto3
5. Test MusicGen model loading to verify GPU functionality
6. Create startup script template for worker bootstrap

### 2.2. Create Custom AMI
1. Stop the prepared instance
2. Create AMI with descriptive name (e.g., `musicgen-worker-v1`)
3. Note AMI ID for launcher configuration
4. Terminate the preparation instance to avoid costs

## Phase 3: Configuration Management

### 3.1. Create Configuration File
1. Create `config.py` or `config.json` with:
   - AWS region
   - AMI ID from Phase 2
   - IAM role ARN from Phase 1
   - S3 bucket name from Phase 1
   - Key pair name from Phase 1
   - Default max spot price (e.g., 0.40)
   - Instance type (g4dn.xlarge)

### 3.2. Create Bootstrap Script
1. Create `bootstrap.sh` UserData script that:
   - Updates system packages
   - Clones the git repository
   - Installs any missing dependencies
   - Starts the worker script automatically

## Phase 4: Launcher Implementation

### 4.1. Basic Launcher Structure
1. Create `launcher.py` with configuration loading
2. Add boto3 EC2 client initialization
3. Implement function to check for existing instances with tag `musicgen-batch-worker`
4. Add error handling for AWS API calls

### 4.2. Spot Price Checking
1. Implement function to get current spot pricing for g4dn.xlarge
2. Display pricing information across available zones
3. Add user confirmation prompt before proceeding
4. Handle pricing API errors gracefully

### 4.3. Spot Instance Request
1. Implement spot instance request with proper configuration:
   - AMI ID, instance type, key pair
   - IAM role attachment
   - Security group (create default if needed)
   - UserData script for bootstrap
   - Proper tags for identification
2. Add request status monitoring
3. Implement proper error handling for spot request failures

### 4.4. Security Group Management
1. Create function to find or create security group
2. Configure inbound SSH access (port 22) for debugging
3. Set appropriate outbound rules for S3/internet access
4. Use security group in spot instance requests

## Phase 5: Testing and Validation

### 5.1. Dry Run Testing
1. Implement dry-run mode in launcher to validate configurations
2. Test all AWS API calls without creating resources
3. Verify IAM permissions work correctly
4. Test configuration file loading and validation

### 5.2. Integration Testing
1. Test complete launcher workflow with minimal setup
2. Verify instance launches successfully with proper tags
3. Confirm bootstrap script executes correctly
4. Test instance can access S3 bucket and repository
5. Verify worker script can be executed manually on instance

### 5.3. Cost Control Validation
1. Test spot instance termination procedures
2. Verify billing tags are applied correctly
3. Confirm max spot price limits are enforced
4. Test launcher behavior when spot capacity unavailable

## Phase 6: Operational Procedures

### 6.1. Create Operation Scripts
1. Create script to list all running musicgen instances
2. Create script to terminate all musicgen instances (emergency stop)
3. Add logging to launcher for audit trail
4. Create simple status checking utilities

### 6.2. Documentation and Safety
1. Document manual shutdown procedures
2. Create troubleshooting guide for common issues
3. Add safety checks to prevent accidental multiple launches
4. Document cost monitoring and alerting setup

## Implementation Notes

- Each task should result in a fully functional system after completion
- Test each phase thoroughly before proceeding to the next
- Keep costs minimal during development by terminating instances promptly
- Use git to track configuration changes and AMI versions
- Implement proper error handling and logging throughout