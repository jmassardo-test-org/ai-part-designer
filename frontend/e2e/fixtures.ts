import { Page, expect } from '@playwright/test';

/**
 * E2E Test Fixtures and Helpers.
 * Common utilities for Playwright tests.
 */

// Test credentials
export const testUser = {
  email: 'e2e-test@example.com',
  password: 'TestPassword123!',
  displayName: 'E2E Test User',
};

export const adminUser = {
  email: 'e2e-admin@example.com',
  password: 'AdminPassword123!',
  displayName: 'E2E Admin User',
};

/**
 * Log in a user
 */
export async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
  
  // Wait for redirect to dashboard
  await expect(page).toHaveURL(/\/dashboard/);
}

/**
 * Log out the current user
 */
export async function logout(page: Page): Promise<void> {
  // Dismiss onboarding modal if it appears by clicking "Skip tour"
  const skipTourButton = page.locator('button:has-text("Skip tour")');
  if (await skipTourButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipTourButton.click();
    await page.waitForTimeout(500);
  }
  
  // Click user menu
  await page.click('[data-tour="user-menu"]');
  
  // Wait for menu to appear and click logout (it's a menuitem, not a button)
  await page.click('[role="menuitem"]:has-text("Log out")');
  
  // Wait for redirect to login
  await expect(page).toHaveURL(/\/login/);
}

/**
 * Register a new user
 */
export async function register(
  page: Page,
  email: string,
  password: string,
  displayName: string
): Promise<void> {
  await page.goto('/register');
  await page.fill('input[name="display_name"]', displayName);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.check('input[name="accepted_terms"]');
  await page.click('button[type="submit"]');
}

/**
 * Wait for toast notification
 */
export async function expectToast(page: Page, message: string | RegExp): Promise<void> {
  const toast = page.locator('[role="alert"]');
  await expect(toast).toContainText(message);
}

/**
 * Navigate to a page via the navigation menu
 */
export async function navigateTo(page: Page, linkText: string): Promise<void> {
  await page.click(`nav >> text="${linkText}"`);
}

/**
 * Wait for loading state to complete
 */
export async function waitForLoading(page: Page): Promise<void> {
  // Wait for any loading spinners to disappear
  await page.waitForSelector('[data-testid="loading"]', { state: 'hidden' }).catch(() => {});
  
  // Also wait for any skeleton loaders
  await page.waitForSelector('.animate-pulse', { state: 'hidden' }).catch(() => {});
}

/**
 * Take a named screenshot
 */
export async function takeScreenshot(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
}

/**
 * Fill a form field by label
 */
export async function fillField(page: Page, label: string, value: string): Promise<void> {
  await page.fill(`input[aria-label="${label}"], label:has-text("${label}") + input, label:has-text("${label}") input`, value);
}

/**
 * Select an option from a dropdown
 */
export async function selectOption(page: Page, label: string, value: string): Promise<void> {
  await page.selectOption(`select[aria-label="${label}"], label:has-text("${label}") + select, label:has-text("${label}") select`, value);
}

/**
 * Check if an element is visible
 */
export async function isVisible(page: Page, selector: string): Promise<boolean> {
  return await page.isVisible(selector);
}

/**
 * Wait for API response
 */
export async function waitForApiResponse(page: Page, urlPattern: string | RegExp): Promise<void> {
  await page.waitForResponse(response => 
    (typeof urlPattern === 'string' 
      ? response.url().includes(urlPattern) 
      : urlPattern.test(response.url())) &&
    response.status() === 200
  );
}

/**
 * Generate a unique email for test isolation
 */
export function generateUniqueEmail(): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(7);
  return `e2e-test-${timestamp}-${random}@example.com`;
}

/**
 * Generate unique test data
 */
export function generateTestData() {
  const id = Date.now().toString(36);
  return {
    projectName: `Test Project ${id}`,
    fileName: `test-file-${id}.stl`,
    email: generateUniqueEmail(),
  };
}
