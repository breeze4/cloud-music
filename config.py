"""
Configuration settings for the MusicGen batch generation system.
This file contains AWS resource identifiers and system settings.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class AWSConfig:
    """AWS configuration settings"""
    region: str
    ami_id: str
    iam_role_arn: str
    s3_bucket_name: str
    key_pair_name: str
    max_spot_price: float
    instance_type: str
    security_group_name: str
    worker_tag: str = "musicgen-batch-worker"


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.aws = self._load_aws_config()
        self.validate()
    
    def _load_aws_config(self) -> AWSConfig:
        """Load AWS configuration from environment variables"""
        account_id = os.getenv('AWS_ACCOUNT_ID', '')
        iam_role_name = os.getenv('IAM_ROLE_NAME', '')
        iam_role_arn = f"arn:aws:iam::{account_id}:role/{iam_role_name}" if account_id and iam_role_name else ''
        
        return AWSConfig(
            region=os.getenv('AWS_REGION', 'us-east-1'),
            ami_id=os.getenv('AMI_ID', ''),
            iam_role_arn=iam_role_arn,
            s3_bucket_name=os.getenv('S3_BUCKET_NAME', ''),
            key_pair_name=os.getenv('KEY_PAIR_NAME', ''),
            max_spot_price=float(os.getenv('MAX_SPOT_PRICE', '0.40')),
            instance_type=os.getenv('INSTANCE_TYPE', 'g4dn.xlarge'),
            security_group_name=os.getenv('SECURITY_GROUP_NAME', 'musicgen-worker-sg')
        )
    
    def validate(self) -> None:
        """Validate that all required configuration values are present"""
        errors = []
        
        if not self.aws.ami_id:
            errors.append("AMI_ID environment variable is required")
        
        if not self.aws.iam_role_arn:
            errors.append("AWS_ACCOUNT_ID and IAM_ROLE_NAME environment variables are required")
        
        if not self.aws.s3_bucket_name:
            errors.append("S3_BUCKET_NAME environment variable is required")
        
        if not self.aws.key_pair_name:
            errors.append("KEY_PAIR_NAME environment variable is required")
        
        if self.aws.max_spot_price <= 0:
            errors.append("MAX_SPOT_PRICE must be greater than 0")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)
    
    def get_user_data_script(self) -> str:
        """Generate the UserData script for EC2 bootstrap"""
        return f"""#!/bin/bash
set -e
exec > >(tee /var/log/user-data.log) 2>&1

echo "Starting MusicGen worker bootstrap..."

# Update system and install required packages
apt-get update -y
apt-get install -y git python3-pip curl

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:$PATH"

# Set up working directory
cd /home/ubuntu
chown ubuntu:ubuntu /home/ubuntu

# Clone repository (update this URL to your actual repository)
# TODO: Replace with your actual git repository URL
sudo -u ubuntu git clone https://github.com/breeze4/cloud-music.git musicgen-batch || echo "Repository already exists"
cd musicgen-batch
sudo -u ubuntu git pull origin main || echo "Pull failed or not needed"

# Install Python dependencies
sudo -u ubuntu /root/.local/bin/uv sync

# Set up environment variables for worker (matching worker.py expectations)
export AWS_DEFAULT_REGION={self.aws.region}
export MUSICGEN_S3_BUCKET={self.aws.s3_bucket_name}
export MUSICGEN_HOURLY_COST={self.aws.max_spot_price}

echo "Environment configured, starting worker..."

# Set up log file with proper permissions
touch /var/log/musicgen-worker.log
chown ubuntu:ubuntu /var/log/musicgen-worker.log
chmod 644 /var/log/musicgen-worker.log

echo "Starting worker script - monitor with: tail -f /var/log/musicgen-worker.log"

# Run the worker script as ubuntu user
sudo -u ubuntu -E /root/.local/bin/uv run python worker.py

echo "Worker script completed."
echo "View final logs: cat /var/log/musicgen-worker.log"
"""


# Global config instance
config = Config()