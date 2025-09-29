"""
Middleware layer for "I hate terraform" app.

This middleware handles:
1. Authentication to Databricks workspace using SSO credentials
2. Retrieval of job details from Databricks workspace
3. Communication with external model API for Terraform generation
4. Response formatting and error handling

The middleware does NOT perform Terraform conversion - that is delegated 
to the external model API endpoint.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import requests
import uuid


@dataclass
class WorkspaceConfig:
    """Configuration for Databricks workspace connection"""
    workspace_url: str
    token: Optional[str] = None
    profile: Optional[str] = None


@dataclass
class ModelAPIConfig:
    """Configuration for model API endpoint"""
    endpoint_url: str
    api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class DatabricksJobRetriever:
    """Handles Databricks job retrieval using REST API calls"""
    
    def __init__(self, workspace_config: WorkspaceConfig):
        self.workspace_config = workspace_config
        self.logger = logging.getLogger(__name__)
        
        # Set up authentication headers
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        # Configure authentication
        if self.workspace_config.token:
            self.headers['Authorization'] = f'Bearer {self.workspace_config.token}'
        elif self.workspace_config.profile:
            # For profile-based auth, try to get token from environment or CLI config
            token = self._get_token_from_profile()
            if token:
                self.headers['Authorization'] = f'Bearer {token}'
            else:
                raise ValueError(f"Could not retrieve token for profile: {self.workspace_config.profile}")
        else:
            # Try to get token from environment variables
            token = os.getenv('DATABRICKS_TOKEN')
            if token:
                self.headers['Authorization'] = f'Bearer {token}'
            else:
                raise ValueError("No authentication method provided. Need either token or valid profile.")
    
    def _get_token_from_profile(self) -> Optional[str]:
        """Get token from Databricks profile or environment"""
        
        # Try general environment variable
        env_token = os.getenv('DATABRICKS_TOKEN')
        print('ENV TOKEN', env_token)
        if env_token:
            return env_token
            
        # TODO: Could try to read from ~/.databrickscfg file here
        return None
    
    def get_job_details(self, job_id: int) -> Dict[str, Any]:
        """Retrieve detailed job configuration from Databricks REST API"""
        try:
            # Construct the API URL
            api_url = f"{self.workspace_config.workspace_url.rstrip('/')}/api/2.0/jobs/get"
            
            # Make the REST API call
            self.logger.info(f"Calling Databricks Jobs API: GET {api_url}")
            response = requests.get(
                api_url,
                headers=self.headers,
                params={'job_id': job_id},
                timeout=30
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the JSON response
            job_data = response.json()
            
            # Return the raw job data from the API
            self.logger.info(f"Successfully retrieved job details for job_id: {job_id}")
            self.logger.info(f"Job name: {job_data.get('settings', {}).get('name', 'Unknown')}")
            
            return job_data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"Job {job_id} not found in workspace")
            elif e.response.status_code == 403:
                raise Exception(f"Access denied. Check your authentication credentials.")
            else:
                raise Exception(f"HTTP {e.response.status_code}: {e.response.text}")
                
        except requests.exceptions.ConnectionError:
            raise Exception(f"Could not connect to Databricks workspace: {self.workspace_config.workspace_url}")
            
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. The Databricks API may be slow to respond.")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
            
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from Databricks API")
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve job {job_id}: {str(e)}")
            raise Exception(f"Unable to retrieve job details: {str(e)}")


class ModelAPIClient:
    """
    Client for communicating with external model API endpoint.
    
    This class handles HTTP communication with the deployed model that
    performs Databricks job to Terraform conversion. It does NOT perform
    any conversion logic itself - it only formats requests and processes responses.
    """
    
    def __init__(self, config: ModelAPIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Set up HTTP headers
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'I-Hate-Terraform-Middleware/1.0'
        }
        
        # Add authentication if provided
        if config.api_key:
            self.headers['Authorization'] = f'Bearer {config.api_key}'
        
        # Add any additional headers
        if config.headers:
            self.headers.update(config.headers)
    
    def request_terraform_generation(self, job_details: Dict[str, Any], workspace_url: str) -> str:
        """
        Send job details to external model API for Terraform generation.
        
        Args:
            job_details: Complete job configuration from Databricks
            workspace_url: URL of the Databricks workspace
            
        Returns:
            str: Generated Terraform code from the model
            
        Raises:
            Exception: If the API request fails or returns invalid response
        """
        request_id = self._generate_request_id()
        
        # Prepare payload for model API
        payload = {
            "job_details": job_details,
            "workspace_url": workspace_url,
            "output_format": "terraform",
            "request_id": request_id,
            "metadata": {
                "job_id": job_details.get("job_id"),
                "job_name": job_details.get("name", "unknown"),
                "timestamp": self._get_timestamp()
            }
        }
        
        self.logger.info(f"Sending Terraform generation request to model API: {self.config.endpoint_url}")
        self.logger.debug(f"Request ID: {request_id}, Job ID: {job_details.get('job_id')}")
        
        try:
            # Make POST request to model API
            response = requests.post(
                self.config.endpoint_url,
                json=payload,
                headers=self.headers,
                timeout=120  # Allow 2 minutes for model processing
            )
            
            # Check HTTP status
            response.raise_for_status()
            
            # Parse JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                self.logger.error("Model API returned invalid JSON response")
                raise Exception(f"Invalid JSON response from model API: {str(e)}")
            
            # Extract Terraform code from response
            if 'terraform_code' in result:
                terraform_code = result['terraform_code']
                if not isinstance(terraform_code, str) or not terraform_code.strip():
                    raise Exception("Model API returned empty or invalid Terraform code")
                
                self.logger.info(f"Successfully received Terraform code ({len(terraform_code)} characters)")
                return terraform_code
            else:
                self.logger.error("Model API response missing 'terraform_code' field")
                available_fields = list(result.keys()) if isinstance(result, dict) else "unknown"
                raise Exception(f"Model API response missing 'terraform_code' field. Available fields: {available_fields}")
                
        except requests.exceptions.Timeout:
            self.logger.error("Request to model API timed out")
            raise Exception("Model API request timed out - the model may be processing a complex job")
        
        except requests.exceptions.ConnectionError:
            self.logger.error("Failed to connect to model API")
            raise Exception("Unable to connect to model API - check endpoint URL and network connectivity")
        
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "unknown"
            self.logger.error(f"Model API returned HTTP error: {status_code}")
            
            # Try to extract error message from response
            error_detail = "Unknown error"
            if e.response:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('error', error_data.get('message', str(e)))
                except:
                    error_detail = e.response.text[:200] if e.response.text else str(e)
            
            raise Exception(f"Model API error ({status_code}): {error_detail}")
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request to model API failed: {str(e)}")
            raise Exception(f"Model API request failed: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Unexpected error during model API communication: {str(e)}")
            raise Exception(f"Failed to communicate with model API: {str(e)}")
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracking"""
        return str(uuid.uuid4())
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for request metadata"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'


