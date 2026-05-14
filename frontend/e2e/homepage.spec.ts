import { test, expect } from "@playwright/test";

import { mockAppApis } from "./mocks";

test.describe("Homepage", () => {
  test.beforeEach(async ({ page }) => {
    await mockAppApis(page);
  });

  test("loads and displays the main heading", async ({ page }) => {
    await page.goto("/");

    const heading = page.locator("h1");
    await expect(heading).toHaveText("Paper2Repo");
  });

  test("displays the subtitle text", async ({ page }) => {
    await page.goto("/");

    const subtitle = page.locator("h1 + p.muted");
    await expect(subtitle).toBeVisible();
    // Default language is zh, so expect the Chinese subtitle
    await expect(subtitle).toContainText("AI");
  });

  test("displays the drop-zone upload area", async ({ page }) => {
    await page.goto("/");

    const dropZone = page.locator(".drop-zone");
    await expect(dropZone).toBeVisible();
    await expect(dropZone).toHaveAttribute("role", "button");
  });

  test("displays the workflow strip with five steps", async ({ page }) => {
    await page.goto("/");

    const workflowStrip = page.locator(".workflow-strip");
    await expect(workflowStrip).toBeVisible();

    const steps = workflowStrip.locator("span");
    await expect(steps).toHaveCount(5);
  });

  test("displays the upload and analyze buttons", async ({ page }) => {
    await page.goto("/");

    const uploadButton = page.locator(".upload-row button").first();
    await expect(uploadButton).toBeVisible();

    const analyzeButton = page.locator(".upload-row button").nth(1);
    await expect(analyzeButton).toBeVisible();
  });

  test("displays the settings link", async ({ page }) => {
    await page.goto("/");

    const settingsLink = page.locator('a[href="/settings"]');
    await expect(settingsLink).toBeVisible();
  });

  test("displays feature panels", async ({ page }) => {
    await page.goto("/");

    const panels = page.locator(".grid .panel");
    await expect(panels).toHaveCount(2);
  });
});
