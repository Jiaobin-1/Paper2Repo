from app.api.routes_compare import _extract_method_summary, _extract_reproduction_summary
from app.api.routes_pwc import _primary_method_name


def test_compare_summaries_use_current_analysis_schema():
    method = _extract_method_summary(
        {
            "method_summary": "A compact method summary.",
            "modules": [{"module_name": "Encoder"}, {"module_name": "Decoder"}],
            "key_formulas": ["L = L_task + L_reg"],
            "system_framework": "Two-stage system",
        }
    )
    reproduction = _extract_reproduction_summary(
        {
            "minimum_reproduction_goal": "pipeline_reproduction",
            "full_reproduction_difficulty": "high",
            "mvp_pipeline_feasibility": "medium",
            "risk_points": [{"risk": "Missing data", "impact": "high", "mitigation": "Use proxy data"}],
            "experiment_checklist": [{"item": "Run baseline", "done": False}],
        }
    )

    assert method.module_names == ["Encoder", "Decoder"]
    assert method.pipeline_overview == method.method_summary
    assert reproduction.reproduction_goal == "pipeline_reproduction"
    assert reproduction.risks == ["Missing data"]
    assert reproduction.checklist == ["Run baseline"]


def test_pwc_method_name_prefers_current_module_schema_with_legacy_fallback():
    assert _primary_method_name({"modules": [{"module_name": "Graph Encoder"}]}) == "Graph Encoder"
    assert _primary_method_name({"method_name": "Legacy Method"}) == "Legacy Method"
