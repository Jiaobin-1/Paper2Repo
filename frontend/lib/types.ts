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
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};
