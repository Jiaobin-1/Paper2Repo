from __future__ import annotations

from app.schemas.classification import PaperTypeClassification
from app.schemas.experiments import ExperimentAnalysis
from app.schemas.metadata import PaperMetadata
from app.schemas.method import MethodAnalysis
from app.schemas.reproduction import ReproductionPlan
from app.schemas.understanding import PaperUnderstanding
from app.services.report_helpers import (
    _bullets,
    _cell,
    _checkboxes,
    _evidence_table,
    _experiment_matrix,
    _label,
    _missing_table,
    _reading_tasks,
    _value,
)
from app.services.report_lang import EN, ZH, Lang


def build_markdown_report(
    metadata: PaperMetadata,
    classification: PaperTypeClassification,
    understanding: PaperUnderstanding,
    method: MethodAnalysis,
    experiments: ExperimentAnalysis,
    reproduction: ReproductionPlan,
    language: str = "zh",
) -> str:
    lang = EN if language == "en" else ZH
    return _build_report(metadata, classification, understanding, method, experiments, reproduction, lang)


def _build_report(
    metadata: PaperMetadata,
    classification: PaperTypeClassification,
    understanding: PaperUnderstanding,
    method: MethodAnalysis,
    experiments: ExperimentAnalysis,
    reproduction: ReproductionPlan,
    lang: Lang,
) -> str:
    L = lang
    not_spec = L.m_not_specified

    modules = "\n".join(
        "\n".join([
            f"### {i}. {m.module_name}",
            f"**Section:** {m.paper_section}",
            f"- {L.m_responsibility}：{_value(m.responsibility, L)}",
            f"- Known Inputs：{', '.join(m.known_inputs) if m.known_inputs else not_spec}",
            f"- Inferred Inputs：{', '.join(m.inferred_inputs) if m.inferred_inputs else not_spec}",
            f"- Missing Inputs：{', '.join(m.missing_inputs) if m.missing_inputs else not_spec}",
            f"- Known Outputs：{', '.join(m.known_outputs) if m.known_outputs else not_spec}",
            f"- Inferred Outputs：{', '.join(m.inferred_outputs) if m.inferred_outputs else not_spec}",
            f"- Missing Outputs：{', '.join(m.missing_outputs) if m.missing_outputs else not_spec}",
            f"- Parameters：{'; '.join(m.key_parameters) if m.key_parameters else not_spec}",
            f"- {L.m_notes}：{'; '.join(m.implementation_notes) if m.implementation_notes else not_spec}",
            f"- Evidence：{m.evidence_quote} (Confidence: {m.confidence})",
        ])
        for i, m in enumerate(method.modules, start=1)
    ) or L.no_modules

    repro_modules = "\n".join(
        "\n".join([
            f"### {i}. {m.name}",
            f"- {L.rm_purpose}：{_value(m.purpose, L)}",
            f"- {L.m_inputs}：{', '.join(m.inputs) if m.inputs else not_spec}",
            f"- {L.m_outputs}：{', '.join(m.outputs) if m.outputs else not_spec}",
            f"- {L.rm_todos}：{'; '.join(m.todos) if m.todos else not_spec}",
        ])
        for i, m in enumerate(reproduction.required_modules, start=1)
    ) or L.no_repro_modules

    datasets = "\n".join(
        f"- **{d.name}**：{d.role or L.ds_role_default}；{L.ds_notes_label}：{d.notes or not_spec}"
        for d in experiments.datasets
    ) or L.no_datasets

    code_structure = "\n".join(
        f"- `{item.path}`（{_label(L.item_type_labels, item.type)}）：{item.purpose}；{L.cd_todo_label}：{item.todo}"
        for item in reproduction.code_structure
    ) or L.no_code

    steps = "\n".join(
        f"{s.step}. **{s.title}**：{s.description} {L.st_output_label}：{s.expected_output or not_spec}"
        for s in reproduction.implementation_steps
    ) or L.no_steps

    risks = "\n".join(
        f"- **{_label(L.level_labels, r.impact)}**：{r.risk}；{L.rk_mitigation_label}：{r.mitigation or not_spec}"
        for r in reproduction.risk_points
    ) or L.no_risks
    read_to_reproduce = _read_to_reproduce_table(understanding, method, experiments, reproduction, L)

    evidence_refs = [
        *understanding.evidence_refs,
        *method.evidence_refs,
        *experiments.evidence_refs,
        *reproduction.evidence_refs,
    ]
    formulas = _bullets(method.key_formulas, L)
    dependencies = _bullets(method.implementation_dependencies, L)
    checklist = _checkboxes([item.item for item in reproduction.experiment_checklist], L)
    acceptance = _checkboxes(reproduction.acceptance_criteria, L)
    difficulty_breakdown = "\n".join(
        [
            f"- {L.h_dependency_difficulty}：{_label(L.level_labels, reproduction.dependency_availability_difficulty)}",
            f"- {L.h_data_difficulty}：{_label(L.level_labels, reproduction.data_availability_difficulty)}",
            f"- {L.h_compute_difficulty}：{_label(L.level_labels, reproduction.compute_cost_difficulty)}",
            f"- {L.h_implementation_difficulty}：{_label(L.level_labels, reproduction.implementation_complexity_difficulty)}",
        ]
    )

    sep = "；" if L.lang_code == "zh" else "; "

    return f"""# {metadata.title}

{L.intro}

{L.h_audit}

- Full Reproduction Difficulty：{_label(L.level_labels, reproduction.full_reproduction_difficulty)}
- MVP Pipeline Feasibility：{_label(L.level_labels, reproduction.mvp_pipeline_feasibility)}
- Report Confidence：{_label(L.level_labels, reproduction.report_confidence)}
- {L.h_audit_summary}：{_value(reproduction.audit_summary or reproduction.feasibility_summary, L)}
- {L.h_first_step}：{_value(reproduction.recommended_first_experiment or reproduction.minimum_reproduction_goal, L)}
- {L.h_biggest_blocker}：{sep.join(item.item for item in reproduction.blocking_missing_items[:3]) if reproduction.blocking_missing_items else L.no_blockers}

{L.h_blocking_gaps}
{_missing_table(reproduction.blocking_missing_items, L)}

{L.h_read_to_reproduce}
{L.rr_intro}

{read_to_reproduce}

{L.h_evidence_map}
{_evidence_table(evidence_refs, L)}

{L.h_metadata}

- {L.h_title}：{metadata.title}
- {L.h_authors}：{", ".join(metadata.authors) if metadata.authors else L.no_value}
- Paper Types：{", ".join(classification.paper_types) if classification.paper_types else L.no_value}

{L.h_class_reasons}
{_bullets(classification.reasons, L)}
{L.h_resources}
{_bullets(classification.required_resources, L)}
{L.h_blockers}
{_bullets(classification.likely_blockers, L)}

{L.h_understanding}

{L.h_background}
{_value(understanding.background, L)}

{L.h_core_problem}
{_value(understanding.core_problem, L)}

{L.h_contributions}
{_bullets(understanding.main_contributions, L)}
{L.h_overall_idea}
{_value(understanding.overall_idea, L)}

{L.h_conclusion}
{_value(understanding.conclusion, L)}

{L.h_limitations}
{_bullets([f'[{limitation.limitation_type}] {limitation.description} (Evidence: {limitation.evidence_quote}, Confidence: {limitation.confidence})' for limitation in understanding.limitations], L)}
{L.h_scenarios}
{_bullets(understanding.applicable_scenarios, L)}

{L.h_assumptions}
{_bullets(understanding.key_assumptions, L)}
{L.h_reading_checklist}
{_reading_tasks(understanding, L)}
{L.h_understanding_gaps}
{_missing_table(understanding.missing_items, L)}

{L.h_method}

{L.h_framework}
{_value(method.system_framework or method.method_summary, L)}

{L.h_method_summary}
{_value(method.method_summary, L)}

{L.h_modules}
{modules}

{L.h_algorithm}
{_bullets([f"{s.step}. {s.name}: {s.description}" for s in method.algorithm_steps], L)}
{L.h_formulas}
{formulas}
{L.h_formula_gaps}
{_bullets(method.formula_or_pseudocode_gaps, L)}
{L.h_interfaces}
{_bullets(method.implementation_interfaces, L)}
{L.h_dependencies}
{dependencies}
{L.h_method_gaps}
{_missing_table(method.missing_items, L)}

{L.h_experiments}

{L.h_matrix}
{_experiment_matrix(experiments, L)}

{L.h_datasets}
{datasets}
{L.h_baselines}
{_bullets(experiments.baselines, L)}
{L.h_metrics}
{_bullets(experiments.metrics, L)}
{L.h_training}
{_bullets(experiments.training_details, L)}
{L.h_eval_protocol}
{_value(experiments.evaluation_protocol, L)}

{L.h_main_results}
{_bullets(experiments.main_results, L)}
{L.h_ablation}
{_bullets(experiments.ablation_studies, L)}
{L.h_experiment_gaps}
{_missing_table(experiments.missing_items, L)}

{L.h_plan}

{L.h_feasibility}
- Full Reproduction Difficulty：{_label(L.level_labels, reproduction.full_reproduction_difficulty)}
- MVP Pipeline Feasibility：{_label(L.level_labels, reproduction.mvp_pipeline_feasibility)}
- {L.h_feasibility_summary}：{_value(reproduction.feasibility_summary, L)}
{L.h_difficulty_breakdown}
{difficulty_breakdown}

{L.h_min_goal}
{_value(reproduction.minimum_reproduction_goal, L)}

{L.h_first_exp}
{_value(reproduction.recommended_first_experiment, L)}

{L.h_scope}
{_bullets(reproduction.reproduction_scope, L)}
{L.h_req_modules}
{repro_modules}

{L.h_dataset_plan}
{_bullets(reproduction.dataset_plan, L)}
{L.h_eval_plan}
{_bullets(reproduction.evaluation_plan, L)}

{L.h_code_skeleton}
{code_structure}

{L.h_impl_steps}
{steps}

{L.h_acceptance}
{acceptance}

{L.h_risks}
{risks}

{L.h_missing_info}
{_bullets(reproduction.missing_information, L)}
{L.h_simplifications}
{_bullets(reproduction.suggested_simplifications, L)}

{L.h_checklist}

{checklist}
"""


