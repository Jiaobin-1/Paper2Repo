import { displayProgressPercent, formatRunTiming, formatStepLabel, getStepStates, WORKFLOW_STEPS } from "../../../lib/runPresentation";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import { text } from "../../../lib/i18n";
import type { Run } from "../../../lib/types";

export function WorkflowProgress({ run }: { run: Run }) {
  const language = useAppLanguage();
  const progress = displayProgressPercent(run);
  const stepStates = getStepStates(run);

  return (
    <section className="progress-panel">
      <div className="progress-header">
        <div>
          <h3>{text(language, "workflowTimeline")}</h3>
          <p className="muted">
            {text(language, "currentStep")}：{formatStepLabel(run.current_step, language)}
          </p>
          <p className="muted">{formatRunTiming(run, language)}</p>
        </div>
        <strong>{progress}%</strong>
      </div>
      <div className="progress-track" aria-label={text(language, "progressAria")}>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <ol className="workflow-timeline">
        {WORKFLOW_STEPS.map((step, index) => {
          const state = stepStates[index];
          return (
            <li key={step.key} className={state === "pending" ? "" : state}>
              <span>{stepMarker(state, index)}</span>
              <div>
                <strong>{step.label[language]}</strong>
                <small>{stepStateLabel(state, language)}</small>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function stepMarker(state: string, index: number): string | number {
  if (state === "done") return "✓";
  if (state === "failed") return "!";
  return index + 1;
}

function stepStateLabel(state: string, language: "zh" | "en"): string {
  if (state === "done") return language === "en" ? "Done" : "已完成";
  if (state === "active") return language === "en" ? "Running" : "执行中";
  if (state === "failed") return language === "en" ? "Failed" : "失败";
  return language === "en" ? "Pending" : "等待";
}
