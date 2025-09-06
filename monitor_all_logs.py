#!/usr/bin/env python3
"""
Unified MusicGen Log Monitor
Shows all log sources (bootstrap, system, worker) in a single view
"""

import boto3
import sys
import subprocess
import time
import threading
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

def ssh_command(instance_ip, command):
    """Execute SSH command and return output"""
    key_path = f"keys/{config.aws.key_pair_name}.pem"
    
    ssh_cmd = [
        'ssh', '-i', key_path,
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        f'ubuntu@{instance_ip}',
        command
    ]
    
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return f"SSH Error: {e}"
    except FileNotFoundError:
        return f"Key file not found: {key_path}"

def monitor_logs_unified(instance_ip):
    """Monitor all log sources in a unified view"""
    print("🔍 Unified Log Monitor - All Sources")
    print("=" * 80)
    print("Checking bootstrap logs, system logs, and worker logs...")
    print("=" * 80)
    
    # Check bootstrap completion status first
    print("\n📋 BOOTSTRAP STATUS:")
    print("-" * 40)
    bootstrap_status = ssh_command(instance_ip, """
        if [ -f /var/log/cloud-init.log ]; then
            echo "✅ Cloud-init log exists"
            if grep -q "Cloud-init.*finished" /var/log/cloud-init.log 2>/dev/null; then
                echo "✅ Bootstrap completed"
            else
                echo "🔄 Bootstrap in progress"
            fi
        else
            echo "❌ No cloud-init log found"
        fi
        
        if [ -f /var/log/user-data.log ]; then
            echo "✅ UserData log exists"
        else
            echo "❌ No UserData log found"
        fi
        
        if [ -f /var/log/musicgen-worker.log ] || [ -f ~/musicgen-worker.log ]; then
            echo "✅ Worker log exists"
        else
            echo "❌ No worker log found yet"
        fi
    """)
    print(bootstrap_status)
    
    # Show recent activity from all sources
    print("\n📜 RECENT ACTIVITY (Last 20 lines from each source):")
    print("-" * 60)
    
    print("\n🔧 BOOTSTRAP LOGS:")
    print("-" * 30)
    bootstrap_logs = ssh_command(instance_ip, """
        echo "=== UserData Log ==="
        tail -20 /var/log/user-data.log 2>/dev/null || echo "No UserData log"
        echo -e "\n=== Cloud-Init Output ==="
        sudo tail -20 /var/log/cloud-init-output.log 2>/dev/null || echo "No cloud-init-output log"
    """)
    print(bootstrap_logs)
    
    print("\n🖥️ WORKER LOGS:")
    print("-" * 30)
    worker_logs = ssh_command(instance_ip, """
        tail -20 /var/log/musicgen-worker.log 2>/dev/null || tail -20 ~/musicgen-worker.log 2>/dev/null || echo "No worker logs yet"
    """)
    print(worker_logs)
    
    print("\n" + "=" * 80)
    print("📊 LIVE MONITORING OPTIONS:")
    print("1. Press 'b' + Enter for live bootstrap logs")
    print("2. Press 'w' + Enter for live worker logs")  
    print("3. Press 's' + Enter for smart follow (auto-switch)")
    print("4. Press 'q' + Enter to quit")
    print("=" * 80)
    
    while True:
        try:
            choice = input("\nChoose monitoring mode: ").strip().lower()
            
            if choice == 'q':
                print("👋 Monitoring stopped")
                break
            elif choice == 'b':
                print("🔧 Following bootstrap logs (Ctrl+C to return to menu):")
                follow_bootstrap_logs(instance_ip)
            elif choice == 'w':
                print("🖥️ Following worker logs (Ctrl+C to return to menu):")
                follow_worker_logs(instance_ip)
            elif choice == 's':
                print("🤖 Smart monitoring - auto-switching between log sources:")
                smart_follow_logs(instance_ip)
            else:
                print("Invalid choice. Use 'b', 'w', 's', or 'q'")
                
        except KeyboardInterrupt:
            print("\n\nReturning to menu...")
            continue