def _read_to_reproduce_table(
    understanding: PaperUnderstanding,
    method: MethodAnalysis,
    experiments: ExperimentAnalysis,
    reproduction: ReproductionPlan,
    lang: Lang,
) -> str:
    rows = [
        (
            lang.rr_core_question,
            _compact("; ".join([understanding.core_problem, *understanding.main_contributions[:2]]), lang),
            _compact("; ".join([
                reproduction.minimum_reproduction_goal,
                reproduction.recommended_first_experiment,
                *reproduction.reproduction_scope[:2],
            ]), lang),
        ),
        (
            lang.rr_method_contract,
            _compact("; ".join([
                method.system_framework or method.method_summary,
                _join_limited([module.module_name for module in method.modules], lang, 3),
            ]), lang),
            _compact("; ".join([
                _join_limited([module.name for module in reproduction.required_modules], lang, 3),
                _join_limited([item.path for item in reproduction.code_structure], lang, 4),
            ]), lang),
        ),
        (
            lang.rr_experiment_target,
            _compact("; ".join([
                _join_limited([dataset.name for dataset in experiments.datasets], lang, 3),
                _join_limited(experiments.metrics, lang, 4),
                experiments.evaluation_protocol,
            ]), lang),
            _compact("; ".join([
                _join_limited(reproduction.dataset_plan, lang, 2),
                _join_limited(reproduction.evaluation_plan, lang, 2),
                _join_limited(reproduction.acceptance_criteria, lang, 2),
            ]), lang),
        ),
        (
            lang.rr_risk_control,
            _compact("; ".join([
                _join_limited(understanding.key_assumptions, lang, 2),
                _join_limited([limitation.description for limitation in understanding.limitations], lang, 2),
                _join_limited([item.item for item in understanding.missing_items], lang, 2),
            ]), lang),
            _compact("; ".join([
                _join_limited([risk.risk for risk in reproduction.risk_points], lang, 2),
                _join_limited([item.item for item in reproduction.blocking_missing_items], lang, 2),
                _join_limited(reproduction.suggested_simplifications, lang, 2),
            ]), lang),
        ),
    ]
    header = (
        f"| {lang.rr_stage} | {lang.rr_understanding_signal} | {lang.rr_reproduction_decision} |\n"
        "| --- | --- | --- |"
    )
    body = "\n".join(f"| {_cell(stage)} | {_cell(signal)} | {_cell(decision)} |" for stage, signal, decision in rows)
    return f"{header}\n{body}\n"


def _join_limited(items: list[str], lang: Lang, limit: int) -> str:
    values = [item for item in items if item]
    if not values:
        return ""
    suffix = "" if len(values) <= limit else ("等" if lang.lang_code == "zh" else " and more")
    return ", ".join(values[:limit]) + suffix


def _compact(value: str, lang: Lang) -> str:
    compacted = " ".join(value.split())
    return compacted or lang.no_value
