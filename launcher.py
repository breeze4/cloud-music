#!/usr/bin/env python3
"""
MusicGen Batch System Launcher

This script manages EC2 spot instance lifecycle for the batch MusicGen generation system.
It checks for existing instances, displays current spot pricing, and launches new instances as needed.
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
    """Manages EC2 spot instances for MusicGen batch processing"""
    
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
            
            # Test spot price permissions
            self.ec2_client.describe_spot_price_history(
                InstanceTypes=[config.aws.instance_type],
                MaxResults=1
            )
            
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
    
    def get_current_spot_prices(self) -> Dict[str, float]:
        """
        Get current spot prices for the configured instance type across availability zones.
        
        Returns:
            Dictionary mapping availability zone to current spot price
        """
        try:
            logger.info(f"Querying spot price history for {config.aws.instance_type} in {config.aws.region}")
            response = self.ec2_client.describe_spot_price_history(
                InstanceTypes=[config.aws.instance_type],
                ProductDescriptions=['Linux/UNIX'],
                MaxResults=20  # Get recent prices across AZs - removed StartTime=None
            )
            logger.info(f"Received {len(response.get('SpotPriceHistory', []))} spot price records")
            
            # Group by availability zone and get the most recent price for each
            zone_prices = {}
            for price_info in response['SpotPriceHistory']:
                zone = price_info['AvailabilityZone']
                price = float(price_info['SpotPrice'])
                timestamp = price_info['Timestamp']
                
                logger.debug(f"Spot price record: {zone} = ${price:.3f} at {timestamp}")
                
                # Keep the most recent (first in results) price for each zone
                if zone not in zone_prices:
                    zone_prices[zone] = price
            
            logger.info(f"Final zone prices: {zone_prices}")
            return zone_prices
            
        except ClientError as e:
            logger.error(f"AWS ClientError getting spot prices: {e}")
            logger.error(f"Error code: {e.response.get('Error', {}).get('Code', 'Unknown')}")
            logger.error(f"Error message: {e.response.get('Error', {}).get('Message', 'Unknown')}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting spot prices: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def display_spot_prices(self, zone_prices: Dict[str, float]) -> None:
        """Display current spot pricing information"""
        if not zone_prices:
            print("\n⚠️  Could not retrieve current spot prices.")
            print(f"Proceeding with configured max price: ${config.aws.max_spot_price:.3f}/hour")
            return
        
        print(f"\n💰 Current spot prices for {config.aws.instance_type}:")
        print("-" * 60)
        
        for zone, price in sorted(zone_prices.items()):
            status = "✅" if price <= config.aws.max_spot_price else "❌"
            savings = ((config.aws.max_spot_price - price) / config.aws.max_spot_price) * 100
            
            print(f"{status} {zone:<15} ${price:.3f}/hour", end="")
            if price <= config.aws.max_spot_price:
                print(f" (saves {savings:.1f}%)")
            else:
                print(f" (exceeds max by ${price - config.aws.max_spot_price:.3f})")
        
        print(f"\nConfigured max price: ${config.aws.max_spot_price:.3f}/hour")
        
        # Show cost estimates
        print(f"\nEstimated costs for common scenarios:")
        print(f"  • 1 hour of generation:  ${config.aws.max_spot_price:.2f}")
        print(f"  • 4 hours of generation: ${config.aws.max_spot_price * 4:.2f}")
        print(f"  • 8 hours of generation: ${config.aws.max_spot_price * 8:.2f}")
    
    def get_user_confirmation(self) -> bool:
        """
        Get user confirmation to proceed with instance launch.
        
        Returns:
            True if user confirms, False otherwise
        """
        print("\n" + "="*60)
        print("⚠️  COST WARNING")
        print("="*60)
        print(f"You are about to launch a {config.aws.instance_type} spot instance")
        print(f"with a maximum price of ${config.aws.max_spot_price:.2f}/hour.")
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
    
    def launch_spot_instance(self) -> bool:
        """
        Launch a spot instance with the configured parameters.
        
        Returns:
            True if spot request was submitted successfully, False otherwise
        """
        try:
            # Get or create security group
            security_group_id = self.get_or_create_security_group()
            
            # Prepare the spot instance request
            spot_request = {
                'ImageId': config.aws.ami_id,
                'InstanceType': config.aws.instance_type,
                'KeyName': config.aws.key_pair_name,
                'SecurityGroupIds': [security_group_id],
                'UserData': config.get_user_data_script(),
                'IamInstanceProfile': {
                    'Arn': config.aws.iam_role_arn
                },
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
            
            # Submit spot instance request
            logger.info(f"Submitting spot request with max price: ${config.aws.max_spot_price:.3f}/hour")
            response = self.ec2_client.request_spot_instances(
                SpotPrice=str(config.aws.max_spot_price),
                InstanceCount=1,
                Type='one-time',
                LaunchSpecification=spot_request
            )
            
            # Log the request details
            spot_request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
            logger.info(f"Spot request submitted: {spot_request_id}")
            
            # Wait a moment and check initial status
            import time
            time.sleep(2)
            
            status_response = self.ec2_client.describe_spot_instance_requests(
                SpotInstanceRequestIds=[spot_request_id]
            )
            
            status = status_response['SpotInstanceRequests'][0]['State']
            logger.info(f"Initial spot request status: {status}")
            
            if status == 'failed':
                fault = status_response['SpotInstanceRequests'][0].get('Fault', {})
                logger.error(f"Spot request failed: {fault.get('Message', 'Unknown error')}")
                return False
            
            print(f"\n📋 Spot Request Details:")
            print(f"   Request ID: {spot_request_id}")
            print(f"   Status: {status}")
            print(f"   Max Price: ${config.aws.max_spot_price:.3f}/hour")
            print(f"   Instance Type: {config.aws.instance_type}")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            if error_code == 'SpotMaxPriceTooLow':
                logger.error(f"Spot price too low: {error_msg}")
                print(f"\n❌ Your max price of ${config.aws.max_spot_price:.3f}/hour is too low.")
                print("Try increasing the max price in your configuration.")
            elif error_code == 'InsufficientInstanceCapacity':
                logger.error(f"Insufficient capacity: {error_msg}")
                print(f"\n❌ No {config.aws.instance_type} instances available in the current region.")
                print("Try again later or consider a different instance type.")
            else:
                logger.error(f"Spot request failed: {error_code} - {error_msg}")
            
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error launching spot instance: {e}")
            return False
    
    def run(self) -> None:
        """Main launcher logic"""
        try:
            logger.info("Starting MusicGen Batch System Launcher")
            logger.info(f"Target region: {config.aws.region}")
            logger.info(f"Instance type: {config.aws.instance_type}")
            logger.info(f"Max spot price: ${config.aws.max_spot_price:.2f}/hour")
            
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
            
            # Get and display current spot prices
            logger.info("Checking current spot prices...")
            zone_prices = self.get_current_spot_prices()
            self.display_spot_prices(zone_prices)
            
            # Get user confirmation
            if not self.get_user_confirmation():
                logger.info("User declined to proceed")
                sys.exit(0)
            
            # Launch spot instance
            logger.info("Launching spot instance...")
            success = self.launch_spot_instance()
            
            if success:
                logger.info("✅ Spot instance request submitted successfully!")
                print("\n🚀 Instance launch initiated!")
                print("The worker will start automatically once the instance is running.")
                print("You can monitor progress in the AWS console.")
                print("\n⚠️  IMPORTANT: Remember to terminate the instance when done!")
            else:
                logger.error("❌ Failed to launch spot instance")
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