def follow_bootstrap_logs(instance_ip):
    """Follow bootstrap logs in real-time"""
    key_path = f"keys/{config.aws.key_pair_name}.pem"
    ssh_cmd = [
        'ssh', '-i', key_path,
        '-o', 'StrictHostKeyChecking=no',
        f'ubuntu@{instance_ip}',
        'sudo tail -f /var/log/cloud-init-output.log 2>/dev/null || tail -f /var/log/user-data.log 2>/dev/null || echo "No bootstrap logs to follow"'
    ]
    
    try:
        subprocess.run(ssh_cmd)
    except KeyboardInterrupt:
        pass

def follow_worker_logs(instance_ip):
    """Follow worker logs in real-time"""
    key_path = f"keys/{config.aws.key_pair_name}.pem"
    ssh_cmd = [
        'ssh', '-i', key_path,
        '-o', 'StrictHostKeyChecking=no',
        f'ubuntu@{instance_ip}',
        'tail -f /var/log/musicgen-worker.log 2>/dev/null || tail -f ~/musicgen-worker.log 2>/dev/null || echo "No worker logs to follow"'
    ]
    
    try:
        subprocess.run(ssh_cmd)
    except KeyboardInterrupt:
        pass

def smart_follow_logs(instance_ip):
    """Intelligently follow logs based on system state"""
    print("🤖 Analyzing system state to determine best log source...")
    
    # Check what's currently active
    status_check = ssh_command(instance_ip, """
        # Check if bootstrap is still running
        if pgrep -f "cloud-init" > /dev/null; then
            echo "BOOTSTRAP_ACTIVE"
        elif pgrep -f "uv.*worker.py" > /dev/null; then
            echo "WORKER_ACTIVE" 
        elif [ -f /var/log/musicgen-worker.log ] && [ -s /var/log/musicgen-worker.log ]; then
            echo "WORKER_LOGS_EXIST"
        elif sudo tail -1 /var/log/cloud-init-output.log 2>/dev/null | grep -q "starting worker"; then
            echo "WORKER_STARTING"
        else
            echo "BOOTSTRAP_LIKELY"
        fi
    """).strip()
    
    if "BOOTSTRAP_ACTIVE" in status_check:
        print("🔧 Bootstrap is active - following bootstrap logs...")
        follow_bootstrap_logs(instance_ip)
    elif "WORKER_ACTIVE" in status_check or "WORKER_LOGS_EXIST" in status_check:
        print("🖥️ Worker is active - following worker logs...")  
        follow_worker_logs(instance_ip)
    elif "WORKER_STARTING" in status_check:
        print("🔄 Worker is starting - monitoring transition...")
        # Use a multi-source tail command
        key_path = f"keys/{config.aws.key_pair_name}.pem"
        ssh_cmd = [
            'ssh', '-i', key_path,
            '-o', 'StrictHostKeyChecking=no',
            f'ubuntu@{instance_ip}',
            '''
            echo "Following transition from bootstrap to worker..."
            (
                sudo tail -f /var/log/cloud-init-output.log 2>/dev/null &
                sleep 5
                tail -f /var/log/musicgen-worker.log 2>/dev/null || tail -f ~/musicgen-worker.log 2>/dev/null &
                wait
            )
            '''
        ]
        try:
            subprocess.run(ssh_cmd)
        except KeyboardInterrupt:
            pass
    else:
        print("🔧 Defaulting to bootstrap logs...")
        follow_bootstrap_logs(instance_ip)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Unified MusicGen Log Monitor")
        print("Usage: python monitor_all_logs.py")
        print("\nThis script provides a unified view of all log sources:")
        print("  • Bootstrap/UserData logs (system setup, uv install)")
        print("  • Cloud-init logs (system initialization)")  
        print("  • Worker logs (MusicGen processing)")
        print("\nInteractive menu lets you switch between different monitoring modes.")
        return
    
    # Find worker instance
    instances = get_worker_instance()
    
    if not instances:
        print("❌ No running worker instances found")
        print("Run: uv run python launcher.py")
        return
    
    instance = instances[0]
    print(f"🖥️ Monitoring worker: {instance['id']} ({instance['state']}) - {instance['ip']}")
    
    if instance['state'] != 'running':
        print(f"❌ Instance is {instance['state']}, not running")
        return
    
    try:
        monitor_logs_unified(instance['ip'])
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")

if __name__ == '__main__':
    main()