class TerraformMiddleware:
    """
    Main middleware coordinating Databricks job retrieval and external model API communication.
    
    This middleware acts as an orchestration layer that:
    1. Authenticates to Databricks workspace
    2. Retrieves detailed job configurations 
    3. Sends job data to external model API for Terraform generation
    4. Returns the generated Terraform code
    
    The middleware does NOT perform any Terraform conversion logic - all conversion
    is handled by the external model API endpoint.
    """
    
    def __init__(self, workspace_config: WorkspaceConfig, model_api_config: ModelAPIConfig):
        self.job_retriever = DatabricksJobRetriever(workspace_config)
        self.model_client = ModelAPIClient(model_api_config)
        self.workspace_config = workspace_config
        self.logger = logging.getLogger(__name__)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        # Logging configuration is the responsibility of the application.
        
        
        
        
        
        self.logger.info("Terraform middleware initialized")
        self.logger.debug(f"Workspace: {workspace_config.workspace_url}")
        self.logger.debug(f"Model API: {model_api_config.endpoint_url}")

    #  self.logger.info("Step 1: Retrieving job details from Databricks workspace")
    #         job_details = self.job_retriever.get_job_details(job_id)
    
    def process_job_to_terraform(self, job_id: int) -> Dict[str, Any]:
        """
        Complete pipeline: authenticate, retrieve job details, and request Terraform generation.
        
        Args:
            job_id: Databricks job ID to convert
            
        Returns:
            Dict containing success status, job details, and generated Terraform code
            
        Flow:
            1. Authenticate to Databricks workspace using SSO/token
            2. Retrieve complete job configuration from Databricks API
            3. Send job details to external model API via POST request
            4. Return Terraform code generated by the model
        """
        request_start_time = self._get_timestamp()
        
        try:
            self.logger.info(f"Starting job-to-Terraform pipeline for job_id: {job_id}")
            
            # Step 1: Authenticate and retrieve job details from Databricks
            self.logger.info("Step 1: Retrieving job details from Databricks workspace")
            job_details = self.job_retriever.get_job_details(job_id)
            
            job_name = job_details.get('settings', {}).get('name', 'Unknown')
            creator = job_details.get('creator_user_name', 'Unknown')
            self.logger.info(f"Retrieved job: '{job_name}' (Created by: {creator})")
            
            # Step 2: Send job details to external model API for Terraform generation  
            self.logger.info("Step 2: Requesting Terraform generation from model API")
            terraform_code = self.model_client.request_terraform_generation(
                job_details=job_details, 
                workspace_url=self.workspace_config.workspace_url
            )
            
            # Step 3: Format and return successful response
            result = {
                "success": True,
                "job_id": job_id,
                "job_details": job_details,
                "terraform_code": terraform_code,
                "workspace_url": self.workspace_config.workspace_url,
                "metadata": {
                    "request_start_time": request_start_time,
                    "request_end_time": self._get_timestamp(),
                    "terraform_length": len(terraform_code),
                    "job_name": job_details.get('settings', {}).get('name', 'Unknown')
                }
            }
            
            self.logger.info(f"Successfully completed pipeline for job_id: {job_id} "
                           f"(Generated {len(terraform_code)} characters of Terraform)")
            return result
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Pipeline failed for job {job_id}: {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "job_id": job_id,
                "metadata": {
                    "request_start_time": request_start_time,
                    "request_end_time": self._get_timestamp(),
                    "error_type": type(e).__name__
                }
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of the middleware components.
        
        Returns:
            Dict with health status of Databricks connection and model API
        """
        health_status = {
            "middleware": "healthy",
            "databricks_auth": "unknown",
            "model_api": "unknown",
            "timestamp": self._get_timestamp()
        }
        
        # Test Databricks authentication by making a simple API call
        try:
            # Try to list jobs (lightweight API call to test auth)
            api_url = f"{self.job_retriever.workspace_config.workspace_url.rstrip('/')}/api/2.0/jobs/list"
            response = requests.get(
                api_url,
                headers=self.job_retriever.headers,
                params={'limit': 1},
                timeout=10
            )
            response.raise_for_status()
            health_status["databricks_auth"] = "healthy"
            health_status["databricks_workspace"] = self.job_retriever.workspace_config.workspace_url
        except Exception as e:
            health_status["databricks_auth"] = "unhealthy"
            health_status["databricks_error"] = str(e)
        
        # Note: We don't test model API here as it would require actual job data
        # and we don't want to make unnecessary API calls during health checks
        
        return health_status
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'


def create_middleware_from_config(
    workspace_url: str,
    model_api_endpoint: str,
    workspace_profile: Optional[str] = None,
    workspace_token: Optional[str] = None,
    model_api_key: Optional[str] = None
) -> TerraformMiddleware:
    """Factory function to create middleware from configuration parameters"""
    
    workspace_config = WorkspaceConfig(
        workspace_url=workspace_url,
        profile=workspace_profile,
        token=workspace_token
    )
    
    model_api_config = ModelAPIConfig(
        endpoint_url=model_api_endpoint,
        api_key=model_api_key
    )
    
    return TerraformMiddleware(workspace_config, model_api_config)


def create_middleware_from_env() -> TerraformMiddleware:
    """Create middleware using environment variables"""
    
    workspace_url = os.getenv('DATABRICKS_HOST')
    if not workspace_url:
        raise ValueError("DATABRICKS_WORKSPACE_URL environment variable is required")
    
    model_api_endpoint = os.getenv('MODEL_API_ENDPOINT')
    if not model_api_endpoint:
        raise ValueError("MODEL_API_ENDPOINT environment variable is required")
    
    return create_middleware_from_config(
        workspace_url=workspace_url,
        model_api_endpoint=model_api_endpoint,
        workspace_profile=os.getenv('DATABRICKS_PROFILE'),
        workspace_token=os.getenv('DATABRICKS_TOKEN'),
        model_api_key=os.getenv('MODEL_API_KEY')
    )
