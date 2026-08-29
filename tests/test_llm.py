import pytest
import requests
from unittest.mock import patch, MagicMock
from src.llm import LocalLLM


def test_llm_initialization():
    llm = LocalLLM()
    assert llm.api_base == "http://127.0.0.1:8788"
    assert llm.api_path == "/v1/responses"
    assert llm.model_name == "oxx"
    assert llm.timeout == 120
    assert llm.max_retries == 3
    assert llm.use_stream is True


def test_llm_initialization_with_params():
    llm = LocalLLM(
        api_base="http://custom:9999",
        api_path="/custom",
        model_name="custom-model",
        timeout=30,
        max_retries=5
    )
    assert llm.api_base == "http://custom:9999"
    assert llm.api_path == "/custom"
    assert llm.model_name == "custom-model"
    assert llm.timeout == 30
    assert llm.max_retries == 5


@patch("src.llm.requests.post")
def test_llm_call_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "Hello, World!"}]}
        ]
    }
    mock_post.return_value = mock_response

    llm = LocalLLM(use_stream=False)
    result = llm._call("Say hello")

    assert result == "Hello, World!"
    mock_post.assert_called_once()


@patch("src.llm.requests.post")
def test_llm_call_retry_on_failure(mock_post):
    mock_fail = MagicMock()
    mock_fail.status_code = 500
    mock_fail.raise_for_status.side_effect = requests.RequestException("Server Error")

    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.json.return_value = {
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "Success after retry"}]}
        ]
    }

    mock_post.side_effect = [mock_fail, mock_fail, mock_success]

    llm = LocalLLM(max_retries=3, use_stream=False)
    result = llm._call("Test retry")

    assert result == "Success after retry"
    assert mock_post.call_count == 3


@patch("src.llm.requests.post")
def test_llm_call_timeout(mock_post):
    mock_post.side_effect = requests.Timeout("Request timed out")

    llm = LocalLLM(timeout=1, max_retries=1, use_stream=False)

    with pytest.raises(Exception) as exc_info:
        llm._call("Test timeout")

    assert "timeout" in str(exc_info.value).lower()


@patch("src.llm.requests.post")
def test_llm_call_all_retries_fail(mock_post):
    mock_fail = MagicMock()
    mock_fail.status_code = 500
    mock_fail.raise_for_status.side_effect = requests.RequestException("Server Error")

    mock_post.return_value = mock_fail

    llm = LocalLLM(max_retries=2, use_stream=False)

    with pytest.raises(Exception):
        llm._call("Test all retries fail")

    assert mock_post.call_count == 2
