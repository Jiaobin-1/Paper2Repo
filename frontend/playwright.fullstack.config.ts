import { defineConfig } from "@playwright/test";

const runtimeRoot = `/tmp/paper2repo-e2e-${process.pid}`;
const backendCommand = process.env.FULLSTACK_BACKEND_COMMAND ?? "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "fullstack.spec.ts",
  timeout: 60000,
  use: {
    baseURL: "http://localhost:3000",
  },
  webServer: [
    {
      command: `cd ../backend && ${backendCommand}`,
      port: 8000,
      reuseExistingServer: false,
      timeout: 120000,
      env: {
        DATABASE_URL: `sqlite:///${runtimeRoot}/paper2repo.db`,
        UPLOAD_DIR: `${runtimeRoot}/uploads`,
        REPORT_DIR: `${runtimeRoot}/reports`,
        OPENAI_API_KEY: "",
        OPENAI_MODEL: "test-model",
        OPENAI_MODEL_OPTIONS: "test-model",
      },
    },
    {
      command: "npm run dev",
      port: 3000,
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});
