#!/usr/bin/env python3
"""
Example usage of the I hate terraform middleware

This script demonstrates how to use the middleware programmatically
to retrieve Databricks jobs and send them to an external model API
for Terraform conversion.

Note: The middleware does NOT perform Terraform conversion itself - 
it only handles authentication, job retrieval, and API communication
with your deployed model endpoint.
"""

import os
import sys
import json
from typing import Optional

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.middleware import create_middleware_from_config, create_middleware_from_env
from backend.config import AppConfig, ConfigManager


def example_with_config():
    """Example using explicit configuration"""
    print("🔧 Creating middleware with explicit configuration...")
    
    # Create configuration - replace with your values
    config = AppConfig(
        workspace_url="https://your-workspace.cloud.databricks.com",
        workspace_profile="DEFAULT",  # or None if using token
        workspace_token=None,  # or your token if not using profile
        model_api_endpoint="https://your-model-api.com/generate-terraform",
        model_api_key="your-api-key-here",  # optional
        debug_mode=True
    )
    
    # Validate configuration
    errors = ConfigManager.validate_config(config)
    if errors:
        print("❌ Configuration errors:")
        for field, error in errors.items():
            print(f"  • {error}")
        return False
    
    # Create middleware
    middleware = create_middleware_from_config(
        workspace_url=config.workspace_url,
        model_api_endpoint=config.model_api_endpoint,
        workspace_profile=config.workspace_profile,
        workspace_token=config.workspace_token,
        model_api_key=config.model_api_key
    )
    
    # Example job ID - replace with your actual job ID
    job_id = 510377430276633
    
    print(f"🚀 Processing job {job_id}...")
    result = middleware.process_job_to_terraform(job_id)
    
    if result["success"]:
        print("✅ Success! Generated Terraform code:")
        print("-" * 50)
        print(result["terraform_code"])
        print("-" * 50)
        
        # Optionally save to file
        filename = f"job_{job_id}.tf"
        with open(filename, 'w') as f:
            f.write(result["terraform_code"])
        print(f"💾 Saved to {filename}")
        
    else:
        print(f"❌ Error: {result['error']}")
    
    return result["success"]


def example_with_env():
    """Example using environment variables"""
    print("🌍 Creating middleware from environment variables...")
    
    try:
        middleware = create_middleware_from_env()
        
        # Example job ID
        job_id = 456
        
        print(f"🚀 Processing job {job_id}...")
        result = middleware.process_job_to_terraform(job_id)
        
        if result["success"]:
            print("✅ Success!")
            print(f"📋 Job details: {json.dumps(result['job_details'], indent=2)}")
            print(f"📄 Terraform code length: {len(result['terraform_code'])} characters")
        else:
            print(f"❌ Error: {result['error']}")
        
        return result["success"]
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Make sure to set the required environment variables:")
        print("   - DATABRICKS_WORKSPACE_URL")
        print("   - MODEL_API_ENDPOINT") 
        print("   - DATABRICKS_PROFILE or DATABRICKS_TOKEN")
        return False


def interactive_example():
    """Interactive example that prompts for configuration"""
    print("🎮 Interactive example - enter your configuration:")
    
    workspace_url = input("Databricks workspace URL: ").strip()
    if not workspace_url:
        print("❌ Workspace URL is required")
        return False
    
    model_api_endpoint = input("Model API endpoint: ").strip()
    if not model_api_endpoint:
        print("❌ Model API endpoint is required")
        return False
    
    print("\nAuthentication options:")
    print("1. Databricks CLI profile (recommended for SSO)")
    print("2. Personal access token")
    
    auth_choice = input("Choose authentication method (1/2): ").strip()
    
    workspace_profile = None
    workspace_token = None
    
    if auth_choice == "1":
        workspace_profile = input("Profile name (DEFAULT): ").strip() or "DEFAULT"
    elif auth_choice == "2":
        workspace_token = input("Access token: ").strip()
        if not workspace_token:
            print("❌ Token is required")
            return False
    else:
        print("❌ Invalid choice")
        return False
    
    model_api_key = input("Model API key (optional): ").strip() or None
    job_id_str = input("Job ID to convert: ").strip()
    
    try:
        job_id = int(job_id_str)
    except ValueError:
        print("❌ Job ID must be a number")
        return False
    
    # Create configuration
    config = AppConfig(
        workspace_url=workspace_url,
        workspace_profile=workspace_profile,
        workspace_token=workspace_token,
        model_api_endpoint=model_api_endpoint,
        model_api_key=model_api_key,
        debug_mode=True
    )
    
    # Validate
    errors = ConfigManager.validate_config(config)
    if errors:
        print("❌ Configuration errors:")
        for field, error in errors.items():
            print(f"  • {error}")
        return False
    
    # Create middleware and process
    middleware = create_middleware_from_config(
        workspace_url=config.workspace_url,
        model_api_endpoint=config.model_api_endpoint,
        workspace_profile=config.workspace_profile,
        workspace_token=config.workspace_token,
        model_api_key=config.model_api_key
    )
    
    print(f"\n🚀 Processing job {job_id}...")
    result = middleware.process_job_to_terraform(job_id)
    
    if result["success"]:
        print("✅ Success!")
        
        # Show job details
        job_details = result["job_details"]
        print(f"\n📋 Job: {job_details.get('name', 'Unknown')} (ID: {job_details['job_id']})")
        print(f"👤 Creator: {job_details.get('creator_user_name', 'Unknown')}")
        
        # Show terraform code
        terraform_code = result["terraform_code"]
        print(f"\n📄 Generated Terraform ({len(terraform_code)} characters):")
        print("-" * 50)
        print(terraform_code[:500] + "..." if len(terraform_code) > 500 else terraform_code)
        print("-" * 50)
        
        # Offer to save
        save_choice = input("\n💾 Save to file? (y/N): ").strip().lower()
        if save_choice in ['y', 'yes']:
            filename = f"job_{job_id}.tf"
            with open(filename, 'w') as f:
                f.write(terraform_code)
            print(f"✅ Saved to {filename}")
        
    else:
        print(f"❌ Error: {result['error']}")
    
    return result["success"]


def main():
    """Main function to run examples"""
    print("😤 I hate terraform - Example Usage\n")
    
    print("Available examples:")
    print("1. Explicit configuration")
    print("2. Environment variables")
    print("3. Interactive configuration")
    print("4. Exit")
    
    while True:
        choice = input("\nSelect an example (1-4): ").strip()
        
        if choice == "1":
            example_with_config()
        elif choice == "2":
            example_with_env()
        elif choice == "3":
            interactive_example()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice, please select 1-4")


if __name__ == "__main__":
    main()
