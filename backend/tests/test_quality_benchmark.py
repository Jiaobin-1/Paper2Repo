from app.services.quality_benchmark import evaluate_analysis_quality
from app.services.report_quality import build_report_quality_appendix, evaluate_report_quality_signals


class ModelValue:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self):
        return self.payload


class CountValue:
    def __init__(self, **values):
        self.__dict__.update(values)


def test_quality_score_rewards_expected_content_and_evidence():
    state = {
        "metadata": ModelValue({"title": "Sample AI Paper"}),
        "understanding": ModelValue({"evidence_refs": [{"page": "p.1"}]}),
        "method_analysis": ModelValue({"evidence_refs": [{"page": "p.1"}]}),
        "experiment_analysis": ModelValue(
            {"datasets": [{"name": "SampleBench"}], "evidence_refs": [{"page": "p.1"}]}
        ),
        "reproduction_plan": ModelValue({"evidence_refs": [{"page": "p.1"}]}),
        "chunked_paper": CountValue(chunk_count=2),
        "parsed_paper": CountValue(page_count=1, ocr_page_count=0, table_count=1, formula_count=1),
        "markdown_report": CountValue(content="Evidence SampleBench reproduction " * 100),
    }
    expectations = {
        "expected_title_terms": ["Sample", "AI", "Paper"],
        "expected_dataset_terms": ["SampleBench"],
        "required_report_terms": ["Evidence", "reproduction"],
        "minimum_evidence_refs": 4,
        "minimum_chunks": 1,
        "minimum_report_chars": 100,
        "minimum_score": 0.8,
    }

    result = evaluate_analysis_quality(state, expectations)

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["observations"]["table_count"] == 1
    assert result["components"]["quality_signals"] == 1.0


def test_report_quality_appendix_flags_low_confidence_and_missing_evidence():
    state = {
        "understanding": ModelValue({"evidence_refs": [], "limitations": [{"confidence": "low"}]}),
        "method_analysis": ModelValue({"evidence_refs": [{"page": "p.1"}], "modules": [{"confidence": "low"}]}),
        "experiment_analysis": ModelValue({"evidence_refs": []}),
        "reproduction_plan": ModelValue({"evidence_refs": [{"page": "p.2"}], "blocking_missing_items": [{"item": "data"}]}),
        "parsed_paper": CountValue(page_count=1),
        "node_errors": [{"node": "analyze_experiments_node", "error": "temporary"}],
    }

    signals = evaluate_report_quality_signals(state, "该模块来自方法相关片段的关键词抽取")
    appendix = build_report_quality_appendix(state, "该模块来自方法相关片段的关键词抽取", "zh")

    assert signals["evidence_sections"] == 2
    assert signals["low_confidence_items"] == 2
    assert signals["fallback_phrase_count"] == 1
    assert "报告质量信号" in appendix
    assert "模板化 fallback 信号：1" in appendix
