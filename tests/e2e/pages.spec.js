import { test, expect } from "@playwright/test";

test.describe("Homepage", () => {
  test("renders correctly", async ({ page }) => {
    await page.goto("/");

    await expect(page).toHaveTitle("Erica Bertugli");
    await expect(page.locator("h1")).toHaveText("Erica Bertugli");
    await expect(page.locator(".profile-pic")).toBeVisible();
    await expect(page.locator(".location")).toContainText("Barcelona");
  });

  test("navigation links work", async ({ page }) => {
    await page.goto("/");

    await expect(page.locator('a[href="pages/developer.html"]')).toBeVisible();
    await expect(page.locator('a[href="pages/traveling.html"]')).toBeVisible();
    await expect(page.locator('a[href="pages/skating.html"]')).toBeVisible();
  });

  test("social links are present", async ({ page }) => {
    await page.goto("/");

    await expect(page.locator('a[href*="github.com"]')).toBeVisible();
    await expect(page.locator('a[href*="linkedin.com"]')).toBeVisible();
    await expect(page.locator('a[href*="instagram.com"]')).toBeVisible();
  });
});

test.describe("Travel page", () => {
  test("renders correctly", async ({ page }) => {
    await page.goto("/pages/traveling.html");

    await expect(page).toHaveTitle("Travel Map - Erica Bertugli");
    await expect(page.locator("h1")).toHaveText("Travel Map");
    await expect(page.locator("#map")).toBeVisible();
  });

  test("back link navigates home", async ({ page }) => {
    await page.goto("/pages/traveling.html");

    await page.locator("#cookie-banner .decline").click();
    await page.click(".back-link");
    await expect(page.locator("h1")).toHaveText("Erica Bertugli");
  });
});

test.describe("Skating page", () => {
  test("renders correctly", async ({ page }) => {
    await page.goto("/pages/skating.html");

    await expect(page).toHaveTitle(
      "Barcelona Inline Skating Routes - Erica Bertugli",
    );
    await expect(page.locator("h1")).toHaveText("Inline Skating");
    await expect(page.locator("#map")).toBeVisible();
  });

  test("disclaimer is visible", async ({ page }) => {
    await page.goto("/pages/skating.html");

    await expect(page.locator(".disclaimer")).toBeVisible();
    await expect(page.locator(".disclaimer")).toContainText("Disclaimer");
  });

  test("back link navigates home", async ({ page }) => {
    await page.goto("/pages/skating.html");

    await page.locator("#cookie-banner .decline").click();
    await page.click(".back-link");
    await expect(page.locator("h1")).toHaveText("Erica Bertugli");
  });
});
