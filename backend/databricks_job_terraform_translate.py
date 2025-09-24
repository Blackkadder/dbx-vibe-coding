"""
Databricks Job to Terraform Translation Service

A self-contained MLflow Python model that converts Databricks job JSON specifications 
into Terraform HCL scripts. This module combines both the conversion logic and MLflow 
wrapper in a single file for easy deployment to Databricks model serving endpoints.

Features:
- Converts Databricks job JSON to Terraform HCL
- Supports all major task types (notebook, Spark, SQL, pipeline, etc.)
- MLflow-compatible model for serving
- Error handling with informative error scripts
- No external file dependencies

Usage:
    # Quick conversion
    terraform_script = quick_convert(job_json_string)
    
    # MLflow model serving
    model = DatabricksJobTerraformTranslateModel()
    result = model.predict(context, input_data)
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

# MLflow dependencies (external)
import mlflow
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TerraformResource:
    """Represents a Terraform resource block."""
    resource_type: str
    resource_name: str
    attributes: Dict[str, Any]


class DatabricksJobToTerraformAgent:
    """
    Core conversion agent that transforms Databricks job JSON specifications 
    into Terraform HCL scripts.
    
    Supported Features:
    - All Databricks task types (notebook, Spark JAR/Python, SQL, pipeline, etc.)
    - Job clusters and existing cluster references
    - Scheduling (cron expressions, triggers, continuous)
    - Email and webhook notifications
    - Git source integration
    - Job parameters and libraries
    - Run-as configurations
    - Queue settings and dependencies
    """
    
    def __init__(self):
        self.terraform_version = ">=1.0"
        self.databricks_provider_version = ">=1.28.0"
    
    def convert_json_to_terraform(self, job_json: str) -> str:
        """
        Convert a JSON job specification to Terraform HCL script.
        
        Args:
            job_json: JSON string containing Databricks job specification
            
        Returns:
            String containing the generated Terraform script
            
        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        try:
            job_spec = json.loads(job_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        
        # Validate required fields
        self._validate_job_spec(job_spec)
        
        # Generate Terraform configuration
        terraform_config = self._generate_terraform_config(job_spec)
        
        return terraform_config
    
    def _validate_job_spec(self, job_spec: Dict[str, Any]) -> None:
        """Validate the job specification contains required fields."""
        required_fields = ["name"]
        
        for field in required_fields:
            if field not in job_spec:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate tasks if present
        if "tasks" in job_spec:
            for i, task in enumerate(job_spec["tasks"]):
                if "task_key" not in task:
                    raise ValueError(f"Task {i} missing required 'task_key' field")
                
                # Check that exactly one task type is specified
                task_types = [
                    "notebook_task", "spark_jar_task", "spark_python_task", 
                    "sql_task", "pipeline_task", "python_wheel_task",
                    "dbt_task", "run_job_task", "condition_task", "for_each_task"
                ]
                
                task_type_count = sum(1 for task_type in task_types if task_type in task)
                if task_type_count == 0:
                    raise ValueError(f"Task {i} ({task.get('task_key')}) must specify exactly one task type")
                elif task_type_count > 1:
                    raise ValueError(f"Task {i} ({task.get('task_key')}) has multiple task types specified")
    
    def _generate_terraform_config(self, job_spec: Dict[str, Any]) -> str:
        """Generate the complete Terraform configuration."""
        config_parts = []
        
        # Add header comments
        config_parts.append(self._generate_header_comment(job_spec))
        
        # Add Terraform and provider configuration
        config_parts.append(self._generate_terraform_block())
        config_parts.append(self._generate_provider_block())
        
        # Add data sources
        data_sources = self._generate_data_sources(job_spec)
        if data_sources:
            config_parts.extend(data_sources)
        
        # Add job clusters (if defined)
        job_clusters = self._generate_job_clusters(job_spec)
        if job_clusters:
            config_parts.extend(job_clusters)
        
        # Add the main job resource
        config_parts.append(self._generate_job_resource(job_spec))
        
        # Add outputs
        config_parts.append(self._generate_outputs(job_spec))
        
        return "\n\n".join(config_parts)
    
    def _generate_header_comment(self, job_spec: Dict[str, Any]) -> str:
        """Generate header comment with metadata."""
        job_name = job_spec.get("name", "Unknown Job")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""# Terraform configuration for Databricks Job: {job_name}
# Generated by Databricks Job to Terraform Translation Service
# Generated on: {timestamp}
# 
# This configuration was automatically generated from a JSON job specification.
# Review and modify as needed before applying.
"""
    
    def _generate_terraform_block(self) -> str:
        """Generate the terraform configuration block."""
        return f"""terraform {{
  required_version = "{self.terraform_version}"
  
  required_providers {{
    databricks = {{
      source  = "databricks/databricks"
      version = "{self.databricks_provider_version}"
    }}
  }}
}}"""
    
    def _generate_provider_block(self) -> str:
        """Generate the databricks provider block."""
        return """provider "databricks" {
  # Configuration will be taken from environment variables:
  # DATABRICKS_HOST
  # DATABRICKS_TOKEN
  # 
  # Or configure explicitly:
  # host  = "https://your-workspace.cloud.databricks.com"
  # token = "your-token-here"
}"""
    
    def _generate_data_sources(self, job_spec: Dict[str, Any]) -> List[str]:
        """Generate data source blocks if needed."""
        data_sources = []
        
        # Add data source for current user
        data_sources.append("""data "databricks_current_user" "me" {}""")
        
        # Add data source for latest Spark version
        data_sources.append("""data "databricks_spark_version" "latest_lts" {
  long_term_support = true
}""")
        
        # Add data source for smallest node type  
        data_sources.append("""data "databricks_node_type" "smallest" {
  local_disk = true
}""")
        
        return data_sources
    
    def _generate_job_clusters(self, job_spec: Dict[str, Any]) -> List[str]:
        """Generate job cluster resources if defined."""
        clusters = []
        
        job_clusters = job_spec.get("job_clusters", [])
        for cluster in job_clusters:
            cluster_key = cluster.get("job_cluster_key", "default")
            cluster_config = self._format_cluster_config(cluster.get("new_cluster", {}))
            
            clusters.append(f"""# Job cluster: {cluster_key}
# Configuration: {cluster_config}
# (Job clusters are defined inline in the job resource)""")
        
        return clusters
    
    def _generate_job_resource(self, job_spec: Dict[str, Any]) -> str:
        """Generate the main databricks_job resource."""
        resource_name = self._sanitize_resource_name(job_spec["name"])
        
        # Start building the resource
        lines = [f'resource "databricks_job" "{resource_name}" {{']
        
        # Basic job attributes
        lines.append(f'  name = "{job_spec["name"]}"')
        
        # Description if provided
        if "description" in job_spec:
            lines.append(f'  description = "{self._escape_string(job_spec["description"])}"')
        
        # Tags if provided
        if "tags" in job_spec:
            lines.append("  tags = {")
            for key, value in job_spec["tags"].items():
                lines.append(f'    {key} = "{self._escape_string(str(value))}"')
            lines.append("  }")
        
        # Timeout if specified
        if "timeout_seconds" in job_spec:
            lines.append(f"  timeout_seconds = {job_spec['timeout_seconds']}")
        
        # Max concurrent runs
        if "max_concurrent_runs" in job_spec:
            lines.append(f"  max_concurrent_runs = {job_spec['max_concurrent_runs']}")
        
        # Job clusters
        self._add_job_clusters(lines, job_spec)
        
        # Tasks
        self._add_tasks(lines, job_spec)
        
        # Schedule
        self._add_schedule(lines, job_spec)
        
        # Email notifications
        self._add_email_notifications(lines, job_spec)
        
        # Webhook notifications
        self._add_webhook_notifications(lines, job_spec)
        
        # Run as configuration
        self._add_run_as(lines, job_spec)
        
        # Git source
        self._add_git_source(lines, job_spec)
        
        # Parameters
        self._add_parameters(lines, job_spec)
        
        # Queue settings
        self._add_queue_settings(lines, job_spec)
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _add_job_clusters(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add job cluster configurations."""
        job_clusters = job_spec.get("job_clusters", [])
        
        for cluster in job_clusters:
            cluster_key = cluster.get("job_cluster_key", "default")
            new_cluster = cluster.get("new_cluster", {})
            
            lines.append("")
            lines.append("  job_cluster {")
            lines.append(f'    job_cluster_key = "{cluster_key}"')
            lines.append("")
            lines.append("    new_cluster {")
            
            # Cluster configuration
            self._add_cluster_config(lines, new_cluster, indent="      ")
            
            lines.append("    }")
            lines.append("  }")
    
    def _add_cluster_config(self, lines: List[str], cluster_config: Dict[str, Any], indent: str = "    ") -> None:
        """Add cluster configuration details."""
        # Spark version
        if "spark_version" in cluster_config:
            lines.append(f'{indent}spark_version = "{cluster_config["spark_version"]}"')
        else:
            lines.append(f'{indent}spark_version = data.databricks_spark_version.latest_lts.id')
        
        # Node type
        if "node_type_id" in cluster_config:
            lines.append(f'{indent}node_type_id = "{cluster_config["node_type_id"]}"')
        else:
            lines.append(f'{indent}node_type_id = data.databricks_node_type.smallest.id')
        
        # Driver node type
        if "driver_node_type_id" in cluster_config:
            lines.append(f'{indent}driver_node_type_id = "{cluster_config["driver_node_type_id"]}"')
        
        # Number of workers vs autoscale
        if "num_workers" in cluster_config:
            lines.append(f'{indent}num_workers = {cluster_config["num_workers"]}')
        elif "autoscale" in cluster_config:
            autoscale = cluster_config["autoscale"]
            lines.append(f"{indent}autoscale {{")
            lines.append(f'{indent}  min_workers = {autoscale.get("min_workers", 1)}')
            lines.append(f'{indent}  max_workers = {autoscale.get("max_workers", 2)}')
            lines.append(f"{indent}}}")
        else:
            lines.append(f"{indent}num_workers = 1")
        
        # Runtime engine
        if "runtime_engine" in cluster_config:
            lines.append(f'{indent}runtime_engine = "{cluster_config["runtime_engine"]}"')
        
        # Spark configuration
        if "spark_conf" in cluster_config:
            lines.append(f"{indent}spark_conf = {{")
            for key, value in cluster_config["spark_conf"].items():
                lines.append(f'{indent}  "{key}" = "{self._escape_string(str(value))}"')
            lines.append(f"{indent}}}")
        
        # Custom tags
        if "custom_tags" in cluster_config:
            lines.append(f"{indent}custom_tags = {{")
            for key, value in cluster_config["custom_tags"].items():
                lines.append(f'{indent}  "{key}" = "{self._escape_string(str(value))}"')
            lines.append(f"{indent}}}")
        
        # AWS attributes
        if "aws_attributes" in cluster_config:
            self._add_aws_attributes(lines, cluster_config["aws_attributes"], indent)
    
    def _add_aws_attributes(self, lines: List[str], aws_attrs: Dict[str, Any], indent: str) -> None:
        """Add AWS-specific cluster attributes."""
        lines.append(f"{indent}aws_attributes {{")
        
        if "instance_profile_arn" in aws_attrs:
            lines.append(f'{indent}  instance_profile_arn = "{aws_attrs["instance_profile_arn"]}"')
        if "availability" in aws_attrs:
            lines.append(f'{indent}  availability = "{aws_attrs["availability"]}"')
        if "zone_id" in aws_attrs:
            lines.append(f'{indent}  zone_id = "{aws_attrs["zone_id"]}"')
        if "spot_bid_price_percent" in aws_attrs:
            lines.append(f'{indent}  spot_bid_price_percent = {aws_attrs["spot_bid_price_percent"]}')
        
        lines.append(f"{indent}}}")
    
    def _add_tasks(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add task configurations."""
        # Handle legacy single task format
        if self._has_legacy_task(job_spec):
            self._add_legacy_task(lines, job_spec)
            return
        
        # Handle new multi-task format
        tasks = job_spec.get("tasks", [])
        for task in tasks:
            lines.append("")
            lines.append("  task {")
            lines.append(f'    task_key = "{task["task_key"]}"')
            
            # Description
            if "description" in task:
                lines.append(f'    description = "{self._escape_string(task["description"])}"')
            
            # Timeout
            if "timeout_seconds" in task:
                lines.append(f"    timeout_seconds = {task['timeout_seconds']}")
            
            # Max retries
            if "max_retries" in task:
                lines.append(f"    max_retries = {task['max_retries']}")
            
            # Min retry interval
            if "min_retry_interval_millis" in task:
                lines.append(f"    min_retry_interval_millis = {task['min_retry_interval_millis']}")
            
            # Retry on timeout
            if "retry_on_timeout" in task:
                lines.append(f"    retry_on_timeout = {str(task['retry_on_timeout']).lower()}")
            
            # Run if condition
            if "run_if" in task:
                lines.append(f'    run_if = "{task["run_if"]}"')
            
            # Cluster configuration
            self._add_task_cluster_config(lines, task)
            
            # Task type specific configuration
            self._add_task_type_config(lines, task)
            
            # Dependencies
            self._add_task_dependencies(lines, task)
            
            # Libraries
            self._add_task_libraries(lines, task)
            
            # Email notifications for task
            if "email_notifications" in task:
                self._add_email_notifications_block(lines, task["email_notifications"], "    ")
            
            lines.append("  }")
    
    def _has_legacy_task(self, job_spec: Dict[str, Any]) -> bool:
        """Check if job uses legacy single task format."""
        legacy_task_types = [
            "notebook_task", "spark_jar_task", "spark_python_task", 
            "spark_submit_task", "pipeline_task", "python_wheel_task"
        ]
        return any(task_type in job_spec for task_type in legacy_task_types)
    
    def _add_legacy_task(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add legacy single task configuration."""
        lines.append("")
        lines.append("  # Legacy single task configuration")
        
        # Cluster configuration for legacy task
        if "new_cluster" in job_spec:
            lines.append("  new_cluster {")
            self._add_cluster_config(lines, job_spec["new_cluster"], "    ")
            lines.append("  }")
        elif "existing_cluster_id" in job_spec:
            lines.append(f'  existing_cluster_id = "{job_spec["existing_cluster_id"]}"')
        
        # Task type configuration
        self._add_task_type_config(lines, job_spec, "  ")
        
        # Libraries for legacy task
        if "libraries" in job_spec:
            for library in job_spec["libraries"]:
                self._add_library_block(lines, library, "  ")
    
    def _add_task_cluster_config(self, lines: List[str], task: Dict[str, Any]) -> None:
        """Add cluster configuration for a task."""
        if "new_cluster" in task:
            lines.append("    new_cluster {")
            self._add_cluster_config(lines, task["new_cluster"], "      ")
            lines.append("    }")
        elif "existing_cluster_id" in task:
            lines.append(f'    existing_cluster_id = "{task["existing_cluster_id"]}"')
        elif "job_cluster_key" in task:
            lines.append(f'    job_cluster_key = "{task["job_cluster_key"]}"')
    
    def _add_task_type_config(self, lines: List[str], task: Dict[str, Any], indent: str = "    ") -> None:
        """Add task type specific configuration."""
        # Notebook task
        if "notebook_task" in task:
            self._add_notebook_task(lines, task["notebook_task"], indent)
        
        # Spark JAR task
        elif "spark_jar_task" in task:
            self._add_spark_jar_task(lines, task["spark_jar_task"], indent)
        
        # Spark Python task
        elif "spark_python_task" in task:
            self._add_spark_python_task(lines, task["spark_python_task"], indent)
        
        # SQL task
        elif "sql_task" in task:
            self._add_sql_task(lines, task["sql_task"], indent)
        
        # Pipeline task
        elif "pipeline_task" in task:
            self._add_pipeline_task(lines, task["pipeline_task"], indent)
        
        # Python wheel task
        elif "python_wheel_task" in task:
            self._add_python_wheel_task(lines, task["python_wheel_task"], indent)
        
        # Run job task
        elif "run_job_task" in task:
            self._add_run_job_task(lines, task["run_job_task"], indent)
        
        # DBT task
        elif "dbt_task" in task:
            self._add_dbt_task(lines, task["dbt_task"], indent)
        
        # Condition task
        elif "condition_task" in task:
            self._add_condition_task(lines, task["condition_task"], indent)
    
    def _add_notebook_task(self, lines: List[str], notebook: Dict[str, Any], indent: str) -> None:
        """Add notebook task configuration."""
        lines.append(f"{indent}notebook_task {{")
        lines.append(f'{indent}  notebook_path = "{notebook["notebook_path"]}"')
        
        if "source" in notebook:
            lines.append(f'{indent}  source = "{notebook["source"]}"')
        
        if "base_parameters" in notebook:
            lines.append(f"{indent}  base_parameters = {{")
            for key, value in notebook["base_parameters"].items():
                lines.append(f'{indent}    "{key}" = "{self._escape_string(str(value))}"')
            lines.append(f"{indent}  }}")
        
        if "warehouse_id" in notebook:
            lines.append(f'{indent}  warehouse_id = "{notebook["warehouse_id"]}"')
        
        lines.append(f"{indent}}}")
    
    def _add_spark_jar_task(self, lines: List[str], spark_jar: Dict[str, Any], indent: str) -> None:
        """Add Spark JAR task configuration."""
        lines.append(f"{indent}spark_jar_task {{")
        
        if "main_class_name" in spark_jar:
            lines.append(f'{indent}  main_class_name = "{spark_jar["main_class_name"]}"')
        
        if "parameters" in spark_jar:
            params = '", "'.join([self._escape_string(p) for p in spark_jar["parameters"]])
            lines.append(f'{indent}  parameters = ["{params}"]')
        
        lines.append(f"{indent}}}")
    
    def _add_spark_python_task(self, lines: List[str], spark_python: Dict[str, Any], indent: str) -> None:
        """Add Spark Python task configuration."""
        lines.append(f"{indent}spark_python_task {{")
        lines.append(f'{indent}  python_file = "{spark_python["python_file"]}"')
        
        if "parameters" in spark_python:
            params = '", "'.join([self._escape_string(p) for p in spark_python["parameters"]])
            lines.append(f'{indent}  parameters = ["{params}"]')
        
        if "source" in spark_python:
            lines.append(f'{indent}  source = "{spark_python["source"]}"')
        
        lines.append(f"{indent}}}")
    
    def _add_sql_task(self, lines: List[str], sql: Dict[str, Any], indent: str) -> None:
        """Add SQL task configuration."""
        lines.append(f"{indent}sql_task {{")
        lines.append(f'{indent}  warehouse_id = "{sql["warehouse_id"]}"')
        
        if "query" in sql:
            lines.append(f"{indent}  query {{")
            lines.append(f'{indent}    query_id = "{sql["query"]["query_id"]}"')
            lines.append(f"{indent}  }}")
        
        if "dashboard" in sql:
            self._add_sql_dashboard(lines, sql["dashboard"], indent)
        
        if "alert" in sql:
            self._add_sql_alert(lines, sql["alert"], indent)
        
        if "parameters" in sql:
            lines.append(f"{indent}  parameters = {{")
            for key, value in sql["parameters"].items():
                lines.append(f'{indent}    "{key}" = "{self._escape_string(str(value))}"')
            lines.append(f"{indent}  }}")
        
        lines.append(f"{indent}}}")
    
    def _add_sql_dashboard(self, lines: List[str], dashboard: Dict[str, Any], indent: str) -> None:
        """Add SQL dashboard configuration."""
        lines.append(f"{indent}  dashboard {{")
        lines.append(f'{indent}    dashboard_id = "{dashboard["dashboard_id"]}"')
        
        if "subscriptions" in dashboard:
            for sub in dashboard["subscriptions"]:
                lines.append(f"{indent}    subscriptions {{")
                if "user_name" in sub:
                    lines.append(f'{indent}      user_name = "{sub["user_name"]}"')
                if "destination_id" in sub:
                    lines.append(f'{indent}      destination_id = "{sub["destination_id"]}"')
                lines.append(f"{indent}    }}")
        
        if "custom_subject" in dashboard:
            lines.append(f'{indent}    custom_subject = "{self._escape_string(dashboard["custom_subject"])}"')
        
        if "pause_subscriptions" in dashboard:
            lines.append(f'{indent}    pause_subscriptions = {str(dashboard["pause_subscriptions"]).lower()}')
        
        lines.append(f"{indent}  }}")
    
    def _add_sql_alert(self, lines: List[str], alert: Dict[str, Any], indent: str) -> None:
        """Add SQL alert configuration."""
        lines.append(f"{indent}  alert {{")
        lines.append(f'{indent}    alert_id = "{alert["alert_id"]}"')
        
        if "subscriptions" in alert:
            for sub in alert["subscriptions"]:
                lines.append(f"{indent}    subscriptions {{")
                if "user_name" in sub:
                    lines.append(f'{indent}      user_name = "{sub["user_name"]}"')
                if "destination_id" in sub:
                    lines.append(f'{indent}      destination_id = "{sub["destination_id"]}"')
                lines.append(f"{indent}    }}")
        
        if "pause_subscriptions" in alert:
            lines.append(f'{indent}    pause_subscriptions = {str(alert["pause_subscriptions"]).lower()}')
        
        lines.append(f"{indent}  }}")
    
    def _add_pipeline_task(self, lines: List[str], pipeline: Dict[str, Any], indent: str) -> None:
        """Add pipeline task configuration."""
        lines.append(f"{indent}pipeline_task {{")
        lines.append(f'{indent}  pipeline_id = "{pipeline["pipeline_id"]}"')
        
        if "full_refresh" in pipeline:
            lines.append(f'{indent}  full_refresh = {str(pipeline["full_refresh"]).lower()}')
        
        lines.append(f"{indent}}}")
    
    def _add_python_wheel_task(self, lines: List[str], wheel: Dict[str, Any], indent: str) -> None:
        """Add Python wheel task configuration."""
        lines.append(f"{indent}python_wheel_task {{")
        
        if "package_name" in wheel:
            lines.append(f'{indent}  package_name = "{wheel["package_name"]}"')
        
        if "entry_point" in wheel:
            lines.append(f'{indent}  entry_point = "{wheel["entry_point"]}"')
        
        if "parameters" in wheel:
            params = '", "'.join([self._escape_string(p) for p in wheel["parameters"]])
            lines.append(f'{indent}  parameters = ["{params}"]')
        
        lines.append(f"{indent}}}")
    
    def _add_run_job_task(self, lines: List[str], run_job: Dict[str, Any], indent: str) -> None:
        """Add run job task configuration."""
        lines.append(f"{indent}run_job_task {{")
        lines.append(f'{indent}  job_id = {run_job["job_id"]}')
        
        if "job_parameters" in run_job:
            lines.append(f"{indent}  job_parameters = {{")
            for key, value in run_job["job_parameters"].items():
                lines.append(f'{indent}    "{key}" = "{self._escape_string(str(value))}"')
            lines.append(f"{indent}  }}")
        
        lines.append(f"{indent}}}")
    
    def _add_dbt_task(self, lines: List[str], dbt: Dict[str, Any], indent: str) -> None:
        """Add DBT task configuration."""
        lines.append(f"{indent}dbt_task {{")
        
        commands = '", "'.join([self._escape_string(cmd) for cmd in dbt["commands"]])
        lines.append(f'{indent}  commands = ["{commands}"]')
        
        if "source" in dbt:
            lines.append(f'{indent}  source = "{dbt["source"]}"')
        
        if "project_directory" in dbt:
            lines.append(f'{indent}  project_directory = "{dbt["project_directory"]}"')
        
        if "profiles_directory" in dbt:
            lines.append(f'{indent}  profiles_directory = "{dbt["profiles_directory"]}"')
        
        if "catalog" in dbt:
            lines.append(f'{indent}  catalog = "{dbt["catalog"]}"')
        
        if "schema" in dbt:
            lines.append(f'{indent}  schema = "{dbt["schema"]}"')
        
        if "warehouse_id" in dbt:
            lines.append(f'{indent}  warehouse_id = "{dbt["warehouse_id"]}"')
        
        lines.append(f"{indent}}}")
    
    def _add_condition_task(self, lines: List[str], condition: Dict[str, Any], indent: str) -> None:
        """Add condition task configuration."""
        lines.append(f"{indent}condition_task {{")
        lines.append(f'{indent}  left = "{self._escape_string(condition["left"])}"')
        lines.append(f'{indent}  op = "{condition["op"]}"')
        lines.append(f'{indent}  right = "{self._escape_string(condition["right"])}"')
        lines.append(f"{indent}}}")
    
    def _add_task_dependencies(self, lines: List[str], task: Dict[str, Any]) -> None:
        """Add task dependencies."""
        depends_on = task.get("depends_on", [])
        
        for dep in depends_on:
            lines.append("    depends_on {")
            lines.append(f'      task_key = "{dep["task_key"]}"')
            
            if "outcome" in dep:
                lines.append(f'      outcome = "{dep["outcome"]}"')
            
            lines.append("    }")
    
    def _add_task_libraries(self, lines: List[str], task: Dict[str, Any]) -> None:
        """Add task libraries."""
        libraries = task.get("library", [])
        
        for library in libraries:
            self._add_library_block(lines, library, "    ")
    
    def _add_library_block(self, lines: List[str], library: Dict[str, Any], indent: str) -> None:
        """Add a library block."""
        lines.append(f"{indent}library {{")
        
        if "jar" in library:
            lines.append(f'{indent}  jar = "{library["jar"]}"')
        elif "egg" in library:
            lines.append(f'{indent}  egg = "{library["egg"]}"')
        elif "whl" in library:
            lines.append(f'{indent}  whl = "{library["whl"]}"')
        elif "pypi" in library:
            pypi = library["pypi"]
            lines.append(f"{indent}  pypi {{")
            lines.append(f'{indent}    package = "{pypi["package"]}"')
            if "repo" in pypi:
                lines.append(f'{indent}    repo = "{pypi["repo"]}"')
            lines.append(f"{indent}  }}")
        elif "maven" in library:
            maven = library["maven"]
            lines.append(f"{indent}  maven {{")
            lines.append(f'{indent}    coordinates = "{maven["coordinates"]}"')
            if "repo" in maven:
                lines.append(f'{indent}    repo = "{maven["repo"]}"')
            if "exclusions" in maven:
                for exclusion in maven["exclusions"]:
                    lines.append(f'{indent}    exclusions = ["{exclusion}"]')
            lines.append(f"{indent}  }}")
        elif "cran" in library:
            cran = library["cran"]
            lines.append(f"{indent}  cran {{")
            lines.append(f'{indent}    package = "{cran["package"]}"')
            if "repo" in cran:
                lines.append(f'{indent}    repo = "{cran["repo"]}"')
            lines.append(f"{indent}  }}")
        
        lines.append(f"{indent}}}")
    
    def _add_schedule(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add schedule configuration."""
        if "schedule" in job_spec:
            schedule = job_spec["schedule"]
            lines.append("")
            lines.append("  schedule {")
            lines.append(f'    quartz_cron_expression = "{schedule["quartz_cron_expression"]}"')
            lines.append(f'    timezone_id = "{schedule["timezone_id"]}"')
            
            if "pause_status" in schedule:
                lines.append(f'    pause_status = "{schedule["pause_status"]}"')
            
            lines.append("  }")
        
        # Handle trigger configuration (alternative to schedule)
        if "trigger" in job_spec:
            self._add_trigger_config(lines, job_spec["trigger"])
        
        # Handle continuous configuration
        if "continuous" in job_spec:
            self._add_continuous_config(lines, job_spec["continuous"])
    
    def _add_trigger_config(self, lines: List[str], trigger: Dict[str, Any]) -> None:
        """Add trigger configuration."""
        lines.append("")
        lines.append("  trigger {")
        
        if "pause_status" in trigger:
            lines.append(f'    pause_status = "{trigger["pause_status"]}"')
        
        if "periodic" in trigger:
            periodic = trigger["periodic"]
            lines.append("    periodic {")
            lines.append(f'      interval = {periodic["interval"]}')
            lines.append(f'      unit = "{periodic["unit"]}"')
            lines.append("    }")
        
        if "file_arrival" in trigger:
            file_arrival = trigger["file_arrival"]
            lines.append("    file_arrival {")
            lines.append(f'      url = "{file_arrival["url"]}"')
            
            if "min_time_between_triggers_seconds" in file_arrival:
                lines.append(f'      min_time_between_triggers_seconds = {file_arrival["min_time_between_triggers_seconds"]}')
            
            if "wait_after_last_change_seconds" in file_arrival:
                lines.append(f'      wait_after_last_change_seconds = {file_arrival["wait_after_last_change_seconds"]}')
            
            lines.append("    }")
        
        lines.append("  }")
    
    def _add_continuous_config(self, lines: List[str], continuous: Dict[str, Any]) -> None:
        """Add continuous configuration."""
        lines.append("")
        lines.append("  continuous {")
        
        if "pause_status" in continuous:
            lines.append(f'    pause_status = "{continuous["pause_status"]}"')
        
        lines.append("  }")
    
    def _add_email_notifications(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add email notification configuration."""
        if "email_notifications" in job_spec:
            self._add_email_notifications_block(lines, job_spec["email_notifications"], "  ")
    
    def _add_email_notifications_block(self, lines: List[str], email_notifications: Dict[str, Any], indent: str) -> None:
        """Add email notifications block."""
        lines.append("")
        lines.append(f"{indent}email_notifications {{")
        
        for event_type in ["on_start", "on_success", "on_failure", "on_duration_warning_threshold_exceeded", "on_streaming_backlog_exceeded"]:
            if event_type in email_notifications:
                emails = '", "'.join(email_notifications[event_type])
                lines.append(f'{indent}  {event_type} = ["{emails}"]')
        
        if "no_alert_for_skipped_runs" in email_notifications:
            lines.append(f'{indent}  no_alert_for_skipped_runs = {str(email_notifications["no_alert_for_skipped_runs"]).lower()}')
        
        lines.append(f"{indent}}}")
    
    def _add_webhook_notifications(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add webhook notification configuration."""
        if "webhook_notifications" in job_spec:
            webhook_notifications = job_spec["webhook_notifications"]
            lines.append("")
            lines.append("  webhook_notifications {")
            
            for event_type in ["on_start", "on_success", "on_failure", "on_duration_warning_threshold_exceeded", "on_streaming_backlog_exceeded"]:
                if event_type in webhook_notifications:
                    for webhook in webhook_notifications[event_type]:
                        lines.append(f"    {event_type} {{")
                        lines.append(f'      id = "{webhook["id"]}"')
                        lines.append("    }")
            
            lines.append("  }")
    
    def _add_run_as(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add run_as configuration."""
        if "run_as" in job_spec:
            run_as = job_spec["run_as"]
            lines.append("")
            lines.append("  run_as {")
            
            if "user_name" in run_as:
                lines.append(f'    user_name = "{run_as["user_name"]}"')
            
            if "service_principal_name" in run_as:
                lines.append(f'    service_principal_name = "{run_as["service_principal_name"]}"')
            
            lines.append("  }")
    
    def _add_git_source(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add git_source configuration."""
        if "git_source" in job_spec:
            git_source = job_spec["git_source"]
            lines.append("")
            lines.append("  git_source {")
            lines.append(f'    url = "{git_source["url"]}"')
            
            if "provider" in git_source:
                lines.append(f'    provider = "{git_source["provider"]}"')
            
            if "branch" in git_source:
                lines.append(f'    branch = "{git_source["branch"]}"')
            elif "tag" in git_source:
                lines.append(f'    tag = "{git_source["tag"]}"')
            elif "commit" in git_source:
                lines.append(f'    commit = "{git_source["commit"]}"')
            
            lines.append("  }")
    
    def _add_parameters(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add parameter configuration."""
        parameters = job_spec.get("parameters", [])
        
        for param in parameters:
            lines.append("")
            lines.append("  parameter {")
            lines.append(f'    name = "{param["name"]}"')
            lines.append(f'    default = "{self._escape_string(str(param["default"]))}"')
            lines.append("  }")
    
    def _add_queue_settings(self, lines: List[str], job_spec: Dict[str, Any]) -> None:
        """Add queue settings configuration."""
        if "queue" in job_spec:
            queue = job_spec["queue"]
            lines.append("")
            lines.append("  queue {")
            lines.append(f'    enabled = {str(queue["enabled"]).lower()}')
            lines.append("  }")
    
    def _generate_outputs(self, job_spec: Dict[str, Any]) -> str:
        """Generate output blocks."""
        resource_name = self._sanitize_resource_name(job_spec["name"])
        
        return f"""# Outputs
output "job_id" {{
  description = "The ID of the created Databricks job"
  value       = databricks_job.{resource_name}.id
}}

output "job_url" {{
  description = "The URL of the job in the Databricks workspace"
  value       = databricks_job.{resource_name}.url
}}"""
    
    def _sanitize_resource_name(self, name: str) -> str:
        """Sanitize job name for use as Terraform resource name."""
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Remove leading digits and multiple underscores
        sanitized = re.sub(r'^[0-9]+', '', sanitized)
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure it starts with a letter
        if sanitized and sanitized[0].isdigit():
            sanitized = 'job_' + sanitized
        # Default name if empty
        if not sanitized:
            sanitized = 'databricks_job'
        
        return sanitized.lower()
    
    def _format_cluster_config(self, cluster_config: Dict[str, Any]) -> str:
        """Format cluster configuration for display."""
        config_items = []
        
        if "spark_version" in cluster_config:
            config_items.append(f"Spark Version: {cluster_config['spark_version']}")
        
        if "node_type_id" in cluster_config:
            config_items.append(f"Node Type: {cluster_config['node_type_id']}")
        
        if "num_workers" in cluster_config:
            config_items.append(f"Workers: {cluster_config['num_workers']}")
        elif "autoscale" in cluster_config:
            autoscale = cluster_config["autoscale"]
            config_items.append(f"Autoscale: {autoscale.get('min_workers', 1)}-{autoscale.get('max_workers', 2)} workers")
        
        return ", ".join(config_items) if config_items else "Default configuration"
    
    def _escape_string(self, value: str) -> str:
        """Escape string values for Terraform HCL."""
        if value is None:
            return ""
        return str(value).replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')


class DatabricksJobTerraformTranslateModel(mlflow.pyfunc.PythonModel):
    """
    MLflow Python model that converts Databricks job JSON specifications 
    to Terraform HCL scripts using the integrated conversion agent.
    
    This model can be served using MLflow model serving and accepts various
    input formats containing Databricks job specifications.
    """
    
    def __init__(self):
        self.agent = None
        self.model_version = "1.0.0"
        self.model_name = "databricks-job-terraform-translator"
    
    def load_context(self, context: mlflow.pyfunc.PythonModelContext) -> None:
        """
        Load the model and initialize the conversion agent.
        
        Args:
            context: MLflow model context containing artifacts and environment info
        """
        logger.info("Loading Databricks Job to Terraform Translation model...")
        
        try:
            # Initialize the conversion agent
            self.agent = DatabricksJobToTerraformAgent()
            logger.info("Successfully loaded conversion agent")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def predict(self, context: mlflow.pyfunc.PythonModelContext, model_input):
        """
        Convert Databricks job JSON specifications to Terraform scripts.
        
        Args:
            context: MLflow model context
            model_input: Input data containing JSON job specifications.
                        Supported formats:
                        - pandas DataFrame with 'job_json' column
                        - Dictionary with 'job_json' key or job spec directly
                        - List of JSON strings
                        - Single JSON string
                        
        Returns:
            - Single Terraform script string if single input
            - List of Terraform scripts if multiple inputs
            
        Raises:
            ValueError: If input format is invalid or conversion fails
        """
        logger.info(f"Processing translation request with input type: {type(model_input)}")
        
        if self.agent is None:
            raise ValueError("Model not properly initialized. Agent is None.")
        
        try:
            # Handle different input formats
            job_jsons = self._extract_job_jsons(model_input)
            
            # Convert each job JSON to Terraform
            terraform_scripts = []
            for i, job_json in enumerate(job_jsons):
                logger.info(f"Translating job specification {i + 1}/{len(job_jsons)}")
                
                try:
                    terraform_script = self.agent.convert_json_to_terraform(job_json)
                    terraform_scripts.append(terraform_script)
                    
                except Exception as e:
                    error_msg = f"Failed to convert job specification {i + 1}: {e}"
                    logger.error(error_msg)
                    
                    # Create an error Terraform script instead of failing completely
                    error_terraform = self._create_error_terraform_script(job_json, str(e))
                    terraform_scripts.append(error_terraform)
            
            # Return single script or list based on input
            if len(terraform_scripts) == 1:
                return terraform_scripts[0]
            else:
                return terraform_scripts
                
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise ValueError(f"Failed to process translation: {e}")
    
    def _extract_job_jsons(self, model_input: Union[pd.DataFrame, Dict, List, str]) -> List[str]:
        """
        Extract job JSON strings from various input formats.
        
        Args:
            model_input: Input in various formats
            
        Returns:
            List of JSON strings
            
        Raises:
            ValueError: If input format is not supported
        """
        job_jsons = []
        
        if isinstance(model_input, str):
            # Single JSON string
            job_jsons.append(model_input)
            
        elif isinstance(model_input, list):
            # List of JSON strings
            for item in model_input:
                if isinstance(item, str):
                    job_jsons.append(item)
                else:
                    raise ValueError(f"List items must be strings, got {type(item)}")
                    
        elif isinstance(model_input, dict):
            # Dictionary with job_json key or direct job specification
            if 'job_json' in model_input:
                job_jsons.append(model_input['job_json'])
            else:
                # Treat the entire dict as a job specification
                job_jsons.append(json.dumps(model_input))
                
        elif isinstance(model_input, pd.DataFrame):
            # DataFrame with job_json column
            if 'job_json' not in model_input.columns:
                raise ValueError("DataFrame must contain 'job_json' column")
            
            for job_json in model_input['job_json']:
                if pd.isna(job_json):
                    raise ValueError("Found null value in job_json column")
                job_jsons.append(str(job_json))
                
        else:
            raise ValueError(f"Unsupported input type: {type(model_input)}")
        
        if not job_jsons:
            raise ValueError("No job JSON specifications found in input")
        
        return job_jsons
    
    def _create_error_terraform_script(self, job_json: str, error_message: str) -> str:
        """
        Create a Terraform script that documents the conversion error.
        
        Args:
            job_json: The original job JSON that failed to convert
            error_message: The error message
            
        Returns:
            Terraform script with error documentation
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to extract job name for the error script
        job_name = "unknown_job"
        try:
            job_spec = json.loads(job_json)
            job_name = job_spec.get("name", "unknown_job")
        except:
            pass
        
        error_script = f"""# CONVERSION ERROR - Databricks Job to Terraform Translation
# Generated on: {timestamp}
# Job Name: {job_name}
# Error: {error_message}
#
# Original Job JSON:
# {job_json.replace('#', '# #')}
#
# Please review the original JSON specification and fix any issues.

terraform {{
  required_version = ">=1.0"
  
  required_providers {{
    databricks = {{
      source  = "databricks/databricks"
      version = ">=1.28.0"
    }}
  }}
}}

provider "databricks" {{
  # Configuration will be taken from environment variables
  # DATABRICKS_HOST
  # DATABRICKS_TOKEN
}}

# ERROR: Could not convert the job specification above
# Please check the job JSON format and try again
# 
# Common issues:
# - Missing required 'name' field
# - Invalid task configuration
# - Malformed JSON syntax
# - Unsupported task types
"""
        
        return error_script


def log_model(
    artifact_path: str = "databricks_terraform_translator",
    registered_model_name: str = None,
    signature = None,
    input_example: Union[pd.DataFrame, Dict, str] = None,
    pip_requirements: List[str] = None,
    extra_pip_requirements: List[str] = None,
    metadata: Dict[str, Any] = None
) -> mlflow.models.model.ModelInfo:
    """
    Log the Databricks Job to Terraform Translation model to MLflow.
    
    Args:
        artifact_path: The run-relative artifact path to log the model to
        registered_model_name: Name for model registration  
        signature: Model signature defining inputs and outputs
        input_example: Example input for the model
        pip_requirements: List of pip requirements
        extra_pip_requirements: Additional pip requirements
        metadata: Additional metadata
        
    Returns:
        ModelInfo object containing model metadata
    """
    # Default pip requirements
    if pip_requirements is None:
        pip_requirements = [
            "mlflow>=2.0.0",
            "pandas>=1.3.0",
            "typing-extensions>=4.0.0"
        ]
    
    # Default input example
    if input_example is None:
        input_example = pd.DataFrame({
            'job_json': [json.dumps({
                "name": "Example Data Processing Job",
                "description": "Sample job for testing the translation service",
                "tasks": [{
                    "task_key": "process_data",
                    "notebook_task": {
                        "notebook_path": "/Users/data-team@company.com/data_processing_notebook",
                        "base_parameters": {
                            "input_path": "/mnt/data/raw",
                            "output_path": "/mnt/data/processed"
                        }
                    },
                    "new_cluster": {
                        "spark_version": "13.3.x-scala2.12",
                        "node_type_id": "i3.xlarge",
                        "num_workers": 2
                    }
                }],
                "schedule": {
                    "quartz_cron_expression": "0 2 * * *",
                    "timezone_id": "UTC"
                },
                "email_notifications": {
                    "on_failure": ["data-team@company.com"],
                    "on_success": ["data-team@company.com"]
                }
            })]
        })
    
    # Default signature
    if signature is None:
        try:
            signature = mlflow.models.infer_signature(
                input_example,
                ["# Terraform configuration would be generated here..."]
            )
        except:
            # Skip signature if it fails
            signature = None
    
    # Default metadata
    if metadata is None:
        metadata = {
            "model_type": "databricks_job_terraform_translator",
            "version": "1.0.0",
            "description": "Self-contained service that converts Databricks job JSON specifications to Terraform HCL scripts",
            "supported_features": [
                "All major Databricks task types",
                "Job clusters and existing cluster references", 
                "Scheduling and notifications",
                "Git source integration",
                "Job parameters and dependencies",
                "Error handling with informative scripts"
            ],
            "supported_task_types": [
                "notebook_task", "spark_jar_task", "spark_python_task", 
                "sql_task", "pipeline_task", "python_wheel_task",
                "dbt_task", "run_job_task", "condition_task"
            ]
        }
    
    # Create model instance
    model = DatabricksJobTerraformTranslateModel()
    
    # Log the model
    model_info = mlflow.pyfunc.log_model(
        artifact_path=artifact_path,
        python_model=model,
        registered_model_name=registered_model_name,
        signature=signature,
        input_example=input_example,
        pip_requirements=pip_requirements,
        extra_pip_requirements=extra_pip_requirements,
        metadata=metadata
    )
    
    logger.info(f"Model logged successfully to {artifact_path}")
    if registered_model_name:
        logger.info(f"Model registered as {registered_model_name}")
    
    return model_info


def quick_convert(job_json: str) -> str:
    """
    Quick conversion function for testing without MLflow context.
    
    Args:
        job_json: JSON string containing job specification
        
    Returns:
        Generated Terraform script
    """
    model = DatabricksJobTerraformTranslateModel()
    # Create a mock context for initialization
    mock_context = type('MockContext', (), {})()
    model.load_context(mock_context)
    return model.predict(mock_context, job_json)


if __name__ == "__main__":
    # Example usage and testing
    example_job = {
        "name": "Production Data Pipeline",
        "description": "Daily data processing pipeline with multiple tasks",
        "tasks": [
            {
                "task_key": "extract_data",
                "notebook_task": {
                    "notebook_path": "/Repos/data-engineering/extract_raw_data",
                    "base_parameters": {
                        "source_database": "raw_data",
                        "extraction_date": "{{ ds }}"
                    }
                },
                "new_cluster": {
                    "spark_version": "13.3.x-scala2.12",
                    "node_type_id": "i3.xlarge",
                    "num_workers": 3,
                    "custom_tags": {
                        "team": "data-engineering",
                        "environment": "production"
                    }
                }
            },
            {
                "task_key": "transform_data",
                "notebook_task": {
                    "notebook_path": "/Repos/data-engineering/transform_data",
                    "base_parameters": {
                        "input_table": "raw_data.events",
                        "output_table": "processed_data.events"
                    }
                },
                "depends_on": [
                    {
                        "task_key": "extract_data",
                        "outcome": "SUCCESS"
                    }
                ],
                "job_cluster_key": "shared_cluster"
            }
        ],
        "job_clusters": [
            {
                "job_cluster_key": "shared_cluster",
                "new_cluster": {
                    "spark_version": "13.3.x-scala2.12",
                    "node_type_id": "i3.2xlarge",
                    "autoscale": {
                        "min_workers": 2,
                        "max_workers": 8
                    }
                }
            }
        ],
        "email_notifications": {
            "on_failure": ["data-team@company.com", "oncall@company.com"],
            "on_success": ["data-team@company.com"]
        },
        "schedule": {
            "quartz_cron_expression": "0 2 * * *",
            "timezone_id": "UTC"
        },
        "tags": {
            "team": "data-engineering",
            "environment": "production",
            "cost_center": "analytics"
        }
    }
    
    job_json = json.dumps(example_job, indent=2)
    
    print("Testing Databricks Job to Terraform Translation Service...")
    print("=" * 70)
    print(f"Input job name: {example_job['name']}")
    print(f"Number of tasks: {len(example_job['tasks'])}")
    print(f"Has schedule: {bool(example_job.get('schedule'))}")
    print(f"Has job clusters: {bool(example_job.get('job_clusters'))}")
    print("-" * 70)
    
    try:
        terraform_script = quick_convert(job_json)
        print("✅ Translation successful!")
        print("\n📄 Generated Terraform script:")
        print("-" * 70)
        print(terraform_script)
        
    except Exception as e:
        print(f"❌ Translation failed: {e}")
        import traceback
        traceback.print_exc()
