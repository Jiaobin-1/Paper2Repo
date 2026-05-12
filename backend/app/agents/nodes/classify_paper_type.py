from __future__ import annotations

import re

from app.agents.state import PaperAnalysisState
from app.schemas.classification import PaperTypeClassification


def _word_match(term: str, text: str) -> bool:
    return bool(re.search(r'\b' + re.escape(term) + r'\b', text))


def _any_word_match(terms: list[str], text: str) -> bool:
    return any(_word_match(term, text) for term in terms)


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
    if _any_word_match(["large language model", "llm", "instruction tuning"], text):
        domain = "llm"
        domain_reason = "Detected LLM-related terms such as large language model, LLM, or instruction tuning."
    elif _any_word_match(["agent", "multi-agent", "tool use"], text):
        domain = "agent"
        domain_reason = "Detected agent-related terms such as agent, multi-agent, or tool use."
    elif _any_word_match(["retrieval augmented", "rag", "retrieval"], text):
        domain = "rag"
        domain_reason = "Detected retrieval/RAG-related terms such as retrieval augmented, RAG, or retrieval."
    elif _any_word_match(["language model", "nlp", "text classification"], text):
        domain = "nlp"
        domain_reason = "Detected NLP-related terms such as language model, NLP, or text classification."
    elif _any_word_match(["image", "vision", "detection", "segmentation"], text):
        domain = "cv"
        domain_reason = "Detected CV-related terms such as image, vision, detection, or segmentation."
    elif _word_match("recommend", text):
        domain = "recommendation"
        domain_reason = "Detected recommendation-related terms."
    elif _any_word_match(["multimodal", "vision-language"], text):
        domain = "multimodal"
        domain_reason = "Detected multimodal or vision-language terms."
    elif _any_word_match(["deep learning", "neural network", "transformer"], text):
        domain = "deep_learning"
        domain_reason = "Detected deep-learning terms such as neural network or transformer."

    paper_type = "experimental"
    type_reason = "Detected experiment/evaluation-oriented wording, so the paper is treated as experimental by default."
    if _any_word_match(["survey", "review"], text):
        paper_type = "survey"
        type_reason = "Detected survey/review wording."
    elif _word_match("benchmark", text):
        paper_type = "benchmark"
        type_reason = "Detected benchmark-oriented wording."
    elif _word_match("dataset", text) and "we propose" in text:
        paper_type = "dataset"
        type_reason = "Detected dataset and proposal wording."
    elif _any_word_match(["system", "platform", "framework"], text):
        paper_type = "system"
        type_reason = "Detected system/framework-oriented wording."
    elif _any_word_match(["theorem", "proof", "lemma"], text):
        paper_type = "theoretical"
        type_reason = "Detected theorem/proof/lemma wording."

    reproduction_mode = "benchmark_evaluation"
    mode_reason = "Benchmark-style evaluation is a conservative default for experimental AI papers."
    if _any_word_match(["fine-tuning", "finetuning", "instruction tuning"], text):
        reproduction_mode = "fine_tuning"
        mode_reason = "Detected fine-tuning or instruction-tuning wording."
    elif _any_word_match(["train from scratch", "pretraining", "pre-training"], text):
        reproduction_mode = "training_from_scratch"
        mode_reason = "Detected training-from-scratch or pretraining wording."
    elif _word_match("ablation", text):
        reproduction_mode = "ablation_reproduction"
        mode_reason = "Detected ablation-oriented wording."
    elif _any_word_match(["inference", "pipeline", "prompt"], text):
        reproduction_mode = "inference_pipeline"
        mode_reason = "Detected inference/pipeline/prompt wording."
    if paper_type in {"survey", "theoretical"}:
        reproduction_mode = "not_recommended"
        mode_reason = "Survey/theoretical papers are not ideal for MVP engineering reproduction."

    difficulty = "medium"
    blockers: list[str] = []
    resources = ["Python environment", "paper PDF", "dataset access"]
    if _any_word_match(["billion", "large-scale", "distributed", "gpu cluster"], text):
        difficulty = "very_high"
        blockers.append("Potential large-scale compute requirement")
        resources.append("GPU resources")
    elif _any_word_match(["fine-tuning", "transformer", "diffusion"], text):
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
