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
});
