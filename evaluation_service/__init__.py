"""Evaluation Service package."""

from .service import EvaluationService, EvaluationServiceConfig
from .stratified_splitter import StratifiedSplitter

__all__ = [
    "EvaluationService",
    "EvaluationServiceConfig",
    "StratifiedSplitter",
]

# DeepEval bridge and custom metrics (optional — requires `pip install -e ".[eval]"`)
try:
    from evaluation_service.custom_metrics.code_quality import create_code_correctness_metric
    from evaluation_service.custom_metrics.costeer_efficiency import (
        CoSTEEREfficiencyResult,
        CoSTEERRound,
        CoSTEERTrace,
        compute_costeer_efficiency,
    )
    from evaluation_service.custom_metrics.proposal_quality import (
        create_feasibility_metric,
        create_specificity_metric,
    )
    from evaluation_service.custom_metrics.report_quality import (
        create_report_coherence_metric,
        create_report_depth_metric,
        create_report_faithfulness_metric,
    )
    from evaluation_service.deepeval_bridge import (
        costeer_round_to_test_case,
        golden_task_to_test_case,
        proposal_to_test_case,
        report_to_test_case,
    )

    __all__ += [
        "CoSTEEREfficiencyResult",
        "CoSTEERRound",
        "CoSTEERTrace",
        "compute_costeer_efficiency",
        "costeer_round_to_test_case",
        "create_code_correctness_metric",
        "create_feasibility_metric",
        "create_report_coherence_metric",
        "create_report_depth_metric",
        "create_report_faithfulness_metric",
        "create_specificity_metric",
        "golden_task_to_test_case",
        "proposal_to_test_case",
        "report_to_test_case",
    ]
except ImportError:
    pass
