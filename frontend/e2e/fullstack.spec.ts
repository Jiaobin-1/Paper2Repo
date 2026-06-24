import path from "node:path";

import { expect, test } from "@playwright/test";

test.skip(process.env.FULLSTACK_E2E !== "1", "Runs only when the real backend is enabled.");

test("uploads a real PDF and renders the generated report", async ({ page }) => {
  test.setTimeout(60000);
  await page.goto("/");

  const fixture = path.resolve(process.cwd(), "../backend/tests/fixtures/sample.pdf");
  await page.locator('input[type="file"]').setInputFiles(fixture);

  const uploadButton = page.locator(".upload-row button").first();
  const analyzeButton = page.locator(".upload-row button").nth(1);
  await uploadButton.click();
  await expect(page.locator(".sub-panel")).toContainText("sample.pdf");
  await expect(analyzeButton).toBeEnabled();

  await analyzeButton.click();
  await expect(page.locator(".report-viewer")).toBeVisible({ timeout: 45000 });
  await expect(page.locator(".report-viewer .markdown-body h1")).toBeVisible();
});
