import { test, expect } from '@playwright/test';
import { testUser, login } from './fixtures';

/**
 * E2E Tests for Project Management Flows.
 * Tests: Create project, view projects, manage designs.
 */

test.describe('Project Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, testUser.email, testUser.password);
    
    // Dismiss onboarding modal if it appears
    const skipTourButton = page.locator('button:has-text("Skip tour")');
    if (await skipTourButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipTourButton.click();
      await page.waitForTimeout(500);
    }
  });

  test.describe('Projects Page', () => {
    test('should navigate to projects page', async ({ page }) => {
      await page.goto('/projects');
      
      // Should see projects page
      await expect(page.locator('text=/Projects|My Projects/i')).toBeVisible();
    });

    test('should show create project button', async ({ page }) => {
      await page.goto('/projects');
      
      // Should see create button
      await expect(page.locator('button:has-text(/Create|New Project/i)')).toBeVisible();
    });

    test('should open create project dialog', async ({ page }) => {
      await page.goto('/projects');
      
      // Click create button
      await page.click('button:has-text(/Create|New Project/i)');
      
      // Should see dialog with form
      await expect(page.locator('input[name="name"], input[placeholder*="name"]')).toBeVisible();
    });
  });

  test.describe('Dashboard', () => {
    test('should show dashboard with recent designs', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Dashboard should load
      await expect(page.locator('text=/Recent|Dashboard|Welcome/i')).toBeVisible();
    });

    test('should show quick actions', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Should have quick action buttons or links
      const createLink = page.locator('a:has-text(/Create|New Design/i)').first();
      const isVisible = await createLink.isVisible().catch(() => false);
      
      // Either quick actions or navigation should be present
      expect(isVisible || await page.locator('nav').isVisible()).toBe(true);
    });
  });

  test.describe('Designs Page', () => {
    test('should navigate to designs/files page', async ({ page }) => {
      await page.goto('/files');
      
      // Should see files/designs page
      await expect(page.locator('text=/Files|Designs|My Files/i')).toBeVisible();
    });

    test('should show upload button', async ({ page }) => {
      await page.goto('/files');
      
      // Should see upload functionality
      const uploadButton = page.locator('button:has-text(/Upload/i)');
      const isVisible = await uploadButton.isVisible().catch(() => false);
      
      // Either upload button or drag area should be present
      expect(isVisible || await page.locator('text=/drag.*drop/i').isVisible()).toBe(true);
    });
  });

  test.describe('Navigation', () => {
    test('should navigate between main sections', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Navigate to projects
      await page.click('a:has-text("Projects")');
      await expect(page).toHaveURL(/\/projects/);
      
      // Navigate to files
      await page.click('a:has-text(/Files|Designs/i)');
      await expect(page).toHaveURL(/\/files/);
      
      // Navigate back to dashboard
      await page.click('a:has-text(/Dashboard|Home/i)');
      await expect(page).toHaveURL(/\/dashboard/);
    });

    test('should show user menu', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Click user menu
      await page.click('[data-tour="user-menu"]');
      
      // Should see menu items
      await expect(page.locator('[role="menuitem"]:has-text("Settings")')).toBeVisible();
      await expect(page.locator('[role="menuitem"]:has-text("Log out")')).toBeVisible();
    });
  });

  test.describe('Settings', () => {
    test('should navigate to settings page', async ({ page }) => {
      await page.goto('/settings');
      
      // Should see settings page
      await expect(page.locator('text=/Settings|Account|Profile/i')).toBeVisible();
    });

    test('should show profile section', async ({ page }) => {
      await page.goto('/settings');
      
      // Should see profile settings
      await expect(page.locator('text=/Profile|Display Name|Email/i')).toBeVisible();
    });
  });
});

test.describe('v2 Design Save Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, testUser.email, testUser.password);
    
    // Dismiss onboarding modal if it appears
    const skipTourButton = page.locator('button:has-text("Skip tour")');
    if (await skipTourButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipTourButton.click();
      await page.waitForTimeout(500);
    }
  });

  // These tests require full backend
  test.skip(({ page }) => !process.env.RUN_FULL_E2E, 'Skipping full E2E tests');

  test('should open save dialog after generation', async ({ page }) => {
    await page.goto('/generate');
    await page.click('text=Manual Config');
    await page.click('button:has-text("Compile Enclosure")');
    
    // Wait for completion
    await expect(page.locator('button:has-text("Save to Project")')).toBeVisible({
      timeout: 60000,
    });
    
    // Click save button
    await page.click('button:has-text("Save to Project")');
    
    // Should see save dialog
    await expect(page.locator('text=Design Name')).toBeVisible();
  });

  test('should save design with name', async ({ page }) => {
    await page.goto('/generate');
    await page.click('text=Manual Config');
    await page.click('button:has-text("Compile Enclosure")');
    
    // Wait for completion and click save
    await expect(page.locator('button:has-text("Save to Project")')).toBeVisible({
      timeout: 60000,
    });
    await page.click('button:has-text("Save to Project")');
    
    // Fill in name
    const timestamp = Date.now();
    await page.fill('input[placeholder*="name"], input[name="name"]', `Test Design ${timestamp}`);
    
    // Click save
    await page.click('button:has-text("Save")');
    
    // Dialog should close (save successful)
    await expect(page.locator('text=Design Name')).not.toBeVisible();
  });

  test('should show saved design in projects', async ({ page }) => {
    // First generate and save a design
    await page.goto('/generate');
    await page.click('text=Manual Config');
    await page.click('button:has-text("Compile Enclosure")');
    
    await expect(page.locator('button:has-text("Save to Project")')).toBeVisible({
      timeout: 60000,
    });
    await page.click('button:has-text("Save to Project")');
    
    const timestamp = Date.now();
    const designName = `E2E Test ${timestamp}`;
    await page.fill('input[placeholder*="name"], input[name="name"]', designName);
    await page.click('button:has-text("Save")');
    
    // Navigate to projects/files
    await page.goto('/files');
    
    // Should see the saved design
    await expect(page.locator(`text=${designName}`)).toBeVisible({ timeout: 10000 });
  });
});
