"""LLM adapter and schemas."""

from .adapter import LLMAdapter, LLMAdapterConfig, LLMProvider, MockLLMProvider
from .prompts import coding_prompt, feedback_prompt, proposal_prompt
from .providers import LiteLLMProvider
from .schemas import CodeDraft, FeedbackDraft, ProposalDraft

__all__ = [
    "CodeDraft",
    "FeedbackDraft",
    "LLMAdapter",
    "LLMAdapterConfig",
    "LLMProvider",
    "LiteLLMProvider",
    "MockLLMProvider",
    "ProposalDraft",
    "coding_prompt",
    "feedback_prompt",
    "proposal_prompt",
]
