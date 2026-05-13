export type Paper = {
  id: string;
  title: string | null;
  filename: string;
  file_path: string;
  file_size: number;
  created_at: string;
};

export type Run = {
  id: string;
  paper_id: string;
  status: string;
  model_name: string | null;
  current_step: string | null;
  progress_percent: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type RunListItem = Run & {
  paper_title: string | null;
  paper_filename: string;
};

export type LlmConfig = {
  configured: boolean;
  base_url: string;
  default_model: string;
  available_models: string[];
};

export type LanguageCode = "zh" | "en";

export type AppSettings = LlmConfig & {
  ui_language: LanguageCode;
  report_language: LanguageCode;
};

export type AppSettingsUpdate = {
  default_model?: string;
  ui_language?: LanguageCode;
  report_language?: LanguageCode;
};

export type Report = {
  run_id: string;
  paper_id: string;
  title: string;
  content: string;
  file_path: string | null;
  created_at: string | null;
};

export type QaMessage = {
  id: string;
  run_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type ComparisonRun = {
  run_id: string;
  paper_id: string;
  paper_title: string | null;
  paper_filename: string | null;
  model_name: string | null;
  created_at: string;
  report_title: string | null;
  report_content: string | null;
  metadata: {
    title?: string;
    authors?: string[];
    venue?: string;
    year?: string;
    keywords?: string[];
  };
  understanding: {
    background?: string;
    core_problem?: string;
    main_contributions?: string[];
    overall_idea?: string;
  };
  method: {
    method_name?: string;
    pipeline_overview?: string;
    key_innovations?: string[];
    architecture?: string;
    loss_functions?: string[];
    training_strategy?: string;
  };
  experiments: {
    datasets?: string[];
    metrics?: string[];
    baselines?: string[];
    main_results?: string[];
  };
  reproduction: {
    reproduction_goal?: string;
    estimated_effort?: string;
    risks?: string[];
    checklist?: string[];
  };
};

export type AvailableRun = {
  run_id: string;
  paper_id: string;
  paper_title: string | null;
  paper_filename: string | null;
  model_name: string | null;
  created_at: string;
};

export type PwcLink = {
  label: string;
  url: string;
  type: "paper" | "method" | "keyword" | "contribution";
};

export type KnowledgeSearchResult = {
  paper_id: string;
  paper_title: string | null;
  chunk_content: string;
  section_title: string | null;
  page_start: number;
  score: number;
};

export type KnowledgePaper = {
  paper_id: string;
  title: string | null;
  filename: string;
  chunk_count: number;
  created_at: string;
};

export type ArxivVersion = {
  version: string;
  date: string;
};

export type ArxivInfo = {
  arxiv_id: string;
  title: string;
  versions: ArxivVersion[];
};
