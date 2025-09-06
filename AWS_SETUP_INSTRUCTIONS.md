CUrrent status:

[Step 1] Checking AWS Credentials                                                    
----------------------------------------                                             
✅ Authenticated as: arn:aws:iam::311141564186:user/basic                             
✅ Account ID: 311141564186                                                           
                                                                                     
[Step 2] Checking AWS Permissions                                                    
----------------------------------------                                             
✅ EC2 Describe permission                                                            
✅ EC2 Spot Pricing permission                                                        
✅ S3 List Buckets permission                                                         
❌ IAM List Roles permission: AccessDenied                                            
                                                                                     
[Step 3] Checking EC2 Service Limits                                                 
----------------------------------------                                             
❌ Service Limits check failed with error: 'SpotPrices'                               
                                                                                     
[Step 4] Setting up S3 Bucket                                                        
----------------------------------------                                             
✅ S3 bucket 'musicgen-batch-output-564186' already exists                            
                                                                                     
[Step 5] Setting up IAM Role                                                         
----------------------------------------                                             
✅ IAM role 'musicgen-worker-role' already exists                                     
✅ IAM policy 'musicgen-worker-role-s3-policy' already exists                         
✅ Policy attached to role                                                            
✅ Instance profile 'musicgen-worker-role' already exists                             
                                                                                     
[Step 6] Checking EC2 Key Pair and Private Key                                       
----------------------------------------                                             
✅ AWS key pair 'musicgen-batch-keypair' exists                                       
✅ Private key file exists: ./keys/musicgen-batch-keypair.pem                         
                                                                                     
[Step 7] Billing Alert Setup                                                         
----------------------------------------                                             
Setting up billing alerts is highly recommended to monitor costs.                    
To set up billing alerts:                                                            
1. Go to AWS Console -> Billing Dashboard                                            
2. Click 'Budgets' in left sidebar                                                   
3. Click 'Create budget'                                                             
4. Choose 'Cost budget'                                                              
5. Set a reasonable monthly limit (e.g., $50)                                        
6. Configure email notifications                                                     
                                                                                     
Have you set up billing alerts? (y/N): y                                             
                                                                                     
============================================================                         
 Readiness Summary                                                                   
============================================================                         
                                                                                     
✅ Credentials                                                                        
❌ Permissions                                                                        
❌ Service Limits                                                                     
✅ S3 Bucket                                                                          
✅ IAM Role                                                                           
✅ Key Pair                                                                           
✅ Billing Alerts                                                                     
                                                                                     
Overall: 5/7 checks passed                                                           
                                                                                     
⚠️  Some checks failed. Please address the issues above before proceeding.           

### PUT INSTRUCTIONS TO FIX BELOW:

## Fix Step 2: IAM List Roles Permission Error

Your IAM policy is missing the `iam:ListRoles` permission. Here's how to fix it:

### Option 1: Add Missing Permission (Recommended)
1. **Go to AWS Console** → **IAM** → **Policies**
2. **Find your policy**: Search for `MusicGenBatchPolicy`
3. **Edit the policy**: Click on the policy → **Edit**
4. **Go to JSON tab** and find the IAM section
5. **Add the missing permission**: Ensure `iam:ListRoles` is in the action list:
   ```json
   {
       "Effect": "Allow", 
       "Action": [
           "iam:CreateRole",
           "iam:GetRole", 
           "iam:CreatePolicy",
           "iam:GetPolicy",
           "iam:AttachRolePolicy",
           "iam:CreateInstanceProfile", 
           "iam:GetInstanceProfile",
           "iam:AddRoleToInstanceProfile",
           "iam:ListRoles",
           "iam:PassRole"
       ],
       "Resource": [...]
   }
   ```
6. **Save changes**

### Option 2: Switch to Administrator Access (Easier)
1. **Go to AWS Console** → **IAM** → **Users** → **basic**
2. **Remove current policy**: Detach `MusicGenBatchPolicy` 
3. **Add Administrator Access**: Attach `AdministratorAccess` policy
4. **Wait 5 minutes** for changes to propagate

## Fix Step 3: EC2 Service Limits SpotPrices Error

This error means the spot pricing API call failed. Here's how to fix it:

### Fix 1: Add Missing EC2 Permission
Your policy needs the `ec2:DescribeInstanceTypeOfferings` permission:

1. **Edit your IAM policy** (same steps as above)
2. **Find the EC2 section** and add this permission to the action list:
   ```json
   {
       "Effect": "Allow",
       "Action": [
           "ec2:DescribeInstances",
           "ec2:DescribeSpotPriceHistory", 
           "ec2:DescribeKeyPairs",
           "ec2:CreateKeyPair",
           "ec2:RunInstances",
           "ec2:TerminateInstances", 
           "ec2:CreateTags",
           "ec2:DescribeInstanceTypes",
           "ec2:DescribeAvailabilityZones",
           "ec2:DescribeSecurityGroups",
           "ec2:CreateSecurityGroup",
           "ec2:AuthorizeSecurityGroupIngress",
           "ec2:RequestSpotInstances",
           "ec2:DescribeSpotInstanceRequests", 
           "ec2:CancelSpotInstanceRequests",
           "ec2:DescribeInstanceTypeOfferings"
       ],
       "Resource": "*"
   }
   ```

### Fix 2: Check Your AWS Region
1. **Check your .env file** - make sure `AWS_REGION` is set to a valid region like `us-west-2`
2. **Verify the region** supports g4dn.xlarge instances

### Fix 3: Try Again After Permissions Update
Sometimes AWS APIs have temporary issues. After updating permissions:
1. **Wait 5-10 minutes** for changes to propagate
2. **Re-run the check**: `uv run python check_aws_readiness.py`

## Complete Updated Policy (Copy-Paste Ready)

If you want to replace your entire policy, here's the complete version with all required permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeSpotPriceHistory",
                "ec2:DescribeKeyPairs",
                "ec2:CreateKeyPair",
                "ec2:RunInstances",
                "ec2:TerminateInstances",
                "ec2:CreateTags",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeAvailabilityZones",
                "ec2:DescribeSecurityGroups",
                "ec2:CreateSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:RequestSpotInstances",
                "ec2:DescribeSpotInstanceRequests",
                "ec2:CancelSpotInstanceRequests",
                "ec2:DescribeInstanceTypeOfferings"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:ListAllMyBuckets",
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:PutBucketPublicAccessBlock"
            ],
            "Resource": [
                "*",
                "arn:aws:s3:::musicgen-batch-output-*",
                "arn:aws:s3:::musicgen-batch-output-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:GetRole",
                "iam:CreatePolicy",
                "iam:GetPolicy",
                "iam:AttachRolePolicy",
                "iam:CreateInstanceProfile",
                "iam:GetInstanceProfile",
                "iam:AddRoleToInstanceProfile",
                "iam:ListRoles",
                "iam:PassRole"
            ],
            "Resource": [
                "arn:aws:iam::311141564186:role/musicgen-*",
                "arn:aws:iam::311141564186:policy/musicgen-*",
                "arn:aws:iam::311141564186:instance-profile/musicgen-*"
            ]
        }
    ]
}
```

## Next Steps

1. **Fix the permissions** using one of the options above
2. **Wait 5-10 minutes** for AWS IAM changes to propagate
3. **Re-run the readiness check**: `uv run python check_aws_readiness.py`
4. **Expect all checks to pass** (7/7)

If you still have issues after trying these fixes, the problem might be region-specific or a temporary AWS service issue.
