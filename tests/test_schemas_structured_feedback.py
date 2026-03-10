"""Tests for StructuredFeedback and ReasoningTrace schemas (FC-3 feedback pipeline)."""

import json

from llm.adapter import MockLLMProvider
from llm.schemas import ReasoningTrace, StructuredFeedback


class TestStructuredFeedback:
    """Test StructuredFeedback dataclass and from_dict method."""

    def test_from_dict_full_fields(self):
        """Create from dict with all fields, verify each field."""
        data = {
            "execution": "Executed successfully",
            "return_checking": "Return values verified",
            "code": "def foo(): pass",
            "final_decision": True,
            "reasoning": "All checks passed",
        }
        obj = StructuredFeedback.from_dict(data)
        assert obj.execution == "Executed successfully"
        assert obj.return_checking == "Return values verified"
        assert obj.code == "def foo(): pass"
        assert obj.final_decision is True
        assert obj.reasoning == "All checks passed"

    def test_from_dict_minimal(self):
        """Create with only required fields, verify Optional fields default to None."""
        data = {
            "execution": "Executed",
            "code": "code",
            "reasoning": "Some reasoning",
        }
        obj = StructuredFeedback.from_dict(data)
        assert obj.execution == "Executed"
        assert obj.code == "code"
        assert obj.reasoning == "Some reasoning"
        assert obj.return_checking is None
        assert obj.final_decision is None

    def test_from_dict_empty(self):
        """Create from empty dict, verify all fields have safe defaults."""
        obj = StructuredFeedback.from_dict({})
        assert obj.execution == ""
        assert obj.return_checking is None
        assert obj.code == ""
        assert obj.final_decision is None
        assert obj.reasoning == ""

    def test_field_types(self):
        """Verify field types are correct."""
        data = {
            "execution": "exec",
            "return_checking": "check",
            "code": "code",
            "final_decision": True,
            "reasoning": "reason",
        }
        obj = StructuredFeedback.from_dict(data)
        assert isinstance(obj.execution, str)
        assert isinstance(obj.return_checking, (str, type(None)))
        assert isinstance(obj.code, str)
        assert isinstance(obj.final_decision, (bool, type(None)))
        assert isinstance(obj.reasoning, str)

    def test_from_dict_with_none_return_checking(self):
        """Handle None value for return_checking field."""
        data = {
            "execution": "executed",
            "return_checking": None,
            "code": "code",
            "final_decision": False,
            "reasoning": "reasoning",
        }
        obj = StructuredFeedback.from_dict(data)
        assert obj.return_checking is None

    def test_from_dict_with_none_final_decision(self):
        """Handle None value for final_decision field."""
        data = {
            "execution": "executed",
            "code": "code",
            "reasoning": "reasoning",
            "final_decision": None,
        }
        obj = StructuredFeedback.from_dict(data)
        assert obj.final_decision is None


class TestReasoningTrace:
    """Test ReasoningTrace dataclass and from_dict method."""

    def test_from_dict_full(self):
        """Create from dict with all fields."""
        data = {
            "trace_id": "trace-123",
            "stages": {"stage1": "complete", "stage2": "pending"},
            "timestamp": "2025-03-07T10:00:00Z",
            "metadata": {"version": "1.0", "status": "active"},
        }
        obj = ReasoningTrace.from_dict(data)
        assert obj.trace_id == "trace-123"
        assert obj.stages == {"stage1": "complete", "stage2": "pending"}
        assert obj.timestamp == "2025-03-07T10:00:00Z"
        assert obj.metadata == {"version": "1.0", "status": "active"}

    def test_from_dict_minimal(self):
        """Create with only trace_id, verify defaults."""
        data = {"trace_id": "trace-456"}
        obj = ReasoningTrace.from_dict(data)
        assert obj.trace_id == "trace-456"
        assert obj.stages == {}
        assert obj.timestamp == ""
        assert obj.metadata == {}

    def test_from_dict_empty(self):
        """Create from empty dict, verify safe defaults."""
        obj = ReasoningTrace.from_dict({})
        assert obj.trace_id == ""
        assert obj.stages == {}
        assert obj.timestamp == ""
        assert obj.metadata == {}

    def test_from_dict_stages_as_dict(self):
        """Verify stages field handles dict properly."""
        data = {"trace_id": "t1", "stages": {"analysis": "done"}}
        obj = ReasoningTrace.from_dict(data)
        assert isinstance(obj.stages, dict)
        assert obj.stages["analysis"] == "done"

    def test_from_dict_metadata_as_dict(self):
        """Verify metadata field handles dict properly."""
        data = {"trace_id": "t2", "metadata": {"key": "value"}}
        obj = ReasoningTrace.from_dict(data)
        assert isinstance(obj.metadata, dict)
        assert obj.metadata["key"] == "value"


class TestMockDetection:
    """Test MockLLMProvider detection of StructuredFeedback schema."""

    def test_mock_detects_structured_feedback(self):
        """Call MockLLMProvider with structured feedback prompt, verify JSON response."""
        provider = MockLLMProvider()
        prompt = """
        Please provide structured feedback with:
        - `execution` status
        - `return_checking` results
        - `code` review findings
        - `final_decision` boolean
        - `reasoning` explanation
        """
        response = provider.complete(prompt)
        data = json.loads(response)

        # Verify response has all required StructuredFeedback fields
        assert "execution" in data
        assert "code" in data
        assert "reasoning" in data
        assert isinstance(data["execution"], str)
        assert isinstance(data["code"], str)
        assert isinstance(data["reasoning"], str)

    def test_mock_structured_feedback_with_keywords(self):
        """Test detection using 'structured feedback' keyword."""
        provider = MockLLMProvider()
        prompt = "Please provide structured feedback on this implementation"
        response = provider.complete(prompt)
        data = json.loads(response)

        # Should return structured feedback JSON
        assert "execution" in data
        assert "code" in data
        assert "reasoning" in data

    def test_mock_structured_feedback_all_fields(self):
        """Verify mock response includes all StructuredFeedback fields."""
        provider = MockLLMProvider()
        prompt = """
        Analyze and provide structured feedback with:
        `execution` `return_checking` `code` `final_decision` `reasoning`
        """
        response = provider.complete(prompt)
        data = json.loads(response)

        # All fields should be present in mock response
        assert "execution" in data
        assert "return_checking" in data
        assert "code" in data
        assert "final_decision" in data
        assert "reasoning" in data

    def test_mock_feedback_can_be_parsed(self):
        """Verify mock response can be parsed into StructuredFeedback object."""
        provider = MockLLMProvider()
        prompt = "Structured feedback with `execution` and `code` and `reasoning`"
        response = provider.complete(prompt)
        data = json.loads(response)

        # Parse into StructuredFeedback object
        obj = StructuredFeedback.from_dict(data)
        assert isinstance(obj, StructuredFeedback)
        assert obj.execution
        assert obj.code
        assert obj.reasoning
