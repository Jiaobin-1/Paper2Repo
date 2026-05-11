from __future__ import annotations

from app.agents.state import PaperAnalysisState
from app.schemas.classification import PaperTypeClassification


def classify_paper_type_node(state: PaperAnalysisState) -> PaperAnalysisState:
    text = " ".join(
        [
            state["metadata"].title,
            state["metadata"].abstract,
            " ".join(state["metadata"].keywords),
            state["parsed_paper"].raw_text[:8000],
        ]
    ).lower()

    domain = "other"
    domain_reason = "No strong domain keyword was detected in title, abstract, keywords, or early paper text."
    if any(term in text for term in ["large language model", "llm", "instruction tuning"]):
        domain = "llm"
        domain_reason = "Detected LLM-related terms such as large language model, LLM, or instruction tuning."
    elif any(term in text for term in ["agent", "multi-agent", "tool use"]):
        domain = "agent"
        domain_reason = "Detected agent-related terms such as agent, multi-agent, or tool use."
    elif any(term in text for term in ["retrieval augmented", "rag", "retrieval"]):
        domain = "rag"
        domain_reason = "Detected retrieval/RAG-related terms such as retrieval augmented, RAG, or retrieval."
    elif any(term in text for term in ["language model", "nlp", "text classification"]):
        domain = "nlp"
        domain_reason = "Detected NLP-related terms such as language model, NLP, or text classification."
    elif any(term in text for term in ["image", "vision", "detection", "segmentation"]):
        domain = "cv"
        domain_reason = "Detected CV-related terms such as image, vision, detection, or segmentation."
    elif "recommend" in text:
        domain = "recommendation"
        domain_reason = "Detected recommendation-related terms."
    elif any(term in text for term in ["multimodal", "vision-language"]):
        domain = "multimodal"
        domain_reason = "Detected multimodal or vision-language terms."
    elif any(term in text for term in ["deep learning", "neural network", "transformer"]):
        domain = "deep_learning"
        domain_reason = "Detected deep-learning terms such as neural network or transformer."

    paper_type = "experimental"
    type_reason = "Detected experiment/evaluation-oriented wording, so the paper is treated as experimental by default."
    if any(term in text for term in ["survey", "review"]):
        paper_type = "survey"
        type_reason = "Detected survey/review wording."
    elif "benchmark" in text:
        paper_type = "benchmark"
        type_reason = "Detected benchmark-oriented wording."
    elif "dataset" in text and "we propose" in text:
        paper_type = "dataset"
        type_reason = "Detected dataset and proposal wording."
    elif any(term in text for term in ["system", "platform", "framework"]):
        paper_type = "system"
        type_reason = "Detected system/framework-oriented wording."
    elif any(term in text for term in ["theorem", "proof", "lemma"]):
        paper_type = "theoretical"
        type_reason = "Detected theorem/proof/lemma wording."

    reproduction_mode = "benchmark_evaluation"
    mode_reason = "Benchmark-style evaluation is a conservative default for experimental AI papers."
    if any(term in text for term in ["fine-tuning", "finetuning", "instruction tuning"]):
        reproduction_mode = "fine_tuning"
        mode_reason = "Detected fine-tuning or instruction-tuning wording."
    elif any(term in text for term in ["train from scratch", "pretraining", "pre-training"]):
        reproduction_mode = "training_from_scratch"
        mode_reason = "Detected training-from-scratch or pretraining wording."
    elif any(term in text for term in ["inference", "pipeline", "prompt"]):
        reproduction_mode = "inference_pipeline"
        mode_reason = "Detected inference/pipeline/prompt wording."
    elif "ablation" in text:
        reproduction_mode = "ablation_reproduction"
        mode_reason = "Detected ablation-oriented wording."
    if paper_type in {"survey", "theoretical"}:
        reproduction_mode = "not_recommended"
        mode_reason = "Survey/theoretical papers are not ideal for MVP engineering reproduction."

    difficulty = "medium"
    blockers: list[str] = []
    resources = ["Python environment", "paper PDF", "dataset access"]
    if any(term in text for term in ["billion", "large-scale", "distributed", "gpu cluster"]):
        difficulty = "very_high"
        blockers.append("Potential large-scale compute requirement")
        resources.append("GPU resources")
    elif any(term in text for term in ["fine-tuning", "transformer", "diffusion"]):
        difficulty = "high"
        resources.append("GPU resources")
    elif paper_type in {"benchmark", "dataset"}:
        difficulty = "medium"

    suitability = "good" if paper_type in {"experimental", "benchmark"} and difficulty != "very_high" else "partial"
    if paper_type in {"survey", "theoretical"}:
        suitability = "poor"
        blockers.append("Paper type is not ideal for MVP reproduction planning")

    classification = PaperTypeClassification(
        domain=domain,
        paper_type=paper_type,
        reproduction_mode=reproduction_mode,
        difficulty=difficulty,
        suitability_for_mvp=suitability,
        reasons=[
            domain_reason,
            type_reason,
            mode_reason,
        ],
        required_resources=resources,
        likely_blockers=blockers,
    )
    return {"classification": classification, "status": "classified"}
