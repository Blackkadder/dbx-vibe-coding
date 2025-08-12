# Streamlit CI/CD Setup

This directory contains the complete CI/CD pipeline for the Streamlit application.

## Components

### GitHub Actions Workflows

- **`.github/workflows/ci.yml`** - Continuous Integration pipeline
  - Runs tests across multiple Python versions (3.9, 3.10, 3.11, 3.12)
  - Performs code linting with flake8
  - Code formatting checks with black
  - Import sorting checks with isort
  - Security scanning with safety
  - Test coverage reporting
  - Streamlit health checks

- **`.github/workflows/cd.yml`** - Continuous Deployment pipeline
  - Builds and pushes Docker images to GitHub Container Registry
  - Deploys to staging environment automatically on main branch
  - Manual deployment to production environment
  - Smoke tests and health checks

- **`.github/workflows/security.yml`** - Security scanning pipeline
  - Dependency vulnerability scanning with safety and pip-audit
  - Code security scanning with bandit
  - Docker image vulnerability scanning with Trivy
  - Secret scanning with GitLeaks
  - Runs daily and on code changes

### Containerization

- **`Dockerfile`** - Multi-stage Docker build for the Streamlit app
  - Based on Python 3.11 slim image
  - Includes health checks
  - Runs as non-root user for security
  - Optimized for production deployment

### Testing

- **`frontend/tests/`** - Test suite for the Streamlit application
  - Unit tests for core functionality
  - Mocking for Streamlit components
  - Test coverage reporting
  - Compatible with pytest

### Configuration

- **`frontend/pyproject.toml`** - Python project configuration
  - pytest configuration
  - black code formatting settings
  - isort import sorting settings
  - coverage reporting configuration

- **`frontend/.flake8`** - Flake8 linting configuration
- **`frontend/requirements-dev.txt`** - Development dependencies

## Usage

### Running Tests Locally

```bash
cd frontend
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

### Code Formatting

```bash
cd frontend
black .
isort .
flake8 .
```

### Building Docker Image

```bash
docker build -t streamlit-app .
docker run -p 8501:8501 streamlit-app
```

### Manual Deployment

The CD workflow can be triggered manually via GitHub Actions with environment selection:
1. Go to Actions tab in GitHub
2. Select "CD - Deploy Streamlit App"
3. Click "Run workflow"
4. Select target environment (staging/production)

## Environment Configuration

For production deployment, configure the following secrets in GitHub:

- `GITHUB_TOKEN` (automatically provided)
- Additional secrets for your deployment target (AWS, Azure, GCP, etc.)

## Monitoring and Alerting

The workflows include:
- Test result reporting
- Coverage tracking with Codecov integration
- Security vulnerability alerts
- Deployment status notifications

## Customization

To adapt this CI/CD setup for your specific deployment target:

1. Update the deployment steps in `.github/workflows/cd.yml`
2. Add your specific infrastructure configuration
3. Configure environment-specific secrets
4. Customize health check endpoints
5. Add monitoring and alerting integrations