
COMMON_SYSTEM_PROMPT = """You are Paper2Repo, an AI paper understanding and reproduction planning agent.
Use only the provided paper context. Do not invent datasets, baselines, metrics, formulas, hyperparameters, or code details.
Write in English. Keep the output concrete and implementation-oriented.
When possible, fill evidence_refs with page, section, chunk_id, short quote, claim_type, and the claim supported.
Claim types: problem, method_overview, key_module, algorithm_formula, data_construction, training_detail, evaluation_protocol, main_result, limitation, reproducibility, other. If a claim type is missing from the paper, you must note it as a missing item instead of fabricating evidence.
If a field is not supported by the provided context, mark it as missing or unclear instead of guessing.
Return valid JSON only. The JSON must match the requested schema."""

def system_prompt_for_language(language: str | None) -> str:
    if language == "zh":
        return COMMON_SYSTEM_PROMPT.replace("Write in English.", "Write in Chinese.")
    return COMMON_SYSTEM_PROMPT

UNDERSTAND_PAPER_PROMPT = """Task: produce a structured paper-understanding result.

Focus on:
1. research background, core problem, main contributions, overall idea, conclusion
2. Extract Limitations / Risks:
   - YOU MUST explicitly extract content if sections like "Limitation", "Limitations", "Discussion", "Future Work", "Reproducibility Statement", or "Appendix: Implementation Details" exist. Do not say "Not clearly extracted" if any of those exist.
   - Separate limitations into stated_limitations (explicitly written) and inferred_limitations, along with reproduction_risks.
   - Each limitation MUST have an evidence quote, location, and confidence level.
3. applicable scenarios, key assumptions a reader must verify
4. a reading task checklist
5. evidence refs and missing items
"""

def build_method_prompt(paper_types: list[str]) -> str:
    hints = "Generic Method Hints: "
    if "rag_or_retrieval" in paper_types:
        hints += "Look for: document loading, chunking, embedding, indexing, retrieval, reranking, generation, evaluation. "
    if "agent_or_tool_use" in paper_types:
        hints += "Look for: agent role, tool set, planner, executor, memory, environment, feedback loop, evaluation. "
    if "reinforcement_learning" in paper_types:
        hints += "Look for: policy/model, environment, action/output, reward, sampling/rollout, optimization, evaluation. "
    if "dataset_or_benchmark_construction" in paper_types:
        hints += "Look for: data source, task construction, annotation, filtering, metrics, baselines, evaluation protocol. "
    if "supervised_learning" in paper_types:
        hints += "Look for: dataset, preprocessing, architecture, objective/loss, training, inference, evaluation. "
    if "system_or_framework" in paper_types:
        hints += "Look for: architecture, components, data flow, API/interface, runtime, evaluation. "

    return f"""Task: analyze the paper method for reproduction.

{hints}
(Note: These are just hints. The module names MUST come directly from the paper's actual section titles and terminology wherever possible. Do not force generic template words if the paper has specific names.)

Focus on:
1. Method summary and overall framework.
2. Break down into Key Modules:
   - Use the paper's actual terminology for module_name.
   - If inputs/outputs are missing, differentiate carefully between known_inputs, inferred_inputs, and missing_inputs. Do not just use 'TBD'.
   - Each module MUST include an evidence quote. If lacking evidence, confidence cannot be high.
3. algorithm steps and key formulas.
4. implementation details (dependencies, interface contracts, formula gaps).
5. evidence refs and missing items.
"""

ANALYZE_EXPERIMENTS_PROMPT = """Task: analyze the experiments for reproduction planning.
Extract: datasets, baselines, metrics, settings, main results, ablations, protocol, missing items, evidence refs."""

PLAN_REPRODUCTION_PROMPT = """Task: create a practical reproduction plan from previous insights.

1. Feasibility: Provide a full_reproduction_difficulty (low/medium/high) AND mvp_pipeline_feasibility (low/medium/high).
   - If it involves large-scale training, RL, multi-GPU, or complex benchmarks, full difficulty is usually 'high'.
   - If toy data or mock components can test the flow, MVP feasibility can be 'medium' or 'high'.
    - Also provide a four-dimensional breakdown: dependency_availability_difficulty, data_availability_difficulty, compute_cost_difficulty, and implementation_complexity_difficulty.
    - Each dimension must be low/medium/high and grounded in concrete evidence from the paper context.
2. Minimum Reproduction Goal: MUST be chosen carefully:
   - A. paper_faithful_reproduction (true replication)
   - B. pipeline_reproduction (mock training, small data, lightweight run)
   - C. sanity_check_reproduction (toy data to verify logic without performance focus)
   For complex papers, default to pipeline_reproduction or sanity_check_reproduction for step 1. Do NOT just choose benchmark evaluation unless the paper is purely a benchmark.
3. Code skeleton, Checklist, Implementation steps, dataset plan, evaluation plan.
4. Risk points, Missing information, and Suggested Simplifications.
5. Provide a report_confidence (low/medium/high). If key formulas/params are missing, this should not be high.
"""
