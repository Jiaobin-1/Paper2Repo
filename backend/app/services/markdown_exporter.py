from __future__ import annotations

from app.schemas.classification import PaperTypeClassification
from app.schemas.experiments import ExperimentAnalysis
from app.schemas.metadata import PaperMetadata
from app.schemas.method import MethodAnalysis
from app.schemas.reproduction import ReproductionPlan
from app.schemas.understanding import PaperUnderstanding
from app.services.report_helpers import (
    _bullets,
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
            f"### {i}. {m.name}",
            f"- {L.m_responsibility}：{_value(m.responsibility, L)}",
            f"- {L.m_inputs}：{', '.join(m.inputs) if m.inputs else not_spec}",
            f"- {L.m_outputs}：{', '.join(m.outputs) if m.outputs else not_spec}",
            f"- {L.m_priority}：{_label(L.priority_labels, m.implementation_priority) if m.implementation_priority else not_spec}",
            f"- {L.m_contract}：{m.interface_contract or not_spec}",
            f"- {L.m_notes}：{'; '.join(m.implementation_notes) if m.implementation_notes else not_spec}",
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

    sep = "；" if L.lang_code == "zh" else "; "

    return f"""# {metadata.title}

{L.intro}

{L.h_audit}

- {L.h_repro_level}：{_label(L.level_labels, reproduction.feasibility_level)}
- {L.h_audit_summary}：{_value(reproduction.audit_summary or reproduction.feasibility_summary, L)}
- {L.h_first_step}：{_value(reproduction.recommended_first_experiment or reproduction.minimum_reproduction_goal, L)}
- {L.h_biggest_blocker}：{sep.join(item.item for item in reproduction.blocking_missing_items[:3]) if reproduction.blocking_missing_items else L.no_blockers}
- {L.h_confidence}：{_label(L.level_labels, reproduction.confidence)}

{L.h_blocking_gaps}
{_missing_table(reproduction.blocking_missing_items, L)}

{L.h_evidence_map}
{_evidence_table(evidence_refs, L)}

{L.h_metadata}

- {L.h_title}：{metadata.title}
- {L.h_authors}：{", ".join(metadata.authors) if metadata.authors else L.no_value}
- {L.h_domain}：{classification.domain}
- {L.h_paper_type}：{_label(L.paper_type_labels, classification.paper_type)}
- {L.h_repro_mode}：{_label(L.reproduction_mode_labels, classification.reproduction_mode)}
- {L.h_difficulty}：{_label(L.level_labels, classification.difficulty)}
- {L.h_mvp_suitability}：{_label(L.level_labels, classification.suitability_for_mvp)}

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
{_bullets(understanding.limitations, L)}
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
- {L.h_feasibility_level}：{_label(L.level_labels, reproduction.feasibility_level)}
- {L.h_feasibility_summary}：{_value(reproduction.feasibility_summary, L)}

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
