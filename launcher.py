#!/usr/bin/env python3
"""
MusicGen Batch System Launcher

This script manages EC2 on-demand instance lifecycle for the batch MusicGen generation system.
It checks for existing instances, displays current on-demand pricing, and launches new instances as needed.
"""

import boto3
import logging
import sys
from typing import List, Optional, Dict, Any
from botocore.exceptions import ClientError, BotoCoreError

from config import config


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MusicGenLauncher:
    """Manages EC2 on-demand instances for MusicGen batch processing"""
    
    def __init__(self):
        try:
            self.ec2_client = boto3.client('ec2', region_name=config.aws.region)
            self.ec2_resource = boto3.resource('ec2', region_name=config.aws.region)
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            sys.exit(1)
    
    def check_existing_instances(self) -> List[Dict[str, Any]]:
        """
        Check for existing EC2 instances with the musicgen-batch-worker tag.
        
        Returns:
            List of instance dictionaries with relevant information
        """
        try:
            response = self.ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:Name',
                        'Values': [config.aws.worker_tag]
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running', 'pending', 'stopping']
                    }
                ]
            )
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'instance_id': instance['InstanceId'],
                        'state': instance['State']['Name'],
                        'instance_type': instance['InstanceType'],
                        'launch_time': instance.get('LaunchTime'),
                        'public_ip': instance.get('PublicIpAddress'),
                        'private_ip': instance.get('PrivateIpAddress')
                    })
            
            return instances
            
        except ClientError as e:
            logger.error(f"AWS API error checking instances: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error checking instances: {e}")
            return []
    
    def display_existing_instances(self, instances: List[Dict[str, Any]]) -> None:
        """Display information about existing instances"""
        if not instances:
            logger.info("No existing MusicGen instances found.")
            return
        
        print(f"\nFound {len(instances)} existing MusicGen instance(s):")
        print("-" * 80)
        
        for i, instance in enumerate(instances, 1):
            print(f"{i}. Instance ID: {instance['instance_id']}")
            print(f"   State: {instance['state']}")
            print(f"   Type: {instance['instance_type']}")
            print(f"   Launch Time: {instance['launch_time']}")
            print(f"   Public IP: {instance['public_ip'] or 'N/A'}")
            print(f"   Private IP: {instance['private_ip'] or 'N/A'}")
            print()
    
    def check_aws_permissions(self) -> bool:
        """
        Check if we have the necessary AWS permissions.
        
        Returns:
            True if permissions are adequate, False otherwise
        """
        try:
            # Test EC2 permissions
            self.ec2_client.describe_instances(MaxResults=5)
            
            logger.info("AWS permissions check passed.")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                logger.error(f"Insufficient AWS permissions: {e}")
                return False
            else:
                logger.warning(f"Permission check inconclusive: {e}")
                return True  # Assume permissions are OK if it's not a clear auth error
        except Exception as e:
            logger.error(f"Unexpected error checking permissions: {e}")
            return False
    
    
    def display_on_demand_pricing(self, hourly_rate: float) -> None:
        """Display on-demand pricing information"""
        print(f"\n💰 On-demand pricing for {config.aws.instance_type}:")
        print("-" * 60)
        print(f"   Hourly Rate: ${hourly_rate:.3f}/hour")
        
        # Show cost estimates
        print(f"\nEstimated costs for common scenarios:")
        print(f"  • 1 hour of generation:  ${hourly_rate:.2f}")
        print(f"  • 4 hours of generation: ${hourly_rate * 4:.2f}")
        print(f"  • 8 hours of generation: ${hourly_rate * 8:.2f}")
    
    
    def get_user_confirmation(self) -> bool:
        """
        Get user confirmation to proceed with instance launch.
        
        Returns:
            True if user confirms, False otherwise
        """
        print("\n" + "="*60)
        print("⚠️  COST WARNING")
        print("="*60)
        on_demand_rate = self.get_on_demand_pricing()
        print(f"You are about to launch a {config.aws.instance_type} on-demand instance")
        print(f"at a rate of ${on_demand_rate:.2f}/hour.")
        print()
        print("⚠️  REMEMBER: You must manually terminate the instance when done!")
        print("⚠️  Forgetting to terminate will result in ongoing charges!")
        print("="*60)
        
        while True:
            response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                print("Please enter 'yes' or 'no'")
    
    def get_or_create_security_group(self) -> str:
        """
        Get existing security group or create a new one for MusicGen instances.
        
        Returns:
            Security group ID
        """
        try:
            # First, try to find existing security group
            try:
                response = self.ec2_client.describe_security_groups(
                    GroupNames=[config.aws.security_group_name]
                )
                sg_id = response['SecurityGroups'][0]['GroupId']
                logger.info(f"Using existing security group: {sg_id}")
                return sg_id
            except ClientError as e:
                if e.response['Error']['Code'] != 'InvalidGroup.NotFound':
                    raise
            
            # Create new security group
            logger.info(f"Creating security group: {config.aws.security_group_name}")
            response = self.ec2_client.create_security_group(
                GroupName=config.aws.security_group_name,
                Description='Security group for MusicGen batch processing instances'
            )
            sg_id = response['GroupId']
            
            # Add SSH access rule
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH access'}]
                    }
                ]
            )
            
            logger.info(f"Created security group: {sg_id}")
            return sg_id
            
        except ClientError as e:
            logger.error(f"Failed to get/create security group: {e}")
            raise
    
    def encode_user_data(self, user_data: str) -> str:
        """Properly encode UserData script for EC2"""
        import base64
        logger.debug(f"UserData script length: {len(user_data)} characters")
        logger.debug(f"UserData script first 200 chars: {user_data[:200]}...")
        encoded = base64.b64encode(user_data.encode('utf-8')).decode('utf-8')
        logger.debug(f"Encoded UserData length: {len(encoded)} characters")
        return encoded
    
    def tag_instance(self, instance_id: str) -> None:
        """Tag an EC2 instance with our standard tags"""
        try:
            logger.info(f"Tagging instance {instance_id}")
            self.ec2_client.create_tags(
                Resources=[instance_id],
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': config.aws.worker_tag
                    },
                    {
                        'Key': 'Project', 
                        'Value': 'musicgen-batch'
                    },
                    {
                        'Key': 'AutoShutdown',
                        'Value': 'manual'
                    }
                ]
            )
            logger.info(f"Successfully tagged instance {instance_id}")
        except Exception as e:
            logger.error(f"Failed to tag instance {instance_id}: {e}")
    
    def get_on_demand_pricing(self) -> float:
        """
        Get on-demand pricing for the configured instance type.
        
        Returns:
            On-demand hourly rate in USD
        """
        # Static pricing for common instance types (approximate)
        pricing = {
            'g4dn.xlarge': 0.526,
            'g4dn.2xlarge': 0.752,
            'p3.2xlarge': 3.06,
            'p3.8xlarge': 12.24,
            'm5.large': 0.096,
            'm5.xlarge': 0.192
        }
        
        return pricing.get(config.aws.instance_type, 0.50)  # Default fallback
    
    def launch_instance(self) -> bool:
        """
        Launch an on-demand instance with the configured parameters.
        
        Returns:
            True if instance was launched successfully, False otherwise
        """
        try:
            # Get or create security group
            security_group_id = self.get_or_create_security_group()
            
            # Prepare the instance launch parameters
            launch_params = {
                'ImageId': config.aws.ami_id,
                'InstanceType': config.aws.instance_type,
                'KeyName': config.aws.key_pair_name,
                'SecurityGroupIds': [security_group_id],
                'UserData': self.encode_user_data(config.get_user_data_script()),
                'IamInstanceProfile': {
                    'Name': config.aws.iam_role_name
                },
                'MinCount': 1,
                'MaxCount': 1,
                'BlockDeviceMappings': [
                    {
                        'DeviceName': '/dev/sda1',
                        'Ebs': {
                            'VolumeSize': 80,
                            'VolumeType': 'gp3',
                            'DeleteOnTermination': True
                        }
                    }
                ],
                'TagSpecifications': [
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {
                                'Key': 'Name',
                                'Value': config.aws.worker_tag
                            },
                            {
                                'Key': 'Project',
                                'Value': 'musicgen-batch'
                            },
                            {
                                'Key': 'AutoShutdown',
                                'Value': 'manual'
                            }
                        ]
                    }
                ]
            }
            
            # Launch on-demand instance
            on_demand_rate = self.get_on_demand_pricing()
            logger.info(f"Launching on-demand instance at ${on_demand_rate:.3f}/hour")
            response = self.ec2_client.run_instances(**launch_params)
            
            # Get instance details
            instance = response['Instances'][0]
            instance_id = instance['InstanceId']
            logger.info(f"Instance launched: {instance_id}")
            
            # Wait a moment and check initial status
            import time
            time.sleep(2)
            
            status_response = self.ec2_client.describe_instances(
                InstanceIds=[instance_id]
            )
            
            instance_state = status_response['Reservations'][0]['Instances'][0]['State']['Name']
            logger.info(f"Initial instance status: {instance_state}")
            
            print(f"\n📋 Instance Details:")
            print(f"   Instance ID: {instance_id}")
            print(f"   Status: {instance_state}")
            print(f"   On-demand Rate: ${on_demand_rate:.3f}/hour")
            print(f"   Instance Type: {config.aws.instance_type}")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            if error_code == 'InsufficientInstanceCapacity':
                logger.error(f"Insufficient capacity: {error_msg}")
                print(f"\n❌ No {config.aws.instance_type} instances available in the current region.")
                print("Try again later or consider a different instance type.")
            elif error_code == 'UnauthorizedOperation':
                logger.error(f"Permission denied: {error_msg}")
                print(f"\n❌ Insufficient permissions to launch EC2 instances.")
                print("Check your IAM permissions for ec2:RunInstances.")
            else:
                logger.error(f"Instance launch failed: {error_code} - {error_msg}")
            
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error launching instance: {e}")
            return False
    
    def run(self) -> None:
        """Main launcher logic"""
        try:
            logger.info("Starting MusicGen Batch System Launcher")
            logger.info(f"Target region: {config.aws.region}")
            logger.info(f"Instance type: {config.aws.instance_type}")
            on_demand_rate = self.get_on_demand_pricing()
            logger.info(f"On-demand rate: ${on_demand_rate:.2f}/hour")
            
            # Check AWS permissions
            if not self.check_aws_permissions():
                logger.error("Insufficient AWS permissions. Please check your credentials and IAM policies.")
                sys.exit(1)
            
            # Check for existing instances
            existing_instances = self.check_existing_instances()
            self.display_existing_instances(existing_instances)
            
            # If instances exist, ask user what to do
            if existing_instances:
                print("\nExisting instances found. Options:")
                print("1. Continue anyway (launch additional instance)")
                print("2. Exit (use existing instances)")
                
                while True:
                    choice = input("\nEnter your choice (1 or 2): ").strip()
                    if choice == '1':
                        logger.info("User chose to launch additional instance")
                        break
                    elif choice == '2':
                        logger.info("User chose to exit and use existing instances")
                        sys.exit(0)
                    else:
                        print("Please enter 1 or 2")
            
            # Display on-demand pricing
            logger.info("Checking on-demand pricing...")
            on_demand_rate = self.get_on_demand_pricing()
            self.display_on_demand_pricing(on_demand_rate)
            
            # Get user confirmation
            if not self.get_user_confirmation():
                logger.info("User declined to proceed")
                sys.exit(0)
            
            # Launch on-demand instance
            logger.info("Launching on-demand instance...")
            success = self.launch_instance()
            
            if success:
                logger.info("✅ On-demand instance launched successfully!")
                print("\n🚀 Instance launched successfully!")
                print("The worker will start automatically once the instance is running.")
                print("You can monitor progress in the AWS console.")
                print("\n⚠️  IMPORTANT: Remember to terminate the instance when done!")
            else:
                logger.error("❌ Failed to launch instance")
                sys.exit(1)
            
        except KeyboardInterrupt:
            logger.info("Launcher interrupted by user")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Launcher failed with unexpected error: {e}")
            sys.exit(1)


def main():
    """Entry point for the launcher script"""
    try:
        launcher = MusicGenLauncher()
        launcher.run()
    except Exception as e:
        logger.error(f"Failed to start launcher: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()