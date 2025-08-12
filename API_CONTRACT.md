# Model API Contract

This document specifies the API contract between the "I hate terraform" middleware and your external model endpoint.

## Overview

The middleware sends Databricks job configurations to your model API via HTTP POST requests. Your model processes the job data and returns generated Terraform code as a string response.

**Key Points:**
- The middleware does NOT perform any Terraform generation itself
- All conversion logic should be in your deployed model
- The middleware only handles authentication, job retrieval, and API communication

## API Endpoint

### Request

**Method**: `POST`  
**Content-Type**: `application/json`  
**Authentication**: Optional `Authorization: Bearer <api_key>` header

### Request Payload

```json
{
  "job_details": {
    "job_id": 123,
    "name": "My Databricks Job",
    "created_time": 1640995200000,
    "creator_user_name": "user@company.com",
    "settings": {
      "name": "My Databricks Job",
      "description": "Job description",
      "tags": { "environment": "prod" },
      "max_concurrent_runs": 1,
      "timeout_seconds": 3600,
      "tasks": [
        {
          "task_key": "main",
          "type": "notebook",
          "notebook_path": "/Users/user@company.com/my-notebook",
          "base_parameters": { "param1": "value1" }
        }
      ],
      "schedule": {
        "quartz_cron_expression": "0 0 12 * * ?",
        "timezone_id": "UTC"
      }
    },
    "cluster_spec": {
      "cluster_name": "my-cluster",
      "node_type_id": "i3.xlarge",
      "driver_node_type_id": "i3.xlarge", 
      "num_workers": 2,
      "spark_version": "11.3.x-scala2.12",
      "spark_conf": { "spark.sql.adaptive.enabled": "true" },
      "custom_tags": { "team": "data-eng" }
    }
  },
  "workspace_url": "https://your-workspace.cloud.databricks.com",
  "output_format": "terraform",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "job_id": 123,
    "job_name": "My Databricks Job",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Response

**Success Response** (HTTP 200):
```json
{
  "terraform_code": "# Generated Terraform Configuration\n\nresource \"databricks_job\" \"this\" {\n  name = \"My Databricks Job\"\n  \n  task {\n    task_key = \"main\"\n    \n    notebook_task {\n      notebook_path = \"/Users/user@company.com/my-notebook\"\n      base_parameters = {\n        param1 = \"value1\"\n      }\n    }\n    \n    new_cluster {\n      num_workers   = 2\n      spark_version = \"11.3.x-scala2.12\"\n      node_type_id  = \"i3.xlarge\"\n      \n      spark_conf = {\n        \"spark.sql.adaptive.enabled\" = \"true\"\n      }\n      \n      custom_tags = {\n        team = \"data-eng\"\n      }\n    }\n  }\n  \n  tags = {\n    environment = \"prod\"\n  }\n  \n  schedule {\n    quartz_cron_expression = \"0 0 12 * * ?\"\n    timezone_id            = \"UTC\"\n  }\n}"
}
```

**Error Response** (HTTP 4xx/5xx):
```json
{
  "error": "Description of what went wrong",
  "message": "Additional error details", 
  "code": "ERROR_CODE_IF_APPLICABLE"
}
```

## Field Descriptions

### Job Details Fields

- `job_id`: Numeric Databricks job identifier
- `name`: Human-readable job name
- `created_time`: Unix timestamp of job creation
- `creator_user_name`: Email of job creator
- `settings`: Complete Databricks job configuration
- `cluster_spec`: Cluster configuration details

### Settings Sub-fields

- `tasks`: Array of job tasks with notebook/script/wheel configurations
- `schedule`: Cron-based scheduling configuration
- `tags`: Key-value pairs for resource tagging
- `max_concurrent_runs`: Maximum parallel executions
- `timeout_seconds`: Job timeout in seconds

### Cluster Spec Sub-fields

- `node_type_id`: AWS/Azure instance type for worker nodes
- `driver_node_type_id`: Instance type for driver node
- `num_workers`: Number of worker nodes
- `spark_version`: Databricks Spark runtime version
- `spark_conf`: Spark configuration parameters
- `custom_tags`: Additional tags for cluster resources

## Implementation Requirements

### Your Model Should:

1. **Parse the job configuration** from the `job_details` field
2. **Generate valid Terraform HCL** that recreates the job
3. **Handle all job types**: notebooks, JAR files, Python wheels, etc.
4. **Include cluster configurations** if using new clusters  
5. **Preserve scheduling** if the job has a schedule
6. **Include tags and metadata** from the original job
7. **Return valid HCL syntax** that can be executed with `terraform plan/apply`

### Error Handling

- Return HTTP 4xx for client errors (invalid job data, missing fields)
- Return HTTP 5xx for server errors (model failures, processing errors)
- Include descriptive error messages in the response body
- Log errors for debugging and monitoring

## Testing Your API

You can test your model API with this sample curl command:

```bash
curl -X POST "https://your-model-api.com/generate-terraform" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "job_details": {
      "job_id": 123,
      "name": "Test Job",
      "settings": {
        "name": "Test Job",
        "tasks": [{
          "task_key": "main",
          "type": "notebook", 
          "notebook_path": "/test/notebook"
        }]
      },
      "cluster_spec": {
        "node_type_id": "i3.xlarge",
        "num_workers": 1,
        "spark_version": "11.3.x-scala2.12"
      }
    },
    "workspace_url": "https://test.databricks.com",
    "output_format": "terraform",
    "request_id": "test-123"
  }'
```

## Security Considerations

- **Authentication**: Use API keys or OAuth for production deployments
- **Input Validation**: Validate all input fields and reject malformed requests  
- **Rate Limiting**: Implement rate limiting to prevent abuse
- **Logging**: Log requests for monitoring and debugging (avoid logging sensitive data)
- **HTTPS**: Always use HTTPS in production for encrypted communication

## Performance Requirements

- **Timeout**: Middleware will timeout requests after 120 seconds
- **Response Size**: Keep Terraform code responses under 1MB when possible
- **Concurrent Requests**: Handle multiple concurrent job conversion requests
- **Caching**: Consider caching similar job configurations to improve performance
