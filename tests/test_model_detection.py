"""
Tests for Ollama model auto-detection functionality
"""
import pytest
from unittest.mock import patch, MagicMock
from coordinator.worker import detect_available_models


def test_detect_available_models_success():
    """Test successful model detection from ollama list"""
    mock_output = """NAME                    ID              SIZE    MODIFIED       
llama3.2:latest        abc123          7.4 GB  2 weeks ago    
mistral:latest         def456          4.1 GB  3 days ago     """
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output
        )
        
        result = detect_available_models()
        assert result == "llama3.2"


def test_detect_available_models_with_tags():
    """Test model detection strips version tags correctly"""
    mock_output = """NAME                    ID              SIZE    MODIFIED       
gemma:2b               xyz789          1.7 GB  1 week ago     """
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output
        )
        
        result = detect_available_models()
        assert result == "gemma"


def test_detect_available_models_no_models():
    """Test when no models are installed"""
    mock_output = """NAME                    ID              SIZE    MODIFIED       """
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output
        )
        
        result = detect_available_models()
        assert result is None


def test_detect_available_models_ollama_not_found():
    """Test when ollama CLI is not installed"""
    with patch('subprocess.run', side_effect=FileNotFoundError()):
        result = detect_available_models()
        assert result is None


def test_detect_available_models_timeout():
    """Test when ollama list times out"""
    import subprocess
    with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('ollama', 5)):
        result = detect_available_models()
        assert result is None


@pytest.mark.skip(reason="Cannot directly access actor attributes in Ray - requires getter method")
@pytest.mark.asyncio
async def test_worker_uses_auto_detection():
    """Test that LLMWorker uses auto-detection when no model specified"""
    # Note: This test is skipped because Ray actors don't expose attributes directly
    # Would need to add a get_model_name() method to LLMWorker to test this
    pass


@pytest.mark.skip(reason="Cannot directly access actor attributes in Ray - requires getter method")  
@pytest.mark.asyncio
async def test_worker_respects_env_var():
    """Test that OLLAMA_MODEL env var takes precedence over auto-detection"""
    # Note: This test is skipped because Ray actors don't expose attributes directly
    # Would need to add a get_model_name() method to LLMWorker to test this
    pass

