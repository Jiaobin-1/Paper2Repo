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
  timeout_seconds: number;
};

export type LlmCheck = {
  configured: boolean;
  ok: boolean;
  base_url: string;
  model: string;
  timeout_seconds: number;
  latency_ms: number | null;
  error: string | null;
};

export type LanguageCode = "zh" | "en";

export type ThemeMode = "light" | "dark" | "system";

export type AppSettings = LlmConfig & {
  ui_language: LanguageCode;
  report_language: LanguageCode;
  theme: ThemeMode;
};

export type AppSettingsUpdate = {
  default_model?: string;
  ui_language?: LanguageCode;
  report_language?: LanguageCode;
  theme?: ThemeMode;
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
  chunk_index: number;
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

export type CitationInfo = {
  citation_index: number;
  authors: string;
  title: string;
  venue: string;
  year: string;
  doi: string;
  raw_text: string;
};

export type CitationEdge = {
  source_paper_id: string;
  target_paper_id: string;
  source_title: string;
  target_title: string;
  cited_title: string;
  similarity: number;
};

export type BatchUploadResponse = {
  papers: Paper[];
};

export type BatchStartResponse = {
  batch_id: string;
  runs: Run[];
};

export type BatchStatusResponse = {
  batch_id: string;
  runs: RunListItem[];
};

export type QueueStatus = {
  max_workers: number;
  max_queued_jobs: number;
  capacity: number;
  active_submissions: number;
  running_submissions: number;
  queued_submissions: number;
  available_slots: number;
  is_full: boolean;
  retry_after_seconds: number;
  pending_runs: number;
  running_runs: number;
};

export type LlmUsageEvent = {
  model: string;
  mode: string;
  operation: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  latency_ms: number;
  attempts: number;
  created_at: string;
};

export type LlmUsageSummary = {
  run_id: string;
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  latency_ms: number;
  cost_estimation_configured: boolean;
  events: LlmUsageEvent[];
};

export type StorageAreaSummary = {
  path: string;
  file_count: number;
  byte_count: number;
};

export type StorageCleanupCandidate = {
  area: string;
  path: string;
  byte_count: number;
  age_hours: number;
  reason: string;
};

export type StorageSummary = {
  uploads: StorageAreaSummary;
  reports: StorageAreaSummary;
  database: StorageAreaSummary;
  total_bytes: number;
  orphan_file_count: number;
  orphan_bytes: number;
  cleanup_min_age_hours: number;
  cleanup_candidates: StorageCleanupCandidate[];
};

export type StorageCleanupResult = {
  dry_run: boolean;
  deleted_file_count: number;
  deleted_bytes: number;
  skipped_file_count: number;
  candidates: StorageCleanupCandidate[];
};
