import type { Page } from "@playwright/test";

export const mockSettings = {
  configured: true,
  base_url: "https://api.openai.com/v1",
  default_model: "test",
  available_models: ["test", "gpt-4o"],
  timeout_seconds: 60,
  ui_language: "zh",
  report_language: "en",
  theme: "light",
};

export const mockQueueStatus = {
  max_workers: 3,
  max_queued_jobs: 20,
  capacity: 23,
  active_submissions: 0,
  running_submissions: 0,
  queued_submissions: 0,
  available_slots: 23,
  is_full: false,
  retry_after_seconds: 5,
  pending_runs: 0,
  running_runs: 0,
};

export const mockStorageSummary = {
  uploads: { path: "/tmp/uploads", file_count: 0, byte_count: 0 },
  reports: { path: "/tmp/reports", file_count: 0, byte_count: 0 },
  database: { path: "/tmp/paper2repo.db", file_count: 0, byte_count: 0 },
  total_bytes: 0,
  orphan_file_count: 0,
  orphan_bytes: 0,
  cleanup_min_age_hours: 24,
  cleanup_candidates: [],
};

export async function mockAppApis(page: Page) {
  await page.route("**/api/settings", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockSettings),
    }),
  );

  await page.route("**/api/runs/queue", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockQueueStatus),
    }),
  );

  await page.route("**/api/runs**", (route) => {
    if (route.request().url().includes("/api/runs/queue")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQueueStatus),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/api/storage/summary", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockStorageSummary),
    }),
  );

  await page.route("**/api/storage/cleanup**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        dry_run: false,
        deleted_file_count: 0,
        deleted_bytes: 0,
        skipped_file_count: 0,
        candidates: [],
      }),
    }),
  );

  await page.route("**/api/llm/check", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        configured: true,
        ok: true,
        base_url: mockSettings.base_url,
        model: mockSettings.default_model,
        timeout_seconds: mockSettings.timeout_seconds,
        latency_ms: 12,
        error: null,
      }),
    }),
  );
}
