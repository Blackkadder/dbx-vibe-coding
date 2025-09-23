"""
Configuration management for the I hate terraform app
"""

import os
import streamlit as st
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 🎯 Static Model API Endpoint - Update this to your actual endpoint URL
DEFAULT_MODEL_API_ENDPOINT = "https://your-terraform-model-api.herokuapp.com/generate-terraform"

@dataclass
class AppConfig:
    """Application configuration"""
    # Required field
    workspace_url: str
    
    # Optional fields with defaults (including static model endpoint)
    model_api_endpoint: str = DEFAULT_MODEL_API_ENDPOINT
    workspace_profile: Optional[str] = None
    workspace_token: Optional[str] = None
    model_api_key: Optional[str] = None
    debug_mode: bool = False


class ConfigManager:
    """Manages application configuration from multiple sources"""
    
    @staticmethod
    def load_from_env() -> AppConfig:
        """Load configuration from environment variables"""
        workspace_url = os.getenv('DATABRICKS_WORKSPACE_URL', '')
        print(workspace_url)
        
        if not workspace_url:
            raise ValueError("DATABRICKS_WORKSPACE_URL environment variable is required")
        
        # ✨ Model API endpoint is now automatic - no env var needed!
        return AppConfig(
            workspace_url=workspace_url,
            workspace_profile=os.getenv('DATABRICKS_PROFILE'),
            workspace_token=os.getenv('DATABRICKS_TOKEN'),
            model_api_key=os.getenv('MODEL_API_KEY'),
            debug_mode=os.getenv('DEBUG_MODE', 'false').lower() == 'true'
            # model_api_endpoint automatically uses DEFAULT_MODEL_API_ENDPOINT
        )
    
   
    
    @staticmethod
    def create_user_input_config() -> Optional[AppConfig]:
        """Create configuration from user input in Streamlit sidebar"""
        st.sidebar.header("🔧 Configuration")
        
        workspace_url = st.sidebar.text_input(
            "Databricks Workspace URL",
            placeholder="https://your-workspace.databricks.com",
            help="Your Databricks workspace URL"
        )
        
        # ✨ Show the static endpoint instead of asking for input
        st.sidebar.info(f"🎯 **Model API Endpoint:**\n`{DEFAULT_MODEL_API_ENDPOINT}`")
        st.sidebar.caption("The model endpoint is configured in the app code.")
        
        # Advanced options
        with st.sidebar.expander("⚙️ Advanced Options"):
            workspace_profile = st.text_input(
                "Databricks Profile",
                placeholder="DEFAULT",
                help="Databricks CLI profile name for SSO authentication"
            )
            
            workspace_token = st.text_input(
                "Databricks Token (optional)",
                type="password",
                help="Personal access token (if not using profile/SSO)"
            )
            
            model_api_key = st.text_input(
                "Model API Key (optional)",
                type="password",
                help="API key for model endpoint authentication"
            )
        
        # ✨ Only workspace URL is required now!
        if workspace_url:
            return AppConfig(
                workspace_url=workspace_url,
                workspace_profile=workspace_profile or None,
                workspace_token=workspace_token or None,
                model_api_key=model_api_key or None,
                debug_mode=False
                # model_api_endpoint automatically uses DEFAULT_MODEL_API_ENDPOINT
            )
        
        return None
    
    @staticmethod
    def validate_config(config: AppConfig) -> Dict[str, str]:
        """Validate configuration and return any errors"""
        errors = {}
        
        if not config.workspace_url:
            errors['workspace_url'] = "Databricks workspace URL is required"
        elif not config.workspace_url.startswith(('http://', 'https://')):
            errors['workspace_url'] = "Workspace URL must start with http:// or https://"
        
        # ✨ Model endpoint validation is simplified since it's always present with default
        if not config.model_api_endpoint.startswith(('http://', 'https://')):
            errors['model_api_endpoint'] = "Model API endpoint must start with http:// or https://"
        
        # Check authentication
        if not config.workspace_profile and not config.workspace_token:
            errors['auth'] = "Either Databricks profile or token is required for authentication"
        
        return errors


def get_app_config() -> Optional[AppConfig]:
    """Get application configuration from the best available source"""
    
    # Try environment variables first
    
    config = ConfigManager.load_from_env()
    if config.workspace_url:
        return config
   
    
    # Fall back to Streamlit-based configuration
    # try:
    #     config = ConfigManager.load_from_streamlit()
    #     if config.workspace_url:
    #         return config
    # except Exception:
    #     pass
    
    # Return None if no configuration is available
    return None
