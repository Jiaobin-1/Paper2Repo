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

export type Report = {
  run_id: string;
  paper_id: string;
  title: string;
  content: string;
  file_path: string | null;
  created_at: string | null;
};
