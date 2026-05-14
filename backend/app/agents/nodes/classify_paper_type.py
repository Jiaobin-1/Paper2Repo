from __future__ import annotations

import re

from app.agents.state import PaperAnalysisState
from app.schemas.classification import PaperType, PaperTypeClassification


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

    paper_types: set[PaperType] = set()
    domain_reasons = []

    if _any_word_match(["large language model", "llm", "instruction tuning"], text):
        paper_types.add("llm_application")
        domain_reasons.append("Detected LLM-related terms.")
    if _any_word_match(["agent", "multi-agent", "tool use"], text):
        paper_types.add("agent_or_tool_use")
        domain_reasons.append("Detected agent-related terms.")
    if _any_word_match(["retrieval augmented", "rag", "retrieval"], text):
        paper_types.add("rag_or_retrieval")
        domain_reasons.append("Detected RAG/retrieval-related terms.")
    if _any_word_match(["reinforcement learning", "rlhf", "ppo"], text):
        paper_types.add("reinforcement_learning")
        domain_reasons.append("Detected Reinforcement Learning terms.")
    if _any_word_match(["self-training", "self-evolution", "self-play"], text):
        paper_types.add("self_training_or_self_evolution")
        domain_reasons.append("Detected Self-training/Evolution terms.")
    if _any_word_match(["dataset", "benchmark"], text) and "we propose" in text:
        paper_types.add("dataset_or_benchmark_construction")
        domain_reasons.append("Detected Dataset/Benchmark compilation wording.")
    elif _word_match("benchmark", text):
        paper_types.add("benchmark_or_evaluation")
        domain_reasons.append("Detected Benchmark/Evaluation wording.")
    if _any_word_match(["system", "platform", "framework"], text):
        paper_types.add("system_or_framework")
        domain_reasons.append("Detected System/Framework-oriented wording.")
    if _any_word_match(["theorem", "proof", "lemma", "algorithm"], text):
        paper_types.add("algorithm_or_theory")
        domain_reasons.append("Detected Algorithm/Theory wording.")
    if _any_word_match(["multimodal", "vision-language", "vlm"], text):
        paper_types.add("multimodal")
        domain_reasons.append("Detected Multimodal terms.")
    if _any_word_match(["image", "vision", "detection", "segmentation", "language model", "nlp", "text classification"], text):
        paper_types.add("cv_or_nlp_classic")
        domain_reasons.append("Detected classic CV/NLP terms.")
    if _any_word_match(["supervised", "classification", "regression"], text):
        paper_types.add("supervised_learning")
        domain_reasons.append("Detected Supervised Learning terms.")

    if not paper_types:
        paper_types.add("supervised_learning")
        domain_reasons.append("Defaulting to Supervised Learning fallback.")

    blockers: list[str] = []
    resources = ["Python environment", "paper PDF", "dataset access"]
    if _any_word_match(["billion", "large-scale", "distributed", "gpu cluster"], text):
        blockers.append("Potential large-scale compute requirement")
        resources.append("GPU resources")
    elif _any_word_match(["fine-tuning", "transformer", "diffusion"], text):
        resources.append("GPU resources")

    classification = PaperTypeClassification(
        paper_types=list(paper_types),
        reasons=domain_reasons,
        required_resources=resources,
        likely_blockers=blockers,
    )
    return {"classification": classification, "status": "classified"}
