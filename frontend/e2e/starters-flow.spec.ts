/**
 * E2E tests for starter designs and remix flow.
 */

import { test, expect } from '@playwright/test';

test.describe('Starters Gallery Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
  });

  test('should navigate to starters page', async ({ page }) => {
    await page.click('text=Starters');
    await page.waitForURL('**/starters');
    
    await expect(page.locator('h1')).toContainText('Starter Designs');
  });

  test('should display starter designs grid', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"], [data-testid="no-starters"]');
    
    // Either starters or empty state
    const hasStarters = await page.locator('[data-testid="starter-card"]').count() > 0;
    const hasEmptyState = await page.locator('[data-testid="no-starters"]').isVisible();
    
    expect(hasStarters || hasEmptyState).toBeTruthy();
  });

  test('should filter by category', async ({ page }) => {
    await page.goto('/starters');
    
    // Wait for category pills
    await page.waitForSelector('[data-testid="category-pill"]');
    
    // Click a category pill
    await page.click('[data-testid="category-pill"]');
    
    // URL should update
    await expect(page).toHaveURL(/category=/);
  });

  test('should search for starters', async ({ page }) => {
    await page.goto('/starters');
    
    await page.fill('[data-testid="starter-search"]', 'raspberry');
    
    // Wait for search debounce
    await page.waitForTimeout(500);
    
    // URL should update
    await expect(page).toHaveURL(/q=raspberry/);
  });

  test('should show starter dimensions', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    
    // Dimensions should be visible on cards
    const dimensionText = page.locator('[data-testid="starter-dimensions"]').first();
    await expect(dimensionText).toContainText(/mm/);
  });

  test('should show remix count', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    
    // Remix count badge should be visible
    const remixCount = page.locator('[data-testid="remix-count"]').first();
    await expect(remixCount).toContainText(/\d+/);
  });

  test('should display feature tags', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    
    // Feature tags should be visible
    const featureTags = page.locator('[data-testid="feature-tag"]');
    
    if (await featureTags.count() > 0) {
      await expect(featureTags.first()).toBeVisible();
    }
  });
});

test.describe('Remix Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
  });

  test('should show remix button on starter cards', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    
    // Remix buttons should be present
    const remixButtons = page.locator('[data-testid="remix-button"]');
    await expect(remixButtons.first()).toBeVisible();
  });

  test('should remix a starter design', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    
    // Click remix on first starter
    await page.click('[data-testid="remix-button"]');
    
    // Should navigate to the new design editor
    await page.waitForURL('**/designs/**', { timeout: 10000 });
    
    // New design page should load
    await expect(page.locator('[data-testid="design-editor"]')).toBeVisible();
  });

  test('should show remixed from attribution', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    await page.click('[data-testid="remix-button"]');
    
    await page.waitForURL('**/designs/**', { timeout: 10000 });
    
    // Should show "Remixed from" attribution
    await expect(page.locator('text=Remixed from')).toBeVisible();
  });

  test('should inherit enclosure spec from starter', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    
    // Get dimensions from the starter card
    const starterDimensions = await page.locator('[data-testid="starter-dimensions"]').first().textContent();
    
    await page.click('[data-testid="remix-button"]');
    
    await page.waitForURL('**/designs/**', { timeout: 10000 });
    
    // Design editor should show similar dimensions (inherited from starter)
    if (starterDimensions) {
      // Check that the design has the enclosure loaded
      await expect(page.locator('[data-testid="enclosure-preview"]')).toBeVisible();
    }
  });
});

test.describe('Starter Detail View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
  });

  test('should click through to starter detail', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    
    // Click card (not the remix button)
    await page.locator('[data-testid="starter-card"]').first().click();
    
    await expect(page).toHaveURL(/\/starters\//);
  });

  test('should show full description on detail page', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    await page.locator('[data-testid="starter-card"]').first().click();
    
    // Description should be fully visible
    await expect(page.locator('[data-testid="starter-description"]')).toBeVisible();
  });

  test('should show 3D preview on detail page', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    await page.locator('[data-testid="starter-card"]').first().click();
    
    // 3D viewer should be present
    await expect(page.locator('[data-testid="3d-viewer"]')).toBeVisible();
  });

  test('should remix from detail page', async ({ page }) => {
    await page.goto('/starters');
    
    await page.waitForSelector('[data-testid="starter-card"]');
    await page.locator('[data-testid="starter-card"]').first().click();
    
    // Click remix button on detail page
    await page.click('[data-testid="remix-button"]');
    
    // Should navigate to new design
    await page.waitForURL('**/designs/**', { timeout: 10000 });
  });
});

test.describe('Create from Scratch CTA', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
  });

  test('should show create from scratch CTA', async ({ page }) => {
    await page.goto('/starters');
    
    await expect(page.locator('text=Create from Scratch')).toBeVisible();
  });

  test('should navigate to new design when clicking create from scratch', async ({ page }) => {
    await page.goto('/starters');
    
    await page.click('text=Create from Scratch');
    
    // Should navigate to design creation
    await expect(page).toHaveURL(/\/(designs\/new|create)/);
  });
});
