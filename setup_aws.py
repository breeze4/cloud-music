#!/usr/bin/env python3
"""
AWS Setup Script for MusicGen Batch System
Handles Phase 1 tasks: uv setup, AWS CLI installation, authentication, and account readiness
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path
import shutil


def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")


def print_step(step_num, text):
    """Print a formatted step"""
    print(f"\n[Step {step_num}] {text}")
    print("-" * 40)


def run_command(command, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode


def check_uv_installed():
    """Check if uv is installed"""
    print_step(1, "Checking uv Installation")
    
    stdout, stderr, returncode = run_command("uv --version", check=False)
    
    if returncode == 0:
        print(f"✅ uv is installed: {stdout}")
        return True
    else:
        print("❌ uv is not installed")
        return False


def install_uv():
    """Install uv package manager"""
    print_step(2, "Installing uv")
    
    system = platform.system().lower()
    
    print("Installing uv package manager...")
    
    if system in ["linux", "darwin"]:  # Linux or macOS
        cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True, check=False)
        
        if result.returncode == 0:
            # Add to PATH for current session
            uv_bin = Path.home() / ".cargo" / "bin"
            if uv_bin.exists():
                current_path = os.environ.get("PATH", "")
                if str(uv_bin) not in current_path:
                    os.environ["PATH"] = f"{uv_bin}:{current_path}"
            
            # Test installation
            stdout, stderr, returncode = run_command("uv --version", check=False)
            if returncode == 0:
                print(f"✅ uv successfully installed: {stdout}")
                return True
            else:
                print("❌ uv installation verification failed")
                print("You may need to restart your shell or run: source ~/.bashrc")
                return False
        else:
            print("❌ uv installation failed")
            return False
    
    elif system == "windows":
        print("For Windows, please install uv using one of these methods:")
        print("1. PowerShell: irm https://astral.sh/uv/install.ps1 | iex")
        print("2. Scoop: scoop install uv")
        print("3. Chocolatey: choco install uv")
        print("Then restart this script.")
        return False
    
    else:
        print(f"❌ Unsupported operating system: {system}")
        return False


def setup_uv_project():
    """Initialize uv project and install dependencies"""
    print_step(3, "Setting up uv Project")
    
    # Check if we're already in a uv project
    if Path("pyproject.toml").exists():
        print("✅ pyproject.toml already exists")
    
    # Use uv sync for simpler dependency management
    print("Installing project dependencies with uv...")
    stdout, stderr, returncode = run_command("uv sync", check=False)
    
    if returncode == 0:
        print("✅ Dependencies installed successfully")
        print("✅ Virtual environment created at .venv")
        return True
    else:
        print(f"❌ Failed to install dependencies")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        
        # Fallback: try manual installation
        print("Trying fallback method...")
        fallback_commands = [
            "uv venv",
            "uv pip install boto3 python-dotenv"
        ]
        
        for cmd in fallback_commands:
            print(f"Running fallback: {cmd}")
            stdout, stderr, returncode = run_command(cmd, check=False)
            if returncode != 0:
                print(f"❌ Fallback failed: {cmd}")
                print(f"Error: {stderr}")
                return False
        
        print("✅ Fallback installation successful")
        return True


def check_aws_cli_installed():
    """Check if AWS CLI is installed"""
    print_step(4, "Checking AWS CLI Installation")
    
    stdout, stderr, returncode = run_command("aws --version", check=False)
    
    if returncode == 0:
        print(f"✅ AWS CLI is installed: {stdout}")
        return True
    else:
        print("❌ AWS CLI is not installed")
        return False


def install_aws_cli():
    """Install AWS CLI based on the operating system"""
    print_step(5, "Installing AWS CLI")
    
    system = platform.system().lower()
    
    if system == "linux":
        # Check if we're on WSL or native Linux
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
            if 'microsoft' in version_info or 'wsl' in version_info:
                print("Detected WSL environment")
        except:
            pass
        
        print("Installing AWS CLI for Linux...")
        commands = [
            "curl 'https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip' -o 'awscliv2.zip'",
            "unzip -q awscliv2.zip",
            "sudo ./aws/install --update",
            "rm -rf awscliv2.zip aws/"
        ]
        
    elif system == "darwin":  # macOS
        print("Installing AWS CLI for macOS...")
        if shutil.which("brew"):
            commands = ["brew install awscli"]
        else:
            commands = [
                "curl 'https://awscli.amazonaws.com/AWSCLIV2.pkg' -o 'AWSCLIV2.pkg'",
                "sudo installer -pkg AWSCLIV2.pkg -target /",
                "rm AWSCLIV2.pkg"
            ]
    
    elif system == "windows":
        print("For Windows, please download and install AWS CLI from:")
        print("https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")
        print("Then restart this script.")
        return False
    
    else:
        print(f"❌ Unsupported operating system: {system}")
        return False
    
    for cmd in commands:
        print(f"Running: {cmd}")
        stdout, stderr, returncode = run_command(cmd)
        if returncode != 0:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {stderr}")
            return False
    
    # Verify installation
    stdout, stderr, returncode = run_command("aws --version", check=False)
    if returncode == 0:
        print(f"✅ AWS CLI successfully installed: {stdout}")
        return True
    else:
        print("❌ AWS CLI installation verification failed")
        return False


def setup_env_file():
    """Guide user through setting up .env file"""
    print_step(6, "Setting up Environment Configuration")
    
    env_path = Path(".env")
    template_path = Path(".env.template")
    
    if env_path.exists():
        response = input(".env file already exists. Overwrite? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Using existing .env file")
            return True
    
    if not template_path.exists():
        print("❌ .env.template file not found!")
        return False
    
    print("Creating .env file from template...")
    
    # Read template
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Guide user through filling out values
    print("\nPlease provide the following information:")
    print("(You can update these values later by editing the .env file)")
    
    replacements = {}
    
    # AWS Account ID
    print("\n1. AWS Account ID:")
    print("   Find this in AWS Console -> Account settings")
    account_id = input("   Enter your 12-digit AWS Account ID: ").strip()
    replacements["123456789012"] = account_id
    
    # AWS Region
    print("\n2. AWS Region:")
    print("   Choose the region where you want to run your instances")
    print("   Popular choices: us-east-1, us-west-2, eu-west-1")
    region = input("   Enter AWS region (default: us-east-1): ").strip() or "us-east-1"
    replacements["us-east-1"] = region
    
    # S3 Bucket Name
    print("\n3. S3 Bucket Name:")
    print("   This must be globally unique")
    default_bucket = f"musicgen-batch-output-{account_id[-6:]}"
    bucket_name = input(f"   Enter S3 bucket name (default: {default_bucket}): ").strip() or default_bucket
    replacements["musicgen-batch-output-your-unique-suffix"] = bucket_name
    
    # Key Pair Name and Path
    print("\n4. EC2 Key Pair:")
    print("   Using standard key pair name: musicgen-batch-keypair")
    print("   Private key will be expected at: ./keys/musicgen-batch-keypair.pem")
    print("   You'll need to:")
    print("   - Create key pair 'musicgen-batch-keypair' in AWS Console -> EC2 -> Key Pairs")
    print("   - Download the .pem file to ./keys/musicgen-batch-keypair.pem")
    key_pair = "musicgen-batch-keypair"
    replacements["your-ec2-keypair-name"] = key_pair
    
    # Create keys directory
    keys_dir = Path("keys")
    if not keys_dir.exists():
        print("   Creating ./keys/ directory...")
        keys_dir.mkdir(mode=0o700)  # Restricted permissions for key storage
    
    # Apply replacements
    content = template_content
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Write .env file
    with open(env_path, 'w') as f:
        f.write(content)
    
    print(f"✅ .env file created successfully!")
    print(f"   You can edit {env_path} to update any values")
    
    return True


def configure_aws_credentials():
    """Guide user through AWS credential configuration"""
    print_step(7, "Configuring AWS Credentials")
    
    print("You need AWS credentials to authenticate with AWS services.")
    print("There are several ways to do this:")
    print()
    print("Option 1: AWS CLI configure (recommended for development)")
    print("Option 2: IAM Role (for EC2 instances)")
    print("Option 3: Environment variables")
    print("Option 4: AWS SSO")
    print()
    
    choice = input("Which option would you like to use? (1-4, default: 1): ").strip() or "1"
    
    if choice == "1":
        return configure_aws_cli_credentials()
    elif choice == "2":
        print("IAM Role setup requires running on an EC2 instance with attached role.")
        print("This is typically used in production. For local development, use Option 1.")
        return False
    elif choice == "3":
        return configure_env_credentials()
    elif choice == "4":
        return configure_aws_sso()
    else:
        print("Invalid option selected")
        return False


def configure_aws_cli_credentials():
    """Configure AWS CLI credentials"""
    print("\nConfiguring AWS CLI credentials...")
    print()
    print("You'll need:")
    print("1. AWS Access Key ID")
    print("2. AWS Secret Access Key") 
    print()
    print("To get these:")
    print("1. Go to AWS Console -> IAM -> Users")
    print("2. Select your user or create a new one")
    print("3. Go to 'Security credentials' tab")
    print("4. Click 'Create access key'")
    print("5. Choose 'Command Line Interface (CLI)'")
    print("6. Copy the Access Key ID and Secret Access Key")
    print()
    
    input("Press Enter when you have your credentials ready...")
    
    # Load region from .env
    region = "us-east-1"
    if os.path.exists(".env"):
        with open(".env", 'r') as f:
            for line in f:
                if line.startswith("AWS_REGION="):
                    region = line.split("=", 1)[1].strip()
                    break
    
    print(f"\nRunning: aws configure")
    print(f"Use region: {region}")
    print(f"Use output format: json")
    
    result = subprocess.run(["aws", "configure"], check=False)
    
    if result.returncode == 0:
        # Test credentials
        stdout, stderr, returncode = run_command("aws sts get-caller-identity")
        if returncode == 0:
            identity = json.loads(stdout)
            print(f"✅ AWS credentials configured successfully!")
            print(f"   Account: {identity.get('Account')}")
            print(f"   User: {identity.get('Arn')}")
            return True
        else:
            print("❌ AWS credentials test failed")
            print(f"Error: {stderr}")
            return False
    else:
        print("❌ AWS configure failed")
        return False


def configure_env_credentials():
    """Configure credentials via environment variables"""
    print("\nTo use environment variables, add these to your shell profile:")
    print("export AWS_ACCESS_KEY_ID=your_access_key_here")
    print("export AWS_SECRET_ACCESS_KEY=your_secret_key_here")
    
    access_key = input("Enter AWS Access Key ID: ").strip()
    secret_key = input("Enter AWS Secret Access Key: ").strip()
    
    # Test credentials
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = access_key
    env["AWS_SECRET_ACCESS_KEY"] = secret_key
    
    result = subprocess.run(
        ["aws", "sts", "get-caller-identity"],
        env=env,
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode == 0:
        print("✅ Credentials are valid")
        print("Add these to your shell profile to make them persistent:")
        print(f"export AWS_ACCESS_KEY_ID={access_key}")
        print(f"export AWS_SECRET_ACCESS_KEY={secret_key}")
        return True
    else:
        print("❌ Credential test failed")
        return False


def configure_aws_sso():
    """Configure AWS SSO"""
    print("\nAWS SSO setup:")
    print("1. Your organization must have AWS SSO enabled")
    print("2. You need the SSO start URL and region")
    
    sso_url = input("Enter SSO start URL: ").strip()
    sso_region = input("Enter SSO region: ").strip()
    
    cmd = f"aws configure sso --sso-start-url {sso_url} --sso-region {sso_region}"
    result = subprocess.run(cmd.split(), check=False)
    
    return result.returncode == 0


def main():
    """Main setup function"""
    print_header("MusicGen Batch System - AWS Setup")
    print("This script will help you set up uv, AWS CLI and authentication for the MusicGen batch system.")
    print()
    
    # Check if uv is installed
    if not check_uv_installed():
        print("uv package manager is required. Would you like to install it?")
        response = input("Install uv? (Y/n): ").strip().lower()
        if response in ['', 'y', 'yes']:
            if not install_uv():
                print("❌ Failed to install uv. Please install manually and run this script again.")
                return False
        else:
            print("uv is required for dependency management. Please install it manually and run this script again.")
            return False
    
    # Set up uv project
    if not setup_uv_project():
        print("❌ Failed to set up uv project")
        return False
    
    # Check if AWS CLI is installed
    if not check_aws_cli_installed():
        print("AWS CLI is required. Would you like to install it?")
        response = input("Install AWS CLI? (Y/n): ").strip().lower()
        if response in ['', 'y', 'yes']:
            if not install_aws_cli():
                print("❌ Failed to install AWS CLI. Please install manually and run this script again.")
                return False
        else:
            print("AWS CLI is required. Please install it manually and run this script again.")
            return False
    
    # Set up .env file
    if not setup_env_file():
        print("❌ Failed to set up .env file")
        return False
    
    # Configure AWS credentials
    if not configure_aws_credentials():
        print("❌ Failed to configure AWS credentials")
        return False
    
    print_header("Setup Complete!")
    print("✅ uv package manager is installed and configured")
    print("✅ Project dependencies are installed")
    print("✅ AWS CLI is installed and configured")
    print("✅ Environment file (.env) is set up")
    print("✅ AWS credentials are configured")
    print()
    print("Next steps:")
    print("1. Run: uv run python check_aws_readiness.py")
    print("2. Create your EC2 key pair in AWS Console if you haven't already")
    print("3. Review and update .env file as needed")
    print()
    print("Development commands:")
    print("• uv run python setup_aws.py        # Re-run this setup")
    print("• uv run python check_aws_readiness.py  # Check AWS account readiness")
    print("• uv add <package>                  # Add new dependencies")
    print("• uv sync                           # Sync dependencies")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)