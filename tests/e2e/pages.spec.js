import { test, expect } from "@playwright/test";

async function mockCartoTiles(page) {
  await page.route("https://*.basemaps.cartocdn.com/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "base64",
      ),
    });
  });
}

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

  test("map renders tiles", async ({ page }) => {
    await mockCartoTiles(page);

    await page.goto("/pages/traveling.html", { waitUntil: "networkidle" });
    await expect(page.locator("#map .leaflet-tile-loaded").first()).toBeVisible();
  });

  test("back link is present", async ({ page }) => {
    await page.goto("/pages/traveling.html");

    const backLink = page.locator(".back-link");
    await expect(backLink).toBeVisible();
    await expect(backLink).toHaveAttribute("href", "../index.html");
    await expect(backLink).toContainText("Back Home");
  });
});

test.describe("Skating page", () => {
  test("renders correctly", async ({ page }) => {
    await page.goto("/pages/skating.html");

    await expect(page).toHaveTitle(
      "Barcelona Inline Skating Routes - Erica Bertugli",
    );
    await expect(page.locator("h1")).toHaveText("Urban Inline Skating");
    await expect(page.locator("#map")).toBeVisible();
  });

  test("map renders tiles", async ({ page }) => {
    await mockCartoTiles(page);

    await page.goto("/pages/skating.html", { waitUntil: "networkidle" });
    await expect(page.locator("#map .leaflet-tile-loaded").first()).toBeVisible();
  });

  test("disclaimer is visible", async ({ page }) => {
    await page.goto("/pages/skating.html");

    await expect(page.locator(".disclaimer")).toBeVisible();
    await expect(page.locator(".disclaimer")).toContainText("Disclaimer");
  });

  test("back link is present", async ({ page }) => {
    await page.goto("/pages/skating.html");

    const backLink = page.locator(".back-link");
    await expect(backLink).toBeVisible();
    await expect(backLink).toHaveAttribute("href", "../index.html");
    await expect(backLink).toContainText("Back Home");
  });
});
