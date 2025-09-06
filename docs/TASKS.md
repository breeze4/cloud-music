# MusicGen Batch System - Methodical Build & Test Tasks

## Phase 1: Foundation Verification

### Task 1.1: Verify Project Dependencies
- [ ] Check pyproject.toml contains all required dependencies (boto3, torch, transformers, etc.)
- [ ] Verify uv.lock is up-to-date with current dependencies
- [ ] Test `uv sync` works correctly
- [ ] Validate Python environment activation

### Task 1.2: Test Configuration Loading
- [ ] Verify config.py loads properly
- [ ] Check .env file contains all required AWS credentials
- [ ] Test configuration validation logic
- [ ] Ensure sensitive data is properly gitignored

## Phase 2: AWS Connectivity Testing

### Task 2.1: Test AWS Credentials and Permissions
- [ ] Run check_aws_readiness.py to verify AWS setup
- [ ] Test EC2 permissions (describe-instances, request-spot-instances)
- [ ] Test S3 permissions (list-buckets, put-object, head-object)
- [ ] Verify IAM role configuration

### Task 2.2: Test EC2 Spot Instance Queries
- [ ] Test spot price querying for g4dn.xlarge instances
- [ ] Verify instance tagging logic works
- [ ] Test existing instance detection by tag
- [ ] Check AMI availability in target region

## Phase 3: Launcher Component Testing

### Task 3.1: Test Launcher Logic (Dry Run)
- [ ] Run launcher.py in dry-run mode to check existing instances
- [ ] Verify spot pricing display works correctly
- [ ] Test user confirmation prompts
- [ ] Validate spot request configuration parameters

### Task 3.2: Test UserData Bootstrap Script
- [ ] Review UserData script for worker initialization
- [ ] Verify git clone and dependency installation commands
- [ ] Test worker.py execution trigger logic
- [ ] Check error handling in bootstrap process

## Phase 4: Worker Component Validation

### Task 4.1: Review MusicGen Implementation
- [ ] Analyze worker.py model loading logic
- [ ] Check GPU memory management
- [ ] Verify chunking/continuation for long audio generation
- [ ] Test model crash recovery (try-except blocks)

### Task 4.2: Test Job Processing Logic
- [ ] Validate prompts.txt parsing (semicolon-separated format)
- [ ] Test comment line filtering (# prefix)
- [ ] Verify deterministic filename generation
- [ ] Check idempotency logic (S3 file existence check)

### Task 4.3: Test Timing and Cost Calculation
- [ ] Verify HOURLY_COST_USD matches launcher max spot price
- [ ] Test generation timing accuracy
- [ ] Validate cost calculation formula
- [ ] Check cost report data structure

## Phase 5: Storage and Reporting

### Task 5.1: Test S3 Integration
- [ ] Verify S3 bucket accessibility
- [ ] Test .wav file upload functionality
- [ ] Check temporary file cleanup after upload
- [ ] Validate S3 object naming convention

### Task 5.2: Test Cost Report Generation
- [ ] Verify cost_report.csv format matches spec
- [ ] Test CSV column headers and data types
- [ ] Check report upload to S3
- [ ] Validate report data accuracy

## Phase 6: Error Handling and Recovery

### Task 6.1: Test Spot Instance Interruption Recovery
- [ ] Simulate interrupted generation process
- [ ] Verify idempotency prevents duplicate work
- [ ] Test partial completion scenarios
- [ ] Check cost report handling for interrupted runs

### Task 6.2: Test Model Error Handling
- [ ] Test worker.py with invalid prompts
- [ ] Verify generation continues after model crashes
- [ ] Check error logging and reporting
- [ ] Test memory cleanup after errors

## Phase 7: End-to-End Integration Testing

### Task 7.1: Full System Test
- [ ] Create test prompts.txt with 2-3 short samples
- [ ] Run complete launcher → worker → reporting cycle
- [ ] Verify all outputs appear in S3
- [ ] Check final cost report accuracy

### Task 7.2: Cost Control Validation
- [ ] Verify max spot price enforcement
- [ ] Test manual EC2 instance shutdown procedures
- [ ] Check cost estimate vs actual billing alignment
- [ ] Validate cost report serves as upper bound estimate

## Testing Instructions
Each phase should be completed and verified before proceeding to the next. After each task:
1. Mark the task as complete in this file
2. Note any issues or deviations from expected behavior
3. Test that the application remains fully functional

## Notes
- DO NOT run actual AWS resources during testing unless explicitly required
- Focus on dry-run modes and validation logic
- Manual testing preferred - no automated test execution needed
- User will handle EC2 instance shutdown and AWS resource management