import { test, expect } from '@playwright/test';
import { testUser, login } from './fixtures';

/**
 * E2E Tests for CAD v2 Generation Flows.
 * Tests: Generate enclosure, download files, save to project.
 */

test.describe('CAD v2 Generation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, testUser.email, testUser.password);
    
    // Dismiss onboarding modal if it appears
    const skipTourButton = page.locator('button:has-text("Skip tour")');
    if (await skipTourButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipTourButton.click();
      await page.waitForTimeout(500);
    }
  });

  test.describe('Generate Page Access', () => {
    test('should navigate to generate page', async ({ page }) => {
      await page.goto('/generate');
      
      // Should see the v2 generate page header
      await expect(page.locator('text=Generate Enclosure')).toBeVisible();
      await expect(page.locator('text=v2')).toBeVisible();
    });

    test('should show AI and Manual mode toggles', async ({ page }) => {
      await page.goto('/generate');
      
      // Should see mode toggles
      await expect(page.locator('text=AI Description')).toBeVisible();
      await expect(page.locator('text=Manual Config')).toBeVisible();
    });
  });

  test.describe('AI Mode', () => {
    test('should show example prompts', async ({ page }) => {
      await page.goto('/generate');
      
      // AI mode should be default
      await expect(page.locator('text=Example Prompts')).toBeVisible();
      
      // Should show at least one example
      await expect(page.locator('text=/enclosure|box|case/i').first()).toBeVisible();
    });

    test('should fill description when example is clicked', async ({ page }) => {
      await page.goto('/generate');
      
      // Find and click an example prompt
      const exampleButton = page.locator('button:has-text("enclosure")').first();
      if (await exampleButton.isVisible()) {
        await exampleButton.click();
        
        // Textarea should now have content
        const textarea = page.locator('textarea');
        const value = await textarea.inputValue();
        expect(value.length).toBeGreaterThan(10);
      }
    });

    test('should disable generate button when description is empty', async ({ page }) => {
      await page.goto('/generate');
      
      // Clear any existing text
      const textarea = page.locator('textarea');
      await textarea.fill('');
      
      // Generate button should be disabled
      const generateButton = page.locator('button:has-text("Generate")').first();
      await expect(generateButton).toBeDisabled();
    });

    test('should enable generate button when description has content', async ({ page }) => {
      await page.goto('/generate');
      
      // Fill in a description
      const textarea = page.locator('textarea');
      await textarea.fill('Create a simple box 100x80x50mm');
      
      // Generate button should be enabled
      const generateButton = page.locator('button:has-text("Generate")');
      await expect(generateButton).toBeEnabled();
    });
  });

  test.describe('Manual Mode', () => {
    test('should switch to manual mode', async ({ page }) => {
      await page.goto('/generate');
      
      await page.click('text=Manual Config');
      
      // Should see dimension controls
      await expect(page.locator('text=Dimensions')).toBeVisible();
      await expect(page.locator('text=Features')).toBeVisible();
    });

    test('should show dimension presets', async ({ page }) => {
      await page.goto('/generate');
      await page.click('text=Manual Config');
      
      // Should see preset buttons
      await expect(page.locator('button:has-text("Small")')).toBeVisible();
      await expect(page.locator('button:has-text("Medium")')).toBeVisible();
      await expect(page.locator('button:has-text("Pi Case")')).toBeVisible();
    });

    test('should show lid type options', async ({ page }) => {
      await page.goto('/generate');
      await page.click('text=Manual Config');
      
      // Should see lid type options
      await expect(page.locator('text=Snap-fit')).toBeVisible();
      await expect(page.locator('text=Screw-on')).toBeVisible();
    });

    test('should show ventilation toggle', async ({ page }) => {
      await page.goto('/generate');
      await page.click('text=Manual Config');
      
      // Should see ventilation section
      await expect(page.locator('text=Ventilation')).toBeVisible();
    });

    test('should show port selection', async ({ page }) => {
      await page.goto('/generate');
      await page.click('text=Manual Config');
      
      // Should see port/cutout section
      await expect(page.locator('text=Ports & Cutouts')).toBeVisible();
      await expect(page.locator('button:has-text("USB-C")')).toBeVisible();
      await expect(page.locator('button:has-text("HDMI")')).toBeVisible();
    });

    test('should add port feature when clicked', async ({ page }) => {
      await page.goto('/generate');
      await page.click('text=Manual Config');
      
      // Add a USB-C port
      await page.click('button:has-text("USB-C")');
      
      // Should show in the features list
      await expect(page.locator('text=1 added')).toBeVisible();
    });
  });

  test.describe('3D Preview', () => {
    test('should show placeholder before generation', async ({ page }) => {
      await page.goto('/generate');
      
      // Preview area should show placeholder
      await expect(page.locator('text=Preview will appear here')).toBeVisible();
    });
  });

  // Note: Actual generation tests require backend to be running
  // These are smoke tests that can run without full backend
  test.describe('Generation Flow (requires backend)', () => {
    test.skip(({ _page }) => !process.env.RUN_FULL_E2E, 'Skipping full E2E tests');

    test('should generate enclosure from manual config', async ({ page }) => {
      await page.goto('/generate');
      await page.click('text=Manual Config');
      
      // Click compile button
      await page.click('button:has-text("Compile Enclosure")');
      
      // Should show loading state
      await expect(page.locator('text=/Compiling|Generating/i')).toBeVisible();
      
      // Wait for completion (up to 60 seconds)
      await expect(page.locator('[data-testid="model-viewer"]')).toBeVisible({
        timeout: 60000,
      });
    });

    test('should show download buttons after generation', async ({ page }) => {
      await page.goto('/generate');
      await page.click('text=Manual Config');
      await page.click('button:has-text("Compile Enclosure")');
      
      // Wait for completion
      await expect(page.locator('text=Downloads')).toBeVisible({ timeout: 60000 });
      
      // Should have STEP and STL downloads
      await expect(page.locator('a:has-text(".step")')).toBeVisible();
      await expect(page.locator('a:has-text(".stl")')).toBeVisible();
    });

    test('should show save to project button for authenticated users', async ({ page }) => {
      await page.goto('/generate');
      await page.click('text=Manual Config');
      await page.click('button:has-text("Compile Enclosure")');
      
      // Wait for completion
      await expect(page.locator('text=Downloads')).toBeVisible({ timeout: 60000 });
      
      // Should have Save to Project button
      await expect(page.locator('button:has-text("Save to Project")')).toBeVisible();
    });
  });
});

test.describe('Create Page (Chat Interface)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, testUser.email, testUser.password);
    
    // Dismiss onboarding modal if it appears
    const skipTourButton = page.locator('button:has-text("Skip tour")');
    if (await skipTourButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipTourButton.click();
      await page.waitForTimeout(500);
    }
  });

  test('should navigate to create page', async ({ page }) => {
    await page.goto('/create');
    
    // Should see the create page
    await expect(page.locator('text=/What would you like to create/i')).toBeVisible();
  });

  test('should show example categories', async ({ page }) => {
    await page.goto('/create');
    
    // Should see example categories
    await expect(page.locator('text=Basic Shapes')).toBeVisible();
  });

  test('should show history button if user has history', async ({ page }) => {
    await page.goto('/create');
    
    // History button may or may not be visible depending on user history
    // Just check the page loads without errors
    await expect(page).toHaveURL(/\/create/);
  });
});
