"""Shared feedback enrichment for CoSTEER retry rounds.

Replaces the three duplicate ``_enrich_*_with_feedback()`` methods in
scenario plugins. Reads all FC-3 structured feedback dimensions, not
just ``_costeer_feedback``.
"""

from __future__ import annotations

from typing import Any


def enrich_feedback_context(
    proposal_summary: str,
    hypothesis: dict[str, Any],
) -> str:
    """Build enriched prompt context from hypothesis feedback fields.

    Parameters
    ----------
    proposal_summary:
        The original proposal/hypothesis text.
    hypothesis:
        The ``experiment.hypothesis`` dict containing CoSTEER feedback keys.

    Returns
    -------
    str
        ``proposal_summary`` with structured feedback appended, or unchanged
        if no meaningful feedback is present.
    """
    if not proposal_summary:
        proposal_summary = ""
    parts: list[str] = [proposal_summary]

    # --- FC-3 structured feedback (execution / code / return / reasoning) ---
    fb_execution = (hypothesis.get("_costeer_feedback_execution") or "").strip()
    fb_code = (hypothesis.get("_costeer_feedback_code") or "").strip()
    fb_return = (hypothesis.get("_costeer_feedback_return") or "").strip()
    fb_reasoning = (hypothesis.get("_costeer_feedback") or "").strip()
    round_idx = hypothesis.get("_costeer_round", 0)

    has_structured = any([fb_execution, fb_code, fb_return])

    if has_structured:
        parts.append(f"\n## Previous Round {round_idx} Feedback")
        if fb_execution:
            parts.append(f"### Execution: {fb_execution}")
        if fb_return:
            parts.append(f"### Output Check: {fb_return}")
        if fb_code:
            parts.append(f"### Code Quality: {fb_code}")
        if fb_reasoning:
            parts.append(f"### Overall: {fb_reasoning}")
    elif fb_reasoning:
        parts.append(f"\nPrevious round feedback:\n{fb_reasoning}")

    # --- Degradation visibility ---
    code_source = (hypothesis.get("_code_source") or "").strip()
    if code_source == "failed":
        parts.append("\nWARNING: Previous code generation FAILED. The code used was a fallback template.")

    # Only return enriched text if we actually added something
    if len(parts) == 1:
        return proposal_summary

    return "\n".join(parts)
