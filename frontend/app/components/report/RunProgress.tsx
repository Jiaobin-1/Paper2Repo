import { displayProgressPercent, formatStepLabel, getStepStates, WORKFLOW_STEPS } from "../../../lib/runPresentation";
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
          <h3>{text(language, "progressTitle")}</h3>
          <p className="muted">
            {text(language, "currentStep")}：{formatStepLabel(run.current_step, language)}
          </p>
        </div>
        <strong>{progress}%</strong>
      </div>
      <div className="progress-track" aria-label={text(language, "progressAria")}>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <ol className="stepper">
        {WORKFLOW_STEPS.map((step, index) => {
          const state = stepStates[index];
          return (
            <li key={step.key} className={state === "pending" ? "" : state}>
              <span>{stepMarker(state, index)}</span>
              <strong>{step.label[language]}</strong>
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
