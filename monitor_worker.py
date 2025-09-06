#!/usr/bin/env python3
"""
Quick monitoring script for MusicGen worker
Provides easy access to logs and status from your local machine
"""

import boto3
import sys
import subprocess
import time
from config import config

def get_worker_instance():
    """Find the running worker instance"""
    ec2 = boto3.client('ec2', region_name=config.aws.region)
    
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [config.aws.worker_tag]},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
            ]
        )
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append({
                    'id': instance['InstanceId'],
                    'state': instance['State']['Name'],
                    'ip': instance.get('PublicIpAddress', 'No IP yet'),
                    'type': instance['InstanceType']
                })
        
        return instances
    except Exception as e:
        print(f"Error finding instances: {e}")
        return []

def ssh_to_instance(instance_ip, command=None):
    """SSH to instance and optionally run a command"""
    key_path = f"keys/{config.aws.key_pair_name}.pem"  # Adjust path as needed
    
    if command:
        ssh_cmd = [
            'ssh', '-i', key_path, 
            '-o', 'StrictHostKeyChecking=no',
            f'ubuntu@{instance_ip}',
            command
        ]
    else:
        ssh_cmd = [
            'ssh', '-i', key_path,
            '-o', 'StrictHostKeyChecking=no', 
            f'ubuntu@{instance_ip}'
        ]
    
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"SSH failed: {e}")
    except FileNotFoundError:
        print(f"Key file not found: {key_path}")
        print("Update the key_path in this script or use SSH manually")

def main():
    if len(sys.argv) < 2:
        print("MusicGen Worker Monitor")
        print("Usage:")
        print("  python monitor_worker.py status    - Show instance status") 
        print("  python monitor_worker.py logs      - Show recent worker logs")
        print("  python monitor_worker.py tail      - Follow worker logs in real-time")
        print("  python monitor_worker.py bootstrap - Show bootstrap/system logs") 
        print("  python monitor_worker.py system    - Follow all system logs")
        print("  python monitor_worker.py ssh       - SSH to worker instance")
        print("  python monitor_worker.py s3        - Show S3 outputs")
        return

    command = sys.argv[1].lower()
    
    # Find worker instance
    instances = get_worker_instance()
    
    if not instances:
        print("❌ No running worker instances found")
        print("Run launcher.py to start a new instance")
        return
    
    instance = instances[0]  # Use first found instance
    print(f"🖥️  Found worker: {instance['id']} ({instance['state']}) - {instance['ip']}")
    
    if command == 'status':
        print(f"\nInstance Details:")
        print(f"  ID: {instance['id']}")
        print(f"  State: {instance['state']}")  
        print(f"  IP: {instance['ip']}")
        print(f"  Type: {instance['type']}")
        
        if instance['state'] == 'running':
            print(f"\n📋 Quick Commands:")
            print(f"  SSH: ssh -i keys/{config.aws.key_pair_name}.pem ubuntu@{instance['ip']}")
            print(f"  Logs: python monitor_worker.py logs")
            print(f"  Real-time: python monitor_worker.py tail")
            print(f"  Bootstrap: python monitor_worker.py bootstrap")
            print(f"  System: python monitor_worker.py system")
    
    elif command == 'logs':
        if instance['state'] != 'running':
            print("❌ Instance not running")
            return
        print("📜 Recent worker logs:")
        ssh_to_instance(instance['ip'], 'tail -50 /var/log/musicgen-worker.log 2>/dev/null || tail -50 ~/musicgen-worker.log 2>/dev/null || echo "No worker logs found yet"')
    
    elif command == 'tail':
        if instance['state'] != 'running':
            print("❌ Instance not running") 
            return
        print("📜 Following worker logs (Ctrl+C to stop):")
        ssh_to_instance(instance['ip'], 'tail -f /var/log/musicgen-worker.log 2>/dev/null || tail -f ~/musicgen-worker.log 2>/dev/null || echo "No worker logs found yet"')
    
    elif command == 'bootstrap':
        if instance['state'] != 'running':
            print("❌ Instance not running")
            return
        print("🔧 Bootstrap/UserData logs:")
        ssh_to_instance(instance['ip'], 'echo "=== Cloud-init output ===" && sudo cat /var/log/cloud-init-output.log 2>/dev/null | tail -100 || echo "No cloud-init-output.log found"; echo -e "\n=== Cloud-init log ===" && sudo cat /var/log/cloud-init.log 2>/dev/null | tail -50 || echo "No cloud-init.log found"')
    
    elif command == 'system':
        if instance['state'] != 'running':
            print("❌ Instance not running") 
            return
        print("📜 Following system logs (Ctrl+C to stop):")
        print("This will show cloud-init progress, uv setup, worker startup...")
        ssh_to_instance(instance['ip'], 'sudo tail -f /var/log/cloud-init-output.log 2>/dev/null || echo "Switching to worker logs..."; tail -f /var/log/musicgen-worker.log 2>/dev/null || tail -f ~/musicgen-worker.log 2>/dev/null || echo "No logs found yet"')
    
    elif command == 'ssh':
        if instance['state'] != 'running':
            print("❌ Instance not running")
            return
        print("🔗 Connecting to worker instance...")
        ssh_to_instance(instance['ip'])
    
    elif command == 's3':
        print("📁 Current S3 outputs:")
        try:
            s3 = boto3.client('s3', region_name=config.aws.region)
            response = s3.list_objects_v2(Bucket=config.aws.s3_bucket_name)
            
            if 'Contents' in response:
                for obj in sorted(response['Contents'], key=lambda x: x['LastModified']):
                    size_mb = obj['Size'] / 1024 / 1024
                    print(f"  {obj['Key']} ({size_mb:.1f}MB) - {obj['LastModified']}")
            else:
                print("  No files found")
                
        except Exception as e:
            print(f"Error listing S3 files: {e}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()