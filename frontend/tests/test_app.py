"""
Test suite for the Streamlit Terraform Generator App
"""

import time
from unittest.mock import MagicMock, patch

import pytest
import streamlit as st

from app import generate_terraform_variables, main


def test_generate_terraform_variables():
    """Test terraform variables generation function"""
    job_id = "test-job-123"

    # Mock time.sleep to speed up tests
    with patch("time.sleep"):
        result = generate_terraform_variables(job_id)

    # Check that result contains expected content
    assert f'default     = "{job_id}"' in result
    assert 'variable "job_id"' in result
    assert 'variable "environment"' in result
    assert 'variable "region"' in result
    assert 'variable "instance_type"' in result
    assert 'variable "tags"' in result
    assert 'resource "aws_instance"' in result
    assert 'resource "aws_s3_bucket"' in result
    assert 'output "instance_id"' in result
    assert 'output "bucket_name"' in result
    assert 'output "job_endpoint"' in result


def test_generate_terraform_variables_with_special_characters():
    """Test terraform variables generation with special characters in job ID"""
    job_id = "test-job_123.special"

    with patch("time.sleep"):
        result = generate_terraform_variables(job_id)

    assert job_id in result
    assert 'variable "job_id"' in result


@pytest.fixture
def streamlit_app():
    """Fixture to set up Streamlit app testing environment"""
    # Mock streamlit components to avoid actual UI rendering during tests
    with (
        patch("streamlit.set_page_config"),
        patch("streamlit.markdown"),
        patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]),
        patch("streamlit.text_input"),
        patch("streamlit.button"),
        patch("streamlit.download_button"),
        patch("streamlit.error"),
        patch("streamlit.rerun"),
    ):
        yield


def test_app_initialization(streamlit_app):
    """Test that the app initializes properly"""
    # Test session state initialization
    if "terraform_output" not in st.session_state:
        st.session_state.terraform_output = ""
    if "is_loading" not in st.session_state:
        st.session_state.is_loading = False
    if "job_completed" not in st.session_state:
        st.session_state.job_completed = False

    assert hasattr(st.session_state, "terraform_output")
    assert hasattr(st.session_state, "is_loading")
    assert hasattr(st.session_state, "job_completed")


def test_main_function_execution(streamlit_app):
    """Test that main function executes without errors"""
    # Initialize session state for the test
    st.session_state.terraform_output = ""
    st.session_state.is_loading = False
    st.session_state.job_completed = False
    st.session_state.job_id_input = "test-job"

    try:
        main()
    except Exception as e:
        pytest.fail(f"main() raised {e} unexpectedly!")


class TestTerraformGeneration:
    """Test class for terraform generation functionality"""

    def test_terraform_output_format(self):
        """Test that terraform output follows proper format"""
        job_id = "format-test"

        with patch("time.sleep"):
            result = generate_terraform_variables(job_id)

        lines = result.split("\n")

        # Check for proper terraform syntax
        variable_blocks = [
            line for line in lines if line.strip().startswith("variable ")
        ]
        resource_blocks = [
            line for line in lines if line.strip().startswith("resource ")
        ]
        output_blocks = [line for line in lines if line.strip().startswith("output ")]

        assert len(variable_blocks) >= 4  # At least 4 variables defined
        assert len(resource_blocks) >= 2  # At least 2 resources defined
        assert len(output_blocks) >= 3  # At least 3 outputs defined

    def test_terraform_variables_uniqueness(self):
        """Test that different job IDs produce different terraform configs"""
        job_id_1 = "unique-job-1"
        job_id_2 = "unique-job-2"

        with patch("time.sleep"):
            result_1 = generate_terraform_variables(job_id_1)
            result_2 = generate_terraform_variables(job_id_2)

        assert job_id_1 in result_1
        assert job_id_2 in result_2
        assert job_id_1 not in result_2
        assert job_id_2 not in result_1


if __name__ == "__main__":
    pytest.main([__file__])
