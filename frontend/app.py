import streamlit as st
import pandas as pd
import json
import time
import re
from typing import Dict, Any
import uuid

# Configure the page
st.set_page_config(
    page_title="I Hate Terraform",
    page_icon="😤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Databricks-inspired UI theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    :root{
        --dbx-bg: #0b0f14;
        --dbx-bg-elev: #121923;
        --dbx-panel: #1a2230;
        --dbx-border: rgba(255,255,255,0.08);
        --dbx-text: #e5e7eb;
        --dbx-muted: #9aa4b2;
        --dbx-accent: #ff3621;
        --dbx-accent-2: #ff6a4f;
        /* Tabs */
        --dbx-tab-line: #2a2f38;               /* darker grey underline */
        --dbx-tab-line-active: #3a414d;        /* slightly brighter dark grey */
        --dbx-tab-text: #96a0ad;               /* dark grey tab text */
        --dbx-tab-text-active: #cfd5de;        /* selected tab text */
    }

    .main { background: var(--dbx-bg); min-height: 100vh; }
    .stApp { background: transparent; }
    html, body, [class^="css"] { font-family: 'Inter', system-ui, sans-serif; }
    /* Remove top whitespace */
    .block-container{ padding-top: 1rem !important; }
    body { margin: 0 !important; }

    .app-header{
        position: sticky; top: 0; z-index: 5;
        background: #12161d;
        border-bottom: 1px solid var(--dbx-border);
        padding: 0.9rem 1.25rem;
        margin: 0 -1rem 1.25rem -1rem;
    }
    .brand{ display:flex; align-items:center; gap:.65rem; color:var(--dbx-text); font-weight:800; letter-spacing:.3px; }
    .brand-dot{ width:10px; height:10px; border-radius:2px; background: var(--dbx-accent); box-shadow:0 0 16px rgba(255,54,33,.55); }

    .page-wrap{ max-width: 1120px; margin: 0 auto; padding: 0 1rem; overflow: visible; }
    .breadcrumb{ display:none; }
    .title-xl{ color: var(--dbx-text); font-weight: 800; font-size: 1.9rem; letter-spacing:.2px; margin:.2rem 0 0.6rem 0; }
    .title-standalone{
        color: #12161d;
        display: block;
        width: 100%;
        text-align: center;
        font-weight: 800;
        font-size: 2.25rem;
        line-height: 1.2;
        margin: 1.25rem 0 .5rem 0;
        letter-spacing: 0;
        overflow: visible;
    }
    .section-title{ color: var(--dbx-muted); text-align:left; font-weight:800; margin: .25rem 0 .5rem 0; }

    .controls-card{ display:none; }
    .left-card{ max-width: 360px; }
    .pill-header{ display: none; }
    .chip-row{ display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.25rem; }
    .chip{ background:#0f1622; color:var(--dbx-text); border:1px solid var(--dbx-border); border-radius:8px; padding:.4rem .55rem; font-size:.9rem; cursor:pointer; }
    .chip:hover{ border-color:var(--dbx-accent); }

    label[data-baseweb="typography"]{
        color: var(--dbx-muted) !important;
        font-weight: 600;
        letter-spacing: .2px;
        margin-bottom: .25rem;
    }
    .stTextInput > div > div > input{
        background: #0f1622;
        border: 1px solid var(--dbx-border);
        border-radius: 10px;
        color: var(--dbx-text);
        padding: .65rem .8rem;
    }
    .stTextInput > div > div > input:focus{ outline: none; border-color: var(--dbx-accent); box-shadow: 0 0 0 2px rgba(255,54,33,.25); }
    .stTextInput > div > div > input::placeholder{ color: rgba(229,231,235,.55); }

    .stButton > button{
        background: linear-gradient(180deg, var(--dbx-accent), var(--dbx-accent-2));
        color:#fff; border: 0; border-radius: 10px; font-weight: 800; letter-spacing:.3px;
        height: 42px; box-shadow: 0 6px 22px rgba(255,54,33,.28);
    }
    .stButton > button:disabled{ filter: grayscale(.5); opacity:.6; box-shadow:none; }
    .stButton > button:hover{ transform: translateY(-1px); }

    .output-container{
        background: #121923;
        border: 1px solid var(--dbx-border);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0 2rem 0;
        box-shadow: 0 12px 28px rgba(0,0,0,.35);
    }
    .terraform-output{
        background: #0d1117; color: #d1e7dd; font-family: 'JetBrains Mono', monospace;
        border-left: 4px solid var(--dbx-accent); border-radius: 8px; padding: 1rem; white-space: pre-wrap; overflow-x: auto;
    }

    .loading-spinner{ display:flex; align-items:center; justify-content:center; height:100px; }
    .spinner{ width: 40px; height: 40px; border: 4px solid rgba(255,255,255,.2); border-top:4px solid var(--dbx-accent); border-radius: 50%; animation: spin 1s linear infinite; }
    @keyframes spin{ 0%{transform:rotate(0)} 100%{transform:rotate(360deg)} }

    .stTabs [data-baseweb="tab-list"]{
        gap: 1rem;
        border-bottom: 1px solid var(--dbx-tab-line);
    }
    .stTabs [data-baseweb="tab"]{
        background: transparent;
        border: none;
        color: var(--dbx-tab-text);
    }
    .stTabs [aria-selected="true"]{
        color: var(--dbx-tab-text-active);
        border-bottom: 3px solid var(--dbx-tab-line-active);
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
if 'open_tf_tab_next' not in st.session_state:
    st.session_state.open_tf_tab_next = False

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


def is_valid_identifier(text: str) -> bool:
    """Return True if text is a non-empty ID of letters, numbers, dashes or underscores."""
    if not isinstance(text, str):
        return False
    if not text.strip():
        return False
    return re.fullmatch(r"[A-Za-z0-9_-]+", text.strip()) is not None

def main():
    # Standalone centered title only
    st.markdown('<div class="page-wrap"><h1 class="title-standalone">Terraform Sucks!</h1>', unsafe_allow_html=True)

    left, right = st.columns([1, 2])

    with left:
        st.markdown('<div class="section-title">Inputs</div>', unsafe_allow_html=True)
        workspace = st.text_input(
            "Workspace ID",
            placeholder="Enter workspace ID (numbers only)...",
            key="workspace_id_input",
            label_visibility="visible",
        )
        job_id = st.text_input(
            "Job ID",
            placeholder="Enter job ID...",
            key="job_id_input",
            label_visibility="visible",
        )

        def is_valid_workspace(url: str) -> bool:
            if not isinstance(url, str) or not url.strip():
                return False
            # Numeric workspace IDs only
            return bool(re.fullmatch(r"\d+", url.strip()))

        def is_valid_job_id(jid: str) -> bool:
            return bool(re.fullmatch(r"\d+", str(jid).strip()))

        form_valid = is_valid_workspace(st.session_state.get("workspace_id_input", "")) and is_valid_job_id(st.session_state.get("job_id_input", ""))

        fetch_clicked = st.button(
            "Fetch Job",
            key="fetch_button",
            use_container_width=True,
            disabled=not form_valid,
        )
        if fetch_clicked:
            st.session_state.terraform_output = ""
            st.session_state.is_loading = True
            st.session_state.job_completed = False
            # on next render after fetch completes, focus Terraform Variables tab
            st.session_state.open_tf_tab_next = True
            st.rerun()

        # no wrapper closing; widgets are standalone in Streamlit

    with right:
        with st.container():
            if st.session_state.is_loading:
                st.markdown(
                    """
<div class=\"output-container\">\n  <div class=\"loading-spinner\"><div class=\"spinner\"></div></div>\n  <div style=\"text-align:center; color:#34d399; margin-top: .5rem;\">Fetching job info...</div>\n</div>
                    """,
                    unsafe_allow_html=True,
                )

                # Generate terraform variables (simulate)
                terraform_output = generate_terraform_variables(
                    st.session_state.job_id_input
                )
                st.session_state.terraform_output = terraform_output
                st.session_state.is_loading = False
                st.session_state.job_completed = True
                st.rerun()

            elif st.session_state.job_completed and st.session_state.terraform_output:
                tab_labels = ["Overview", "Terraform Variables", "Raw JSON"]
                if st.session_state.get("open_tf_tab_next", False):
                    tab_labels = ["Terraform Variables", "Overview", "Raw JSON"]
                    st.session_state.open_tf_tab_next = False
                tabs = st.tabs(tab_labels)
                tab_map = {label: tab for label, tab in zip(tab_labels, tabs)}

                with tab_map["Overview"]:
                    st.markdown(
                        f"""
<div class=\"output-container\">\n  <div class=\"terraform-output\" style=\"border-left-color:#374151;\">\n$ databricks jobs get --job-id {st.session_state.job_id_input}\nFetching job info...\n\n✔ Job retrieved successfully\n  </div>\n</div>
                        """,
                        unsafe_allow_html=True,
                    )
                with tab_map["Terraform Variables"]:
                    st.markdown(
                        f"""
<div class=\"output-container\">\n  <div style=\"display:flex; justify-content:flex-end;\">\n    <button id=\"copyBtn\" class=\"chip\" onclick=\"navigator.clipboard.writeText(document.getElementById('tfBlock').innerText)\">Copy</button>\n  </div>\n  <div id=\"tfBlock\" class=\"terraform-output\">{st.session_state.terraform_output}</div>\n</div>
                        """,
                        unsafe_allow_html=True,
                    )
                    dl_cols = st.columns([1,1,6])
                    with dl_cols[0]:
                        st.download_button(
                            label="Download .tf",
                            data=st.session_state.terraform_output,
                            file_name=f"terraform_job_{st.session_state.job_id_input}.tf",
                            mime="text/plain",
                            key="download_tf",
                            use_container_width=True,
                        )
                    with dl_cols[1]:
                        json_payload = {
                            "job_id": st.session_state.job_id_input,
                            "generated_on": time.strftime('%Y-%m-%d %H:%M:%S'),
                            "workspace": st.session_state.get("workspace_id_input", ""),
                        }
                        st.download_button(
                            label="Download JSON",
                            data=json.dumps(json_payload, indent=2),
                            file_name=f"job_{st.session_state.job_id_input}.json",
                            mime="application/json",
                            key="download_json",
                            use_container_width=True,
                        )
                with tab_map["Raw JSON"]:
                    st.json({
                        "job_id": st.session_state.job_id_input,
                        "workspace": st.session_state.get("workspace_id_input", ""),
                        "status": "retrieved",
                    })
            else:
                st.markdown('<div class="section-title">Outputs</div>', unsafe_allow_html=True)
                st.markdown(
                    """
<div class=\"output-container\"><div style=\"color:#9aa4b2;\">Enter a workspace and job id, then click Fetch Job</div></div>
                    """,
                    unsafe_allow_html=True,
                )

    # Footer & close page-wrap
    st.markdown("""
    <div class="page-wrap" style="text-align:center; margin-top: 1.5rem; padding: 1.5rem 0; color: #9aa4b2; font-size: .9rem; border-top: 1px solid var(--dbx-border);">
        Built with Streamlit • Databricks-inspired UI
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()