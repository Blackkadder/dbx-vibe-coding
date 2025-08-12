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
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Job


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
    """Handles Databricks job retrieval using SSO credentials"""
    
    def __init__(self, workspace_config: WorkspaceConfig):
        self.workspace_config = workspace_config
        self._client: Optional[WorkspaceClient] = None
        self.logger = logging.getLogger(__name__)
    
    def _get_client(self) -> WorkspaceClient:
        """Get authenticated Databricks client"""
        if self._client is None:
            try:
                # Try to use profile-based authentication first (SSO)
                if self.workspace_config.profile:
                    self._client = WorkspaceClient(
                        host=self.workspace_config.workspace_url,
                        profile=self.workspace_config.profile
                    )
                # Fall back to token-based authentication
                elif self.workspace_config.token:
                    self._client = WorkspaceClient(
                        host=self.workspace_config.workspace_url,
                        token=self.workspace_config.token
                    )
                else:
                    # Use environment variables or default profile
                    self._client = WorkspaceClient(
                        host=self.workspace_config.workspace_url
                    )
                    
                # Test the connection
                self._client.current_user.me()
                self.logger.info("Successfully authenticated to Databricks workspace")
                
            except Exception as e:
                self.logger.error(f"Failed to authenticate to Databricks: {str(e)}")
                raise
        
        return self._client
    
    def get_job_details(self, job_id: int) -> Dict[str, Any]:
        """Retrieve detailed job configuration from Databricks"""
        try:
            client = self._get_client()
            job = client.jobs.get(job_id=job_id)
            
            # Extract relevant job details
            job_details = {
                "job_id": job.job_id,
                "name": job.settings.name if job.settings else "Unknown",
                "created_time": job.created_time,
                "creator_user_name": job.creator_user_name,
                "settings": self._serialize_job_settings(job.settings) if job.settings else {},
                "cluster_spec": self._extract_cluster_spec(job.settings) if job.settings else {}
            }
            
            self.logger.info(f"Successfully retrieved job details for job_id: {job_id}")
            return job_details
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve job {job_id}: {str(e)}")
            raise Exception(f"Unable to retrieve job details: {str(e)}")
    
    def _serialize_job_settings(self, settings) -> Dict[str, Any]:
        """Convert job settings to serializable format"""
        try:
            # Convert to dictionary, handling complex objects
            settings_dict = {}
            
            # Basic properties
            if hasattr(settings, 'name'):
                settings_dict['name'] = settings.name
            if hasattr(settings, 'description'):
                settings_dict['description'] = settings.description
            if hasattr(settings, 'tags'):
                settings_dict['tags'] = settings.tags
            if hasattr(settings, 'max_concurrent_runs'):
                settings_dict['max_concurrent_runs'] = settings.max_concurrent_runs
            if hasattr(settings, 'timeout_seconds'):
                settings_dict['timeout_seconds'] = settings.timeout_seconds
                
            # Task configuration
            if hasattr(settings, 'tasks') and settings.tasks:
                settings_dict['tasks'] = []
                for task in settings.tasks:
                    task_dict = {
                        'task_key': getattr(task, 'task_key', ''),
                        'description': getattr(task, 'description', ''),
                        'depends_on': getattr(task, 'depends_on', []),
                    }
                    
                    # Add task type specific details
                    if hasattr(task, 'notebook_task') and task.notebook_task:
                        task_dict['type'] = 'notebook'
                        task_dict['notebook_path'] = task.notebook_task.notebook_path
                        task_dict['base_parameters'] = getattr(task.notebook_task, 'base_parameters', {})
                    elif hasattr(task, 'spark_python_task') and task.spark_python_task:
                        task_dict['type'] = 'spark_python'
                        task_dict['python_file'] = task.spark_python_task.python_file
                        task_dict['parameters'] = getattr(task.spark_python_task, 'parameters', [])
                    elif hasattr(task, 'python_wheel_task') and task.python_wheel_task:
                        task_dict['type'] = 'python_wheel'
                        task_dict['package_name'] = task.python_wheel_task.package_name
                        task_dict['entry_point'] = task.python_wheel_task.entry_point
                    
                    settings_dict['tasks'].append(task_dict)
            
            # Schedule information
            if hasattr(settings, 'schedule') and settings.schedule:
                settings_dict['schedule'] = {
                    'quartz_cron_expression': getattr(settings.schedule, 'quartz_cron_expression', ''),
                    'timezone_id': getattr(settings.schedule, 'timezone_id', 'UTC')
                }
            
            return settings_dict
            
        except Exception as e:
            self.logger.warning(f"Failed to serialize job settings: {str(e)}")
            return {"error": "Failed to serialize job settings"}
    
    def _extract_cluster_spec(self, settings) -> Dict[str, Any]:
        """Extract cluster specification from job settings"""
        cluster_spec = {}
        
        try:
            # Check for job cluster
            if hasattr(settings, 'job_clusters') and settings.job_clusters:
                job_cluster = settings.job_clusters[0]  # Take first cluster
                if hasattr(job_cluster, 'new_cluster'):
                    cluster = job_cluster.new_cluster
                    cluster_spec = {
                        'cluster_name': getattr(job_cluster, 'job_cluster_key', ''),
                        'node_type_id': getattr(cluster, 'node_type_id', ''),
                        'driver_node_type_id': getattr(cluster, 'driver_node_type_id', ''),
                        'num_workers': getattr(cluster, 'num_workers', 0),
                        'spark_version': getattr(cluster, 'spark_version', ''),
                        'spark_conf': getattr(cluster, 'spark_conf', {}),
                        'aws_attributes': getattr(cluster, 'aws_attributes', {}),
                        'custom_tags': getattr(cluster, 'custom_tags', {})
                    }
            
            # Check for existing cluster ID
            elif hasattr(settings, 'existing_cluster_id'):
                cluster_spec = {
                    'existing_cluster_id': settings.existing_cluster_id,
                    'type': 'existing'
                }
            
            return cluster_spec
            
        except Exception as e:
            self.logger.warning(f"Failed to extract cluster spec: {str(e)}")
            return {"error": "Failed to extract cluster specification"}


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
        
        self.logger.info("Terraform middleware initialized")
        self.logger.debug(f"Workspace: {workspace_config.workspace_url}")
        self.logger.debug(f"Model API: {model_api_config.endpoint_url}")
    
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
            
            self.logger.info(f"Retrieved job: '{job_details.get('name', 'Unknown')}' "
                           f"(Created by: {job_details.get('creator_user_name', 'Unknown')})")
            
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
                    "job_name": job_details.get('name', 'Unknown')
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
        
        # Test Databricks authentication
        try:
            client = self.job_retriever._get_client()
            user = client.current_user.me()
            health_status["databricks_auth"] = "healthy"
            health_status["databricks_user"] = user.user_name
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
    
    workspace_url = os.getenv('DATABRICKS_WORKSPACE_URL')
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
