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

export async function mockAppApis(page: Page) {
  await page.route("**/api/settings", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockSettings),
    }),
  );

  await page.route("**/api/runs**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
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
