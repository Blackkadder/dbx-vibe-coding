import json
import time
import uuid
from typing import Any, Dict

import pandas as pd
import streamlit as st

# Configure the page
st.set_page_config(
    page_title="I Hate Terraform",
    page_icon="😤",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for a cool dark theme
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "terraform_output" not in st.session_state:
    st.session_state.terraform_output = ""
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False
if "job_completed" not in st.session_state:
    st.session_state.job_completed = False


def generate_terraform_variables(job_id: str) -> str:
    """Generate mock terraform variables based on job ID"""
    # Simulate some processing time
    time.sleep(2)

    terraform_vars = f"""# Terraform Variables for Job: {job_id}
# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

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

variable "region" {{
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}}

variable "instance_type" {{
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}}

variable "tags" {{
  description = "Resource tags"
  type        = map(string)
  default = {{
    "JobId"       = "{job_id}"
    "Environment" = "production"
    "ManagedBy"   = "terraform"
    "Project"     = "ihateterraform"
  }}
}}

# Resource Configuration
resource "aws_instance" "job_instance" {{
  ami           = "ami-0c55b159cbfafe1d0"
  instance_type = var.instance_type
  
  tags = merge(var.tags, {{
    Name = "job-${{var.job_id}}-instance"
  }})
}}

resource "aws_s3_bucket" "job_storage" {{
  bucket = "job-${{var.job_id}}-storage-${{random_id.bucket_suffix.hex}}"
  
  tags = var.tags
}}

resource "random_id" "bucket_suffix" {{
  byte_length = 4
}}

# Outputs
output "instance_id" {{
  description = "ID of the EC2 instance"
  value       = aws_instance.job_instance.id
}}

output "bucket_name" {{
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.job_storage.id
}}

output "job_endpoint" {{
  description = "Job endpoint URL"
  value       = "https://api.example.com/jobs/${{var.job_id}}"
}}"""

    return terraform_vars


def main():
    # Title
    st.markdown(
        """
    <div class="title-container">
        <h1 class="main-title">I hate terraform 😤</h1>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Input container
    st.markdown('<div class="input-container">', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])

    with col1:
        job_id = st.text_input(
            "",
            placeholder="Enter job ID...",
            key="job_id_input",
            label_visibility="collapsed",
        )

    with col2:
        if st.button("GO", key="go_button", use_container_width=True):
            if job_id.strip():
                st.session_state.is_loading = True
                st.session_state.job_completed = False
                st.rerun()
            else:
                st.error("Please enter a job ID!")

    st.markdown("</div>", unsafe_allow_html=True)

    # Processing and output area
    if st.session_state.is_loading:
        st.markdown(
            """
        <div class="output-container">
            <div class="loading-spinner">
                <div class="spinner"></div>
            </div>
            <div style="text-align: center; color: #00ff00; margin-top: 1rem;">
                🔄 Generating terraform variables for job: <strong>{}</strong><br/>
                💭 Thinking about how much I hate terraform...<br/>
                ⚡ Processing infrastructure as code...
            </div>
        </div>
        """.format(
                st.session_state.job_id_input
            ),
            unsafe_allow_html=True,
        )

        # Generate terraform variables
        terraform_output = generate_terraform_variables(st.session_state.job_id_input)
        st.session_state.terraform_output = terraform_output
        st.session_state.is_loading = False
        st.session_state.job_completed = True
        st.rerun()

    elif st.session_state.job_completed and st.session_state.terraform_output:
        st.markdown(
            """
        <div class="success-message">
            ✅ Terraform variables generated successfully! (Even though we hate it...)
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="output-container">', unsafe_allow_html=True)

        # Display terraform output
        st.markdown(
            f"""
        <div class="terraform-output">
{st.session_state.terraform_output}
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

        # Download button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.download_button(
                label="📥 Download terraform.tf",
                data=st.session_state.terraform_output,
                file_name=f"terraform_job_{st.session_state.job_id_input}.tf",
                mime="text/plain",
                key="download_button",
                use_container_width=True,
            )

    elif not st.session_state.terraform_output:
        # Default state
        st.markdown(
            """
        <div class="output-container">
            <div style="text-align: center; color: #666; font-size: 1.2rem; margin-top: 8rem;">
                💻 Enter a job ID and click GO to generate terraform variables<br/><br/>
                🤬 (Warning: May cause severe frustration with Infrastructure as Code)
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Footer
    st.markdown(
        """
    <div style="text-align: center; margin-top: 3rem; padding: 2rem;">
        <p style="color: rgba(255,255,255,0.7); font-size: 0.9rem;">
            Made with ❤️ and 😤 for people who understand the terraform struggle
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
