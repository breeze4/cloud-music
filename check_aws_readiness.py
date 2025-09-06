#!/usr/bin/env python3
"""
AWS Account Readiness Checker for MusicGen Batch System
Validates Phase 1 requirements and creates necessary AWS resources
"""

import os
import sys
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pathlib import Path
import time


class AWSReadinessChecker:
    def __init__(self):
        self.load_env_config()
        self.session = None
        self.ec2 = None
        self.s3 = None
        self.iam = None
        self.sts = None
        
    def load_env_config(self):
        """Load configuration from .env file"""
        env_path = Path(".env")
        if not env_path.exists():
            print("❌ .env file not found. Please run setup_aws.py first.")
            sys.exit(1)
        
        self.config = {}
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    self.config[key] = value
        
        # Validate required config
        required = ['AWS_ACCOUNT_ID', 'AWS_REGION', 'S3_BUCKET_NAME', 'IAM_ROLE_NAME']
        missing = [key for key in required if key not in self.config]
        if missing:
            print(f"❌ Missing required configuration: {', '.join(missing)}")
            print("Please update your .env file.")
            sys.exit(1)

    def print_header(self, text):
        """Print formatted header"""
        print(f"\n{'='*60}")
        print(f" {text}")
        print(f"{'='*60}\n")

    def print_step(self, step_num, text):
        """Print formatted step"""
        print(f"\n[Step {step_num}] {text}")
        print("-" * 40)

    def print_status(self, status, message):
        """Print status with emoji"""
        emoji = "✅" if status else "❌"
        print(f"{emoji} {message}")

    def initialize_aws_clients(self):
        """Initialize AWS service clients"""
        try:
            self.session = boto3.Session(region_name=self.config['AWS_REGION'])
            self.ec2 = self.session.client('ec2')
            self.s3 = self.session.client('s3')
            self.iam = self.session.client('iam')
            self.sts = self.session.client('sts')
            return True
        except NoCredentialsError:
            print("❌ AWS credentials not found. Please run setup_aws.py first.")
            return False
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            return False

    def check_credentials(self):
        """Verify AWS credentials and account"""
        self.print_step(1, "Checking AWS Credentials")
        
        try:
            identity = self.sts.get_caller_identity()
            account_id = identity['Account']
            user_arn = identity['Arn']
            
            self.print_status(True, f"Authenticated as: {user_arn}")
            self.print_status(True, f"Account ID: {account_id}")
            
            # Verify account ID matches config
            if account_id != self.config['AWS_ACCOUNT_ID']:
                print(f"⚠️  Warning: Account ID in .env ({self.config['AWS_ACCOUNT_ID']}) doesn't match actual account ({account_id})")
                response = input("Update .env file with correct account ID? (Y/n): ").strip().lower()
                if response in ['', 'y', 'yes']:
                    self.update_env_value('AWS_ACCOUNT_ID', account_id)
            
            return True
            
        except ClientError as e:
            self.print_status(False, f"Authentication failed: {e}")
            return False

    def check_permissions(self):
        """Check required AWS permissions"""
        self.print_step(2, "Checking AWS Permissions")
        
        permissions_tests = [
            ('EC2 Describe', lambda: self.ec2.describe_instances(MaxResults=5)),
            ('EC2 Spot Pricing', lambda: self.ec2.describe_spot_price_history(MaxResults=1)),
            ('S3 List Buckets', lambda: self.s3.list_buckets()),
            ('IAM List Roles', lambda: self.iam.list_roles(MaxItems=1)),
        ]
        
        all_passed = True
        for name, test_func in permissions_tests:
            try:
                test_func()
                self.print_status(True, f"{name} permission")
            except ClientError as e:
                self.print_status(False, f"{name} permission: {e.response['Error']['Code']}")
                all_passed = False
        
        return all_passed

    def check_service_limits(self):
        """Check EC2 service limits for required instance types"""
        self.print_step(3, "Checking EC2 Service Limits")
        
        instance_type = self.config.get('INSTANCE_TYPE', 'g4dn.xlarge')
        
        try:
            # Check spot price history to verify instance type availability
            response = self.ec2.describe_spot_price_history(
                InstanceTypes=[instance_type],
                ProductDescriptions=['Linux/UNIX'],
                MaxResults=5
            )
            
            if response['SpotPrices']:
                latest_price = response['SpotPrices'][0]['SpotPrice']
                az = response['SpotPrices'][0]['AvailabilityZone']
                self.print_status(True, f"{instance_type} available in {az} at ${latest_price}/hour")
                
                # Check if our max price is reasonable
                max_price = float(self.config.get('MAX_SPOT_PRICE', '0.40'))
                if float(latest_price) > max_price:
                    print(f"⚠️  Warning: Current spot price (${latest_price}) > your max price (${max_price})")
                
                return True
            else:
                self.print_status(False, f"{instance_type} not available or no recent pricing data")
                return False
                
        except ClientError as e:
            self.print_status(False, f"Failed to check instance availability: {e}")
            return False

    def create_s3_bucket(self):
        """Create S3 bucket if it doesn't exist"""
        self.print_step(4, "Setting up S3 Bucket")
        
        bucket_name = self.config['S3_BUCKET_NAME']
        region = self.config['AWS_REGION']
        
        try:
            # Check if bucket exists
            try:
                self.s3.head_bucket(Bucket=bucket_name)
                self.print_status(True, f"S3 bucket '{bucket_name}' already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # Bucket doesn't exist, create it
                    print(f"Creating S3 bucket '{bucket_name}' in {region}...")
                    
                    if region == 'us-east-1':
                        # us-east-1 doesn't need LocationConstraint
                        self.s3.create_bucket(Bucket=bucket_name)
                    else:
                        self.s3.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': region}
                        )
                    
                    # Wait for bucket to be created
                    waiter = self.s3.get_waiter('bucket_exists')
                    waiter.wait(Bucket=bucket_name, WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
                    
                    # Block public access
                    self.s3.put_public_access_block(
                        Bucket=bucket_name,
                        PublicAccessBlockConfiguration={
                            'BlockPublicAcls': True,
                            'IgnorePublicAcls': True,
                            'BlockPublicPolicy': True,
                            'RestrictPublicBuckets': True
                        }
                    )
                    
                    self.print_status(True, f"S3 bucket '{bucket_name}' created successfully")
                    return True
                else:
                    raise e
                    
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyExists':
                print(f"❌ Bucket name '{bucket_name}' is already taken globally. Please choose a different name.")
                new_name = input("Enter a new bucket name: ").strip()
                if new_name:
                    self.update_env_value('S3_BUCKET_NAME', new_name)
                    return self.create_s3_bucket()  # Retry with new name
            else:
                self.print_status(False, f"Failed to create S3 bucket: {e}")
            return False

    def create_iam_role(self):
        """Create IAM role for EC2 instances"""
        self.print_step(5, "Setting up IAM Role")
        
        role_name = self.config['IAM_ROLE_NAME']
        bucket_name = self.config['S3_BUCKET_NAME']
        
        # Trust policy for EC2
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Policy for S3 access
        s3_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:HeadObject",
                        "s3:GetObject"
                    ],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:ListBucket"
                    ],
                    "Resource": f"arn:aws:s3:::{bucket_name}"
                }
            ]
        }
        
        try:
            # Check if role exists
            try:
                role = self.iam.get_role(RoleName=role_name)
                self.print_status(True, f"IAM role '{role_name}' already exists")
                role_arn = role['Role']['Arn']
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    # Create role
                    print(f"Creating IAM role '{role_name}'...")
                    response = self.iam.create_role(
                        RoleName=role_name,
                        AssumeRolePolicyDocument=json.dumps(trust_policy),
                        Description='IAM role for MusicGen batch worker instances'
                    )
                    role_arn = response['Role']['Arn']
                    self.print_status(True, f"IAM role '{role_name}' created")
                else:
                    raise e
            
            # Create and attach policy
            policy_name = f"{role_name}-s3-policy"
            policy_arn = f"arn:aws:iam::{self.config['AWS_ACCOUNT_ID']}:policy/{policy_name}"
            
            try:
                # Check if policy exists
                self.iam.get_policy(PolicyArn=policy_arn)
                self.print_status(True, f"IAM policy '{policy_name}' already exists")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    # Create policy
                    print(f"Creating IAM policy '{policy_name}'...")
                    response = self.iam.create_policy(
                        PolicyName=policy_name,
                        PolicyDocument=json.dumps(s3_policy),
                        Description='S3 access policy for MusicGen batch workers'
                    )
                    self.print_status(True, f"IAM policy '{policy_name}' created")
                else:
                    raise e
            
            # Attach policy to role
            try:
                self.iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                self.print_status(True, f"Policy attached to role")
            except ClientError as e:
                if e.response['Error']['Code'] != 'EntityAlreadyExists':
                    raise e
            
            # Create instance profile
            try:
                self.iam.get_instance_profile(InstanceProfileName=role_name)
                self.print_status(True, f"Instance profile '{role_name}' already exists")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    print(f"Creating instance profile '{role_name}'...")
                    self.iam.create_instance_profile(InstanceProfileName=role_name)
                    
                    # Add role to instance profile
                    self.iam.add_role_to_instance_profile(
                        InstanceProfileName=role_name,
                        RoleName=role_name
                    )
                    
                    # Wait for instance profile to be ready
                    time.sleep(10)
                    
                    self.print_status(True, f"Instance profile '{role_name}' created")
                else:
                    raise e
            
            return True
            
        except ClientError as e:
            self.print_status(False, f"Failed to set up IAM role: {e}")
            return False

    def check_key_pair(self):
        """Check if EC2 key pair exists and private key file is available"""
        self.print_step(6, "Checking EC2 Key Pair and Private Key")
        
        key_pair_name = self.config.get('KEY_PAIR_NAME', '')
        key_pair_path = self.config.get('KEY_PAIR_PATH', './keys/musicgen-batch-keypair.pem')
        
        if not key_pair_name or key_pair_name == 'your-ec2-keypair-name':
            print("⚠️  No key pair configured in .env file")
            self._print_key_pair_instructions()
            return False
        
        # Check if key pair exists in AWS
        aws_key_exists = False
        try:
            response = self.ec2.describe_key_pairs(KeyNames=[key_pair_name])
            if response['KeyPairs']:
                self.print_status(True, f"AWS key pair '{key_pair_name}' exists")
                aws_key_exists = True
            else:
                self.print_status(False, f"AWS key pair '{key_pair_name}' not found")
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
                self.print_status(False, f"AWS key pair '{key_pair_name}' not found")
            else:
                self.print_status(False, f"Failed to check key pair: {e}")
        
        # Check if private key file exists locally
        local_key_exists = False
        key_path = Path(key_pair_path)
        if key_path.exists():
            # Check file permissions (should be 600 for security)
            import stat
            file_stat = key_path.stat()
            file_mode = stat.filemode(file_stat.st_mode)
            
            self.print_status(True, f"Private key file exists: {key_pair_path}")
            
            # Check if permissions are secure
            if file_stat.st_mode & 0o077:  # Check if group/other have any permissions
                print(f"⚠️  Warning: Private key has insecure permissions: {file_mode}")
                print(f"   Run: chmod 600 {key_pair_path}")
            else:
                print(f"✅ Private key permissions are secure: {file_mode}")
            
            local_key_exists = True
        else:
            self.print_status(False, f"Private key file not found: {key_pair_path}")
        
        # Provide instructions if either is missing
        if not aws_key_exists or not local_key_exists:
            self._print_key_pair_instructions()
            return False
        
        return True
    
    def _print_key_pair_instructions(self):
        """Print instructions for setting up the key pair"""
        print("\nTo set up the EC2 key pair:")
        print("1. Go to AWS Console -> EC2 -> Key Pairs")
        print("2. Click 'Create key pair'")
        print("3. Name: musicgen-batch-keypair")
        print("4. Type: RSA")
        print("5. Format: .pem")
        print("6. Download the .pem file")
        print("7. Move it to: ./keys/musicgen-batch-keypair.pem")
        print("8. Set secure permissions: chmod 600 ./keys/musicgen-batch-keypair.pem")

    def setup_billing_alerts(self):
        """Provide instructions for setting up billing alerts"""
        self.print_step(7, "Billing Alert Setup")
        
        print("Setting up billing alerts is highly recommended to monitor costs.")
        print("To set up billing alerts:")
        print("1. Go to AWS Console -> Billing Dashboard")
        print("2. Click 'Budgets' in left sidebar")
        print("3. Click 'Create budget'")
        print("4. Choose 'Cost budget'")
        print("5. Set a reasonable monthly limit (e.g., $50)")
        print("6. Configure email notifications")
        print()
        response = input("Have you set up billing alerts? (y/N): ").strip().lower()
        return response in ['y', 'yes']

    def update_env_value(self, key, value):
        """Update a value in the .env file"""
        env_path = Path(".env")
        lines = []
        
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update the line
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                updated = True
                break
        
        # If not found, add it
        if not updated:
            lines.append(f"{key}={value}\n")
        
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        # Update in-memory config
        self.config[key] = value

    def run_all_checks(self):
        """Run all readiness checks"""
        self.print_header("AWS Account Readiness Check")
        
        if not self.initialize_aws_clients():
            return False
        
        checks = [
            ("Credentials", self.check_credentials),
            ("Permissions", self.check_permissions),
            ("Service Limits", self.check_service_limits),
            ("S3 Bucket", self.create_s3_bucket),
            ("IAM Role", self.create_iam_role),
            ("Key Pair", self.check_key_pair),
            ("Billing Alerts", self.setup_billing_alerts),
        ]
        
        results = {}
        for name, check_func in checks:
            try:
                results[name] = check_func()
            except Exception as e:
                print(f"❌ {name} check failed with error: {e}")
                results[name] = False
        
        # Summary
        self.print_header("Readiness Summary")
        
        passed = sum(results.values())
        total = len(results)
        
        for name, result in results.items():
            self.print_status(result, f"{name}")
        
        print(f"\nOverall: {passed}/{total} checks passed")
        
        if passed == total:
            self.print_header("🎉 AWS Account is Ready!")
            print("Your AWS account is properly configured for the MusicGen batch system.")
            print()
            print("Next steps:")
            print("1. Create Phase 2 AMI (see TASKS.md)")
            print("2. Implement the launcher script")
            print("3. Test the complete system")
            return True
        else:
            print("\n⚠️  Some checks failed. Please address the issues above before proceeding.")
            return False


def main():
    """Main function"""
    checker = AWSReadinessChecker()
    success = checker.run_all_checks()
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCheck cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)