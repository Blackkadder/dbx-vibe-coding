# I hate terraform 😤

Convert Databricks jobs to Terraform code using AI - because writing infrastructure as code is frustrating enough without doing it manually!

## Features

- 🔐 **SSO Authentication**: Connect to your Databricks workspace using SSO credentials
- 📋 **Job Retrieval**: Automatically fetch job details from your workspace 
- 🤖 **AI-Powered Generation**: Use a deployed model to convert jobs to Terraform
- 💻 **Beautiful UI**: Streamlit-based interface with a modern dark theme
- 📥 **Export Options**: Download generated Terraform files or copy to clipboard

## Architecture

The app consists of:
- **Frontend**: Streamlit app (`frontend/app.py`) with user interface
- **Middleware**: Backend layer (`backend/middleware.py`) that handles:
  - Databricks SSO authentication and job retrieval
  - HTTP communication with external model API endpoint
  - Request/response formatting and error handling
- **External Model API**: Your deployed model that performs the actual job-to-Terraform conversion

**Important**: The middleware does NOT perform Terraform conversion - it only retrieves job data from Databricks and forwards it to your model API endpoint.

## Setup

### 1. Install Dependencies

```bash
# Using pip
pip install -r frontend/requirements.txt

# Or using uv (if available)
uv sync
```

### 2. Configure Authentication

#### Option A: Environment Variables (Recommended)
Copy `.env.example` to `.env` and fill in your details:

```bash
cp .env.example .env
# Edit .env with your configuration
```

#### Option B: Databricks CLI Profile
Install and configure the Databricks CLI:

```bash
pip install databricks-cli
databricks configure --token
```

#### Option C: Streamlit Interface
Configure directly in the app's sidebar when running.

### 3. Set Up Model API

The app requires a deployed model endpoint that accepts Databricks job configurations and returns generated Terraform code.

**API Contract:**

**Request (POST):**
```json
{
  "job_details": {
    "job_id": 123,
    "name": "My Job",
    "creator_user_name": "user@company.com",
    "settings": { /* Complete Databricks job configuration */ },
    "cluster_spec": { /* Cluster specifications */ }
  },
  "workspace_url": "https://workspace.databricks.com",
  "output_format": "terraform",
  "request_id": "uuid-string",
  "metadata": {
    "job_id": 123,
    "job_name": "My Job", 
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

**Response (JSON):**
```json
{
  "terraform_code": "# Generated Terraform HCL code\nresource \"databricks_job\" \"this\" {\n  ...\n}"
}
```

**Authentication**: Optional API key via `Authorization: Bearer <token>` header

### 4. Run the App

```bash
cd frontend
streamlit run app.py
```

## Configuration Options

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABRICKS_WORKSPACE_URL` | Your Databricks workspace URL | Yes |
| `DATABRICKS_PROFILE` | CLI profile name for SSO auth | Yes* |
| `DATABRICKS_TOKEN` | Personal access token | Yes* |
| `MODEL_API_ENDPOINT` | Model API endpoint URL | Yes |
| `MODEL_API_KEY` | API key for model endpoint | No |
| `DEBUG_MODE` | Enable debug logging | No |

*Either `DATABRICKS_PROFILE` or `DATABRICKS_TOKEN` is required.

## Usage

1. **Configure**: Set up your Databricks workspace and model API endpoint details
2. **Enter Job ID**: Input the numeric ID of your Databricks job  
3. **Process**: Click GO to:
   - Authenticate to your Databricks workspace
   - Retrieve complete job configuration 
   - Send job data to your model API for Terraform generation
   - Display the generated Terraform code
4. **Export**: Download the `.tf` file or copy to clipboard

The middleware acts as a bridge between your Databricks workspace and your deployed model - it doesn't generate Terraform itself.

## Demo Mode

If no configuration is provided, the app runs in demo mode with mock data to showcase the interface.

## Middleware API

The middleware can also be used programmatically:

```python
from backend.middleware import create_middleware_from_config
from backend.config import AppConfig

# Create configuration
config = AppConfig(
    workspace_url="https://your-workspace.databricks.com",
    workspace_profile="DEFAULT",
    model_api_endpoint="https://your-model-api.com/generate"
)

# Create middleware
middleware = create_middleware_from_config(
    workspace_url=config.workspace_url,
    model_api_endpoint=config.model_api_endpoint,
    workspace_profile=config.workspace_profile,
    model_api_key=config.model_api_key
)

# Generate Terraform
result = middleware.process_job_to_terraform(job_id=123)

if result["success"]:
    terraform_code = result["terraform_code"]
    print(terraform_code)
else:
    print(f"Error: {result['error']}")
```

## Error Handling

The app includes comprehensive error handling for:
- Authentication failures
- Invalid job IDs
- Network connectivity issues
- Model API errors
- Malformed responses

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the middleware and frontend
5. Submit a pull request

## License

Made with ❤️ and 😤 for people who understand the terraform struggle.
