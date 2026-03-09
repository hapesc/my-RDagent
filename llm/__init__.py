"""LLM adapter and schemas."""

from .adapter import LLMAdapter, LLMAdapterConfig, LLMProvider, MockLLMProvider
from .prompts import (
    coding_prompt,
    feedback_prompt,
    proposal_prompt,
    reasoning_analysis_prompt,
    reasoning_design_prompt,
    reasoning_hypothesize_prompt,
    reasoning_identify_prompt,
    virtual_eval_prompt,
)
from .providers import LiteLLMProvider
from .schemas import (
    AnalysisResult,
    CodeDraft,
    ExperimentDesign,
    FeedbackDraft,
    HypothesisFormulation,
    ProblemIdentification,
    ProposalDraft,
    VirtualEvalResult,
)

__all__ = [
    "AnalysisResult",
    "CodeDraft",
    "ExperimentDesign",
    "FeedbackDraft",
    "HypothesisFormulation",
    "LLMAdapter",
    "LLMAdapterConfig",
    "LLMProvider",
    "LiteLLMProvider",
    "MockLLMProvider",
    "ProblemIdentification",
    "ProposalDraft",
    "VirtualEvalResult",
    "coding_prompt",
    "feedback_prompt",
    "proposal_prompt",
    "reasoning_analysis_prompt",
    "reasoning_design_prompt",
    "reasoning_hypothesize_prompt",
    "reasoning_identify_prompt",
    "virtual_eval_prompt",
]
