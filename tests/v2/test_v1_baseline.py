from pathlib import Path


def test_v1_behavioral_invariants_doc_exists_and_has_required_sections() -> None:
    doc_path = Path("v2/docs/v1_behavioral_invariants.md")
    assert doc_path.exists(), "Missing file: v2/docs/v1_behavioral_invariants.md"

    doc = doc_path.read_text(encoding="utf-8")

    required_sections = [
        "## State Transitions",
        "## CoSTEER Loop",
        "## Lifecycle Management",
        "## Checkpoint Semantics",
        "## Exploration Strategy (DAG Scheduling)",
        "## Guardrails",
        "## Error Recovery",
    ]
    missing = [s for s in required_sections if s not in doc]
    assert not missing, f"Missing sections: {missing}"


def test_v1_behavioral_invariants_doc_has_key_state_names_and_guardrail_marker() -> None:
    doc = Path("v2/docs/v1_behavioral_invariants.md").read_text(encoding="utf-8")
    assert "PROPOSING" in doc and "FEEDBACK" in doc and "COMPLETED" in doc, "Missing key state names"
    assert "REAL_PROVIDER_SAFE_PROFILE" in doc, "Missing guardrails marker"
