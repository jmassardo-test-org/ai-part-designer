/**
 * E2E tests for marketplace browse and interaction flows.
 */

import { test, expect } from '@playwright/test';

test.describe('Marketplace Browse Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
  });

  test('should navigate to marketplace page', async ({ page }) => {
    await page.click('text=Marketplace');
    await page.waitForURL('**/marketplace');
    
    await expect(page.locator('h1')).toContainText('Design Marketplace');
  });

  test('should display featured designs section', async ({ page }) => {
    await page.goto('/marketplace');
    
    await expect(page.locator('text=Featured Designs')).toBeVisible();
  });

  test('should filter by category', async ({ page }) => {
    await page.goto('/marketplace');
    
    // Wait for categories to load
    await page.waitForSelector('[data-testid="category-filter"]');
    
    // Click on a category
    await page.click('[data-testid="category-raspberry-pi"]');
    
    // URL should update with category
    await expect(page).toHaveURL(/category=raspberry-pi/);
  });

  test('should search for designs', async ({ page }) => {
    await page.goto('/marketplace');
    
    // Type in search box
    await page.fill('[data-testid="search-input"]', 'arduino');
    
    // Wait for debounce
    await page.waitForTimeout(500);
    
    // URL should update with search query
    await expect(page).toHaveURL(/q=arduino/);
  });

  test('should sort designs', async ({ page }) => {
    await page.goto('/marketplace');
    
    // Click sort dropdown
    await page.click('[data-testid="sort-select"]');
    await page.click('text=Newest First');
    
    // URL should update with sort param
    await expect(page).toHaveURL(/sort=newest/);
  });

  test('should toggle grid and list view', async ({ page }) => {
    await page.goto('/marketplace');
    
    // Default should be grid
    await expect(page.locator('[data-testid="design-grid"]')).toBeVisible();
    
    // Toggle to list view
    await page.click('[data-testid="list-view-toggle"]');
    
    // Should show list layout
    await expect(page.locator('[data-testid="design-list"]')).toBeVisible();
  });

  test('should paginate through results', async ({ page }) => {
    await page.goto('/marketplace');
    
    // Click next page if available
    const nextButton = page.locator('[data-testid="next-page"]');
    
    if (await nextButton.isEnabled()) {
      await nextButton.click();
      await expect(page).toHaveURL(/page=2/);
    }
  });
});

test.describe('Marketplace Save Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
  });

  test('should save a design to default list', async ({ page }) => {
    await page.goto('/marketplace');
    
    // Wait for designs to load
    await page.waitForSelector('[data-testid="design-card"]');
    
    // Click save button on first design
    const saveButton = page.locator('[data-testid="save-button"]').first();
    await saveButton.click();
    
    // Button should show saved state
    await expect(saveButton).toHaveClass(/saved/);
  });

  test('should open save to list dialog', async ({ page }) => {
    await page.goto('/marketplace');
    
    await page.waitForSelector('[data-testid="design-card"]');
    
    // Click the dropdown arrow on save button
    await page.click('[data-testid="save-to-list-button"]').catch(() => {
      // Fallback: right-click on save button
      page.locator('[data-testid="save-button"]').first().click({ button: 'right' });
    });
    
    // Dialog should appear
    await expect(page.locator('[data-testid="save-to-list-dialog"]')).toBeVisible();
  });

  test('should unsave a previously saved design', async ({ page }) => {
    await page.goto('/marketplace');
    
    await page.waitForSelector('[data-testid="design-card"]');
    
    // Find a saved design and unsave it
    const savedButton = page.locator('[data-testid="save-button"].saved').first();
    
    if (await savedButton.isVisible()) {
      await savedButton.click();
      
      // Should no longer have saved class
      await expect(savedButton).not.toHaveClass(/saved/);
    }
  });
});

test.describe('Design Detail from Marketplace', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
  });

  test('should click through to design detail', async ({ page }) => {
    await page.goto('/marketplace');
    
    await page.waitForSelector('[data-testid="design-card"]');
    
    // Click on design card
    await page.click('[data-testid="design-card"]');
    
    // Should navigate to design detail page
    await expect(page).toHaveURL(/\/designs\//);
  });

  test('should show designer info on detail page', async ({ page }) => {
    await page.goto('/marketplace');
    
    await page.waitForSelector('[data-testid="design-card"]');
    await page.click('[data-testid="design-card"]');
    
    // Designer info should be visible
    await expect(page.locator('[data-testid="designer-info"]')).toBeVisible();
  });
});
