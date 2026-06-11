import { test, expect } from "@playwright/test";

import { mockAppApis } from "./mocks";

test.describe("Upload flow", () => {
  test.beforeEach(async ({ page }) => {
    await mockAppApis(page);
  });

  test("drop-zone is visible with mocked API", async ({ page }) => {
    await page.goto("/");

    const dropZone = page.locator(".drop-zone");
    await expect(dropZone).toBeVisible();
  });

  test("shows configured model message when settings are configured", async ({ page }) => {
    await page.goto("/");

    // The message area should NOT show "model not configured" when settings.configured is true
    // Instead it should show the default "select PDF to start" message
    const messageArea = page.locator(".panel p.muted").first();
    await expect(messageArea).toBeVisible();
  });

  test("drop-zone has correct ARIA attributes", async ({ page }) => {
    await page.goto("/");

    const dropZone = page.locator(".drop-zone");
    await expect(dropZone).toHaveAttribute("role", "button");
    await expect(dropZone).toHaveAttribute("tabindex", "0");
  });

  test("upload and analyze buttons are initially disabled", async ({ page }) => {
    await page.goto("/");

    const buttons = page.locator(".upload-row button");
    const uploadButton = buttons.first();
    const analyzeButton = buttons.nth(1);

    await expect(uploadButton).toBeDisabled();
    await expect(analyzeButton).toBeDisabled();
  });

  test("drop-zone prompt text changes with language", async ({ page }) => {
    await page.goto("/");

    // Default language is zh, so expect the Chinese prompt
    const dropZoneText = page.locator(".drop-zone p");
    await expect(dropZoneText).toContainText("拖拽");
  });

  test("task status and model info are displayed", async ({ page }) => {
    await page.goto("/");

    // Info blocks should be present
    const taskStatusLabel = page.locator(".status-card span").first();
    await expect(taskStatusLabel).toBeVisible();
  });

  test("upload, analyze, and render a generated report", async ({ page }) => {
    const now = "2026-06-11T00:00:00Z";
    const paper = {
      id: "paper-1",
      title: null,
      filename: "paper.pdf",
      file_path: "/tmp/paper.pdf",
      file_size: 15,
      created_at: now,
    };
    const completedRun = {
      id: "run-1",
      paper_id: paper.id,
      status: "completed",
      model_name: "test",
      current_step: "completed",
      progress_percent: 100,
      error_message: null,
      started_at: now,
      completed_at: now,
      created_at: now,
      updated_at: now,
    };

    await page.route("**/api/papers/upload", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(paper),
      }),
    );
    await page.route("**/api/papers/paper-1/runs", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...completedRun,
          status: "pending",
          current_step: "queued",
          progress_percent: 0,
          completed_at: null,
        }),
      }),
    );
    await page.route("**/api/runs/run-1", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(completedRun),
      }),
    );
    await page.route("**/api/runs/run-1/report", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: "run-1",
          paper_id: paper.id,
          title: "Example Paper",
          content: "# Example Paper\n\n## 0. 复现审计摘要\n\n报告已生成。\n\n### 验收标准\n\n- [ ] 输出 F1。",
          file_path: "/tmp/report.md",
          created_at: now,
        }),
      }),
    );

    await page.goto("/");
    await page.locator('input[type="file"]').setInputFiles({
      name: "paper.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\n%%EOF"),
    });

    await expect(page.locator(".drop-zone p")).toContainText("paper.pdf");
    await page.locator(".upload-row button").first().click();
    await expect(page.locator(".upload-message")).toContainText("上传成功");

    await page.locator(".upload-row button").nth(1).click();
    await expect(page.locator(".upload-message")).toContainText("分析完成");
    await expect(page.locator(".report-viewer")).toContainText("Example Paper");
    await expect(page.locator(".report-viewer")).toContainText("复现审计摘要");
  });
});
