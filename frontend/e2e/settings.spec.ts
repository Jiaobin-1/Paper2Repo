import { test, expect } from "@playwright/test";

import { mockAppApis } from "./mocks";

test.describe("Settings page", () => {
  test.beforeEach(async ({ page }) => {
    await mockAppApis(page);
  });

  test("loads and displays the settings heading", async ({ page }) => {
    await page.goto("/settings");

    const heading = page.locator("h1");
    await expect(heading).toBeVisible();
    // Default UI language is zh
    await expect(heading).toHaveText("设置");
  });

  test("displays the nav bar with home link", async ({ page }) => {
    await page.goto("/settings");

    const navBrand = page.locator(".nav-brand");
    await expect(navBrand).toBeVisible();
    await expect(navBrand).toContainText("Paper2Repo");
  });

  test("displays the UI language select", async ({ page }) => {
    await page.goto("/settings");

    const uiLanguageSelect = page.locator("#ui-language");
    await expect(uiLanguageSelect).toBeVisible();

    const options = uiLanguageSelect.locator("option");
    await expect(options).toHaveCount(2);
  });

  test("displays the report language select", async ({ page }) => {
    await page.goto("/settings");

    const reportLanguageSelect = page.locator("#report-language");
    await expect(reportLanguageSelect).toBeVisible();

    const options = reportLanguageSelect.locator("option");
    await expect(options).toHaveCount(2);
  });

  test("displays the default model select", async ({ page }) => {
    await page.goto("/settings");

    const modelSelect = page.locator("#default-model");
    await expect(modelSelect).toBeVisible();
  });

  test("displays language labels", async ({ page }) => {
    await page.goto("/settings");

    // Check that the field labels for language selects are present
    const uiLanguageLabel = page.locator('label[for="ui-language"]');
    await expect(uiLanguageLabel).toBeVisible();
    await expect(uiLanguageLabel).toContainText("界面语言");

    const reportLanguageLabel = page.locator('label[for="report-language"]');
    await expect(reportLanguageLabel).toBeVisible();
    await expect(reportLanguageLabel).toContainText("报告语言");
  });

  test("displays the save button", async ({ page }) => {
    await page.goto("/settings");

    const saveButton = page.getByRole("button", { name: "保存设置" });
    await expect(saveButton).toBeVisible();
  });

  test("can run model connection check", async ({ page }) => {
    await page.goto("/settings");

    await page.getByRole("button", { name: "测试模型连接" }).click();
    await expect(page.locator(".muted").filter({ hasText: "模型连接正常" })).toBeVisible();
  });
});
