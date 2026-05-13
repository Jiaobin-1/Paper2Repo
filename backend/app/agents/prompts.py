COMMON_SYSTEM_PROMPT = """You are Paper2Repo, an AI paper understanding and reproduction planning agent.
Use only the provided paper context. Do not invent datasets, baselines, metrics, formulas, hyperparameters, or code details.
Write in English. Keep the output concrete and implementation-oriented.
When possible, fill evidence_refs with page, section, short quote, role, and the claim supported by that quote.
If a field is not supported by the provided context, mark it as missing or unclear instead of guessing.
Return valid JSON only. The JSON must match the requested schema."""


def system_prompt_for_language(language: str | None) -> str:
    if language == "zh":
        return COMMON_SYSTEM_PROMPT.replace("Write in English.", "Write in Chinese.")
    return COMMON_SYSTEM_PROMPT


UNDERSTAND_PAPER_PROMPT = """Task: produce a structured paper-understanding result.

Focus on:
1. research background
2. core problem
3. main contributions
4. overall idea
5. conclusion
6. limitations
7. applicable scenarios
8. key assumptions a reader must verify
9. a reading task checklist covering problem, hypothesis, contribution evidence, and limitations
10. evidence refs and missing items

Avoid generic summaries. Tie claims to the provided abstract, introduction, and conclusion context.
For reading_tasks, use status values like confirmed, unclear, or missing."""


ANALYZE_METHOD_PROMPT = """Task: analyze the paper method for reproduction.

Focus on:
1. method summary and overall framework
2. key modules
3. each module's inputs and outputs
4. algorithm steps
5. key formulas if visible in the context
6. implementation dependencies and notes
7. implementation interfaces/contracts between modules
8. formula or pseudocode gaps that would block faithful reproduction
9. evidence refs and method missing items

If a detail is missing, say it is missing instead of guessing."""


ANALYZE_EXPERIMENTS_PROMPT = """Task: analyze the experiments for reproduction planning.

Focus on:
1. datasets
2. baselines
3. metrics
4. experiment settings
5. main results
6. ablation studies
7. training or evaluation protocol
8. a reproduction matrix with target, dataset, baseline, metric, protocol, reported result, reproducibility status, and missing items
9. evidence refs and experiment missing items

Extract concrete names and settings from the context. If the context does not contain a field, mark it as not found."""


PLAN_REPRODUCTION_PROMPT = """Task: create a practical reproduction plan from the paper understanding, method analysis, and experiment analysis.

The plan must include:
1. feasibility level and summary
2. minimum reproduction goal
3. necessary modules
4. dataset plan
5. evaluation plan
6. code directory skeleton
7. implementation steps
8. experiment checklist
9. risk points
10. missing information
11. simplifications for a local MVP
12. reproduction audit summary
13. recommended first experiment
14. blocking missing items
15. acceptance criteria
16. confidence level

Do not generate a complete repository. Only generate a directory skeleton and TODO-oriented engineering plan.
Prioritize the smallest experiment that can prove the method pipeline is correctly understood."""
