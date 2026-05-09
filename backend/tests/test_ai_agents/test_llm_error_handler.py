"""Tests for LLM error classification."""
from features.ai_agents.llm_error_handler import classify_llm_error


class TestClassifyLlmError:
    def test_gemini_api_key_blocked_returns_actionable_message(self):
        exc = Exception(
            "VertexAIException BadRequestError - {\"error\": {\"reason\": \"API_KEY_SERVICE_BLOCKED\", "
            "\"domain\": \"generativelanguage.googleapis.com\"}}"
        )
        result = classify_llm_error(exc)
        assert "Gemini API key" in result
        assert "Google Cloud Console" in result

    def test_gemini_permission_denied_returns_actionable_message(self):
        exc = Exception("PERMISSION_DENIED: generativelanguage.googleapis.com access denied")
        result = classify_llm_error(exc)
        assert "Gemini API key" in result

    def test_openai_invalid_key_returns_actionable_message(self):
        exc = Exception("AuthenticationError: Incorrect API key provided: sk-bad")
        result = classify_llm_error(exc)
        assert "OpenAI API key" in result
        assert "OPENAI_API_KEY" in result

    def test_openai_no_key_returns_actionable_message(self):
        exc = Exception("No API key provided. Set OPENAI_API_KEY.")
        result = classify_llm_error(exc)
        assert "OpenAI API key" in result

    def test_unknown_error_returns_raw_message(self):
        exc = Exception("Some unexpected model error occurred")
        result = classify_llm_error(exc)
        assert "Some unexpected model error occurred" in result

    def test_always_returns_string(self):
        for exc in [
            Exception("API_KEY_SERVICE_BLOCKED"),
            Exception("Incorrect API key"),
            Exception("mystery error"),
        ]:
            assert isinstance(classify_llm_error(exc), str)
