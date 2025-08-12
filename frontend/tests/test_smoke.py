"""
Smoke tests for the Streamlit application
Tests basic functionality without UI rendering
"""
import time
from unittest.mock import patch

import pytest

from app import generate_terraform_variables


def test_app_smoke_test():
    """Basic smoke test to ensure app components work"""
    # Test that the terraform generation function works
    job_id = "smoke-test-123"
    
    with patch('time.sleep'):  # Speed up the test
        result = generate_terraform_variables(job_id)
    
    # Basic validations
    assert result is not None
    assert len(result) > 0
    assert job_id in result
    assert "terraform" in result.lower()
    assert "variable" in result
    assert "resource" in result
    assert "output" in result


def test_terraform_syntax_validation():
    """Test that generated terraform has basic syntax elements"""
    job_id = "syntax-test"
    
    with patch('time.sleep'):
        result = generate_terraform_variables(job_id)
    
    # Check for terraform syntax elements
    lines = result.split('\n')
    
    # Count blocks
    variable_count = sum(1 for line in lines if line.strip().startswith('variable '))
    resource_count = sum(1 for line in lines if line.strip().startswith('resource '))
    output_count = sum(1 for line in lines if line.strip().startswith('output '))
    
    assert variable_count >= 4, f"Expected at least 4 variables, got {variable_count}"
    assert resource_count >= 2, f"Expected at least 2 resources, got {resource_count}"
    assert output_count >= 3, f"Expected at least 3 outputs, got {output_count}"
    
    # Check for proper terraform structure
    assert any('{' in line for line in lines), "Missing opening braces"
    assert any('}' in line for line in lines), "Missing closing braces"


def test_app_imports():
    """Test that all required modules can be imported"""
    try:
        import streamlit as st
        import pandas as pd
        import json
        import time
        import uuid
        from typing import Dict, Any
    except ImportError as e:
        pytest.fail(f"Failed to import required module: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])