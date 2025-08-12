import streamlit as st
import pandas as pd
import json
import time
from typing import Dict, Any
import uuid
import sys
import os

# Add the parent directory to the Python path to import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.middleware import create_middleware_from_config
from backend.config import ConfigManager, AppConfig, get_app_config

# Configure the page
st.set_page_config(
    page_title="I Hate Terraform",
    page_icon="😤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for a cool dark theme
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    .stApp {
        background: transparent;
    }
    
    .title-container {
        text-align: center;
        padding: 2rem 0;
        margin-bottom: 2rem;
    }
    
    .main-title {
        font-size: 4rem;
        font-weight: bold;
        color: white;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        margin-bottom: 0;
        font-family: 'Arial Black', sans-serif;
    }
    
    .input-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin: 2rem auto;
        max-width: 600px;
    }
    
    .output-container {
        background: rgba(0, 0, 0, 0.8);
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        font-family: 'Courier New', monospace;
        color: #00ff00;
        min-height: 400px;
    }
    
    .go-button {
        background: linear-gradient(45deg, #ff6b6b, #ee5a24);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 1rem 3rem;
        font-size: 1.5rem;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(238, 90, 36, 0.4);
    }
    
    .go-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(238, 90, 36, 0.6);
    }
    
    .download-button {
        background: linear-gradient(45deg, #4ecdc4, #44a08d);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.8rem 2rem;
        font-size: 1.2rem;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(68, 160, 141, 0.4);
        margin-top: 1rem;
    }
    
    .download-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(68, 160, 141, 0.6);
    }
    
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.9);
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 15px;
        color: #333;
        font-size: 1.2rem;
        padding: 1rem;
        font-weight: bold;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #ff6b6b;
        box-shadow: 0 0 0 2px rgba(255, 107, 107, 0.2);
    }
    
    .terraform-output {
        background: #1e1e1e;
        color: #d4edda;
        font-family: 'Courier New', monospace;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #00ff00;
        white-space: pre-wrap;
        overflow-x: auto;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    
    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100px;
    }
    
    .spinner {
        width: 40px;
        height: 40px;
        border: 4px solid rgba(255, 255, 255, 0.3);
        border-top: 4px solid #ff6b6b;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .success-message {
        background: rgba(40, 167, 69, 0.2);
        border: 1px solid #28a745;
        color: #28a745;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        font-weight: bold;
    }
    
    .error-message {
        background: rgba(220, 53, 69, 0.2);
        border: 1px solid #dc3545;
        color: #dc3545;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'terraform_output' not in st.session_state:
    st.session_state.terraform_output = ""
if 'is_loading' not in st.session_state:
    st.session_state.is_loading = False
if 'job_completed' not in st.session_state:
    st.session_state.job_completed = False
if 'error_message' not in st.session_state:
    st.session_state.error_message = ""
if 'app_config' not in st.session_state:
    st.session_state.app_config = None


def get_or_create_config() -> AppConfig:
    """Get or create app configuration"""
    if st.session_state.app_config is None:
        # Try to load from environment/secrets
        config = get_app_config()
        if config:
            st.session_state.app_config = config
        else:
            # Use user input configuration
            config = ConfigManager.create_user_input_config()
            if config:
                # Validate the configuration
                errors = ConfigManager.validate_config(config)
                if not errors:
                    st.session_state.app_config = config
                else:
                    # Show validation errors
                    st.sidebar.error("Configuration Errors:")
                    for field, error in errors.items():
                        st.sidebar.error(f"• {error}")
                    return None
            else:
                return None
    
    return st.session_state.app_config


def generate_terraform_from_databricks(job_id: str, config: AppConfig) -> Dict[str, Any]:
    """Generate terraform using the real middleware pipeline"""
    try:
        # Convert job_id to integer
        job_id_int = int(job_id)
        
        # Create middleware
        middleware = create_middleware_from_config(
            workspace_url=config.workspace_url,
            model_api_endpoint=config.model_api_endpoint,
            workspace_profile=config.workspace_profile,
            workspace_token=config.workspace_token,
            model_api_key=config.model_api_key
        )
        
        # Process job to terraform
        result = middleware.process_job_to_terraform(job_id_int)
        
        return result
        
    except ValueError as e:
        return {
            "success": False,
            "error": f"Invalid job ID: {job_id}. Job ID must be a number.",
            "job_id": job_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "job_id": job_id
        }


def generate_terraform_variables(job_id: str, config: AppConfig) -> str:
    """Generate terraform using real Databricks job data and external AI model"""
    
    # Add a processing indicator with real-time status updates
    status_placeholder = st.empty()
    status_placeholder.markdown("""
        <div style="text-align: center; color: #00ff00; margin: 1rem 0;">
            🔐 Authenticating to Databricks workspace...<br/>
            <small>Establishing connection with SSO credentials</small>
        </div>
    """, unsafe_allow_html=True)
    
    time.sleep(0.5)  # Brief pause for UX
    
    status_placeholder.markdown("""
        <div style="text-align: center; color: #00ff00; margin: 1rem 0;">
            📋 Retrieving job configuration from workspace...<br/>
            <small>Fetching job details and cluster specifications</small>
        </div>
    """, unsafe_allow_html=True)
    
    # Call the middleware - it will handle auth and job retrieval
    result = generate_terraform_from_databricks(job_id, config)
    
    if result["success"]:
        status_placeholder.markdown("""
            <div style="text-align: center; color: #00ff00; margin: 1rem 0;">
                🤖 Sending job data to AI model for conversion...<br/>
                <small>External model processing Databricks job configuration</small>
            </div>
        """, unsafe_allow_html=True)
        
        time.sleep(1)  # Brief pause for UX
        status_placeholder.empty()
        
        return result["terraform_code"]
    else:
        status_placeholder.empty()
        # Store error for display
        st.session_state.error_message = result["error"]
        raise Exception(result["error"])


def show_configuration_help():
    """Show configuration help in sidebar"""
    with st.sidebar.expander("❓ Configuration Help"):
        st.markdown("""
        **To use this app, you need:**
        
        1. **Databricks Workspace URL**: Your workspace URL (e.g., `https://your-workspace.databricks.com`)
        
        2. **Authentication**: Either:
           - Databricks CLI profile (recommended for SSO)
           - Personal access token
        
        3. **Model API Endpoint**: URL of your deployed model that converts Databricks jobs to Terraform
        
        **Setting up authentication:**
        - Install Databricks CLI: `pip install databricks-cli`
        - Configure: `databricks configure --token`
        - Or use environment variables
        """)


def show_demo_mode_warning():
    """Show warning about demo mode"""
    st.warning("""
    ⚠️ **Demo Mode**: No valid configuration found. 
    
    Please configure your Databricks workspace and model API endpoint in the sidebar to use real job data.
    Currently showing mock data for demonstration purposes.
    """)


def generate_mock_terraform(job_id: str) -> str:
    """Generate mock terraform for demo purposes"""
    time.sleep(2)  # Simulate processing
    
    return f"""# Mock Terraform Configuration for Job: {job_id}
# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}
# 
# ⚠️  This is DEMO data - configure the app to use real Databricks jobs

variable "job_id" {{
  description = "The job identifier"
  type        = string
  default     = "{job_id}"
}}

variable "environment" {{
  description = "Environment name"
  type        = string
  default     = "production"
}}

# Mock Resource Configuration
resource "databricks_job" "this" {{
  name = "mock-job-{job_id}"
  
  task {{
    task_key = "main"
    
    notebook_task {{
      notebook_path = "/Users/demo@example.com/mock-notebook"
    }}
    
    new_cluster {{
      num_workers   = 2
      spark_version = "11.3.x-scala2.12"
      node_type_id  = "i3.xlarge"
    }}
  }}
  
  tags = {{
    environment = var.environment
    job_id      = var.job_id
  }}
}}

output "job_url" {{
  description = "Mock job URL"
  value       = "https://demo.databricks.com/#job/${{databricks_job.this.id}}"
}}"""

def main():
    # Show configuration help
    show_configuration_help()
    
    # Get or create configuration
    config = get_or_create_config()
    is_demo_mode = config is None
    
    # Title
    st.markdown("""
    <div class="title-container">
        <h1 class="main-title">I hate terraform 😤</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Show demo mode warning if applicable
    if is_demo_mode:
        show_demo_mode_warning()
    else:
        # Show current configuration status
        st.success(f"✅ Connected to workspace: `{config.workspace_url}`")
    
    # Input container
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        job_id = st.text_input(
            "",
            placeholder="Enter Databricks job ID...",
            key="job_id_input",
            label_visibility="collapsed",
            help="Enter the numeric ID of your Databricks job"
        )
    
    with col2:
        if st.button("GO", key="go_button", use_container_width=True):
            if job_id.strip():
                st.session_state.is_loading = True
                st.session_state.job_completed = False
                st.session_state.error_message = ""
                st.rerun()
            else:
                st.error("Please enter a job ID!")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Processing and output area
    if st.session_state.is_loading:
        st.markdown("""
        <div class="output-container">
            <div class="loading-spinner">
                <div class="spinner"></div>
            </div>
            <div style="text-align: center; color: #00ff00; margin-top: 1rem;">
                🔄 Generating terraform code for job: <strong>{}</strong><br/>
                💭 Thinking about how much I hate terraform...<br/>
                ⚡ Processing infrastructure as code...
            </div>
        </div>
        """.format(st.session_state.job_id_input), unsafe_allow_html=True)
        
        try:
            # Generate terraform using appropriate method
            if is_demo_mode:
                terraform_output = generate_mock_terraform(st.session_state.job_id_input)
            else:
                terraform_output = generate_terraform_variables(st.session_state.job_id_input, config)
            
            st.session_state.terraform_output = terraform_output
            st.session_state.is_loading = False
            st.session_state.job_completed = True
            
        except Exception as e:
            st.session_state.is_loading = False
            st.session_state.job_completed = False
            st.session_state.terraform_output = ""
            if not st.session_state.error_message:
                st.session_state.error_message = str(e)
        
        st.rerun()
    
    elif st.session_state.error_message:
        # Show error message
        st.markdown(f"""
        <div class="error-message">
            ❌ Error: {st.session_state.error_message}
        </div>
        """, unsafe_allow_html=True)
        
        # Clear error on next interaction
        if st.button("🔄 Try Again", use_container_width=True):
            st.session_state.error_message = ""
            st.session_state.terraform_output = ""
            st.session_state.job_completed = False
            st.rerun()
    
    elif st.session_state.job_completed and st.session_state.terraform_output:
        # Success message
        success_msg = "✅ Terraform code generated successfully! (Even though we hate it...)"
        if is_demo_mode:
            success_msg = "✅ Demo Terraform generated! Configure the app for real job data."
        
        st.markdown(f"""
        <div class="success-message">
            {success_msg}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="output-container">', unsafe_allow_html=True)
        
        # Display terraform output
        st.markdown(f"""
        <div class="terraform-output">
{st.session_state.terraform_output}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Download button and actions
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🆕 New Job", use_container_width=True):
                # Reset for new job
                st.session_state.terraform_output = ""
                st.session_state.job_completed = False
                st.session_state.error_message = ""
                st.rerun()
        
        with col2:
            st.download_button(
                label="📥 Download .tf",
                data=st.session_state.terraform_output,
                file_name=f"job_{st.session_state.job_id_input}.tf",
                mime="text/plain",
                key="download_button",
                use_container_width=True
            )
        
        with col3:
            # Copy to clipboard button (using JavaScript)
            copy_button = """
            <script>
            function copyToClipboard() {
                const text = document.querySelector('.terraform-output').textContent;
                navigator.clipboard.writeText(text).then(function() {
                    alert('Terraform code copied to clipboard!');
                });
            }
            </script>
            <button onclick="copyToClipboard()" style="
                background: linear-gradient(45deg, #6c5ce7, #a29bfe);
                color: white; border: none; border-radius: 25px;
                padding: 0.8rem 2rem; font-size: 1.2rem; font-weight: bold;
                cursor: pointer; width: 100%; margin-top: 0.5rem;
            ">📋 Copy</button>
            """
            st.markdown(copy_button, unsafe_allow_html=True)
    
    else:
        # Default state
        instruction_text = """
            💻 Enter a Databricks job ID and click GO to generate terraform code<br/><br/>
            🤬 (Warning: May cause severe frustration with Infrastructure as Code)
        """
        
        if is_demo_mode:
            instruction_text += "<br/><br/>📝 Currently in demo mode - configure the app to use real job data"
        
        st.markdown(f"""
        <div class="output-container">
            <div style="text-align: center; color: #666; font-size: 1.2rem; margin-top: 6rem;">
                {instruction_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; padding: 2rem;">
        <p style="color: rgba(255,255,255,0.7); font-size: 0.9rem;">
            Made with ❤️ and 😤 for people who understand the terraform struggle
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()