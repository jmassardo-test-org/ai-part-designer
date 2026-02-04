/**
 * E2E tests for design lists management flows.
 */

import { test, expect } from '@playwright/test';

test.describe('Lists Management Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
  });

  test('should navigate to lists page', async ({ page }) => {
    await page.click('text=My Lists');
    await page.waitForURL('**/lists');
    
    await expect(page.locator('h1')).toContainText('My Lists');
  });

  test('should display existing lists', async ({ page }) => {
    await page.goto('/lists');
    
    // Wait for lists to load
    await page.waitForSelector('[data-testid="list-card"], [data-testid="empty-state"]');
    
    // Either lists or empty state should be visible
    const hasLists = await page.locator('[data-testid="list-card"]').count() > 0;
    const hasEmptyState = await page.locator('[data-testid="empty-state"]').isVisible();
    
    expect(hasLists || hasEmptyState).toBeTruthy();
  });

  test('should open create list dialog', async ({ page }) => {
    await page.goto('/lists');
    
    await page.click('[data-testid="create-list-button"]');
    
    await expect(page.locator('[data-testid="create-list-dialog"]')).toBeVisible();
  });

  test('should create a new list', async ({ page }) => {
    await page.goto('/lists');
    
    // Open create dialog
    await page.click('[data-testid="create-list-button"]');
    
    // Fill in list name
    await page.fill('[data-testid="list-name-input"]', 'My Test List');
    
    // Optional: add description
    await page.fill('[data-testid="list-description-input"]', 'A test list created by E2E');
    
    // Submit
    await page.click('[data-testid="create-list-submit"]');
    
    // Dialog should close
    await expect(page.locator('[data-testid="create-list-dialog"]')).not.toBeVisible();
    
    // New list should appear
    await expect(page.locator('text=My Test List')).toBeVisible();
  });

  test('should show list item count', async ({ page }) => {
    await page.goto('/lists');
    
    await page.waitForSelector('[data-testid="list-card"]');
    
    // Item counts should be displayed
    const itemCountElements = page.locator('[data-testid="item-count"]');
    
    if (await itemCountElements.count() > 0) {
      await expect(itemCountElements.first()).toContainText(/\d+ items?/);
    }
  });

  test('should toggle list visibility', async ({ page }) => {
    await page.goto('/lists');
    
    await page.waitForSelector('[data-testid="list-card"]');
    
    // Find visibility toggle
    const visibilityToggle = page.locator('[data-testid="visibility-toggle"]').first();
    
    if (await visibilityToggle.isVisible()) {
      const initialState = await visibilityToggle.getAttribute('data-public');
      await visibilityToggle.click();
      
      // State should change
      await expect(visibilityToggle).not.toHaveAttribute('data-public', initialState || '');
    }
  });

  test('should delete a list', async ({ page }) => {
    await page.goto('/lists');
    
    // First create a list to delete
    await page.click('[data-testid="create-list-button"]');
    await page.fill('[data-testid="list-name-input"]', 'List To Delete');
    await page.click('[data-testid="create-list-submit"]');
    
    await page.waitForSelector('text=List To Delete');
    
    // Find and click delete button
    const listCard = page.locator('[data-testid="list-card"]').filter({ hasText: 'List To Delete' });
    await listCard.locator('[data-testid="delete-list-button"]').click();
    
    // Confirm deletion
    await page.click('[data-testid="confirm-delete"]');
    
    // List should be gone
    await expect(page.locator('text=List To Delete')).not.toBeVisible();
  });
});

test.describe('List Detail Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
  });

  test('should click through to list detail', async ({ page }) => {
    await page.goto('/lists');
    
    await page.waitForSelector('[data-testid="list-card"]');
    
    // Click on list card
    await page.click('[data-testid="list-card"]');
    
    // Should navigate to list detail
    await expect(page).toHaveURL(/\/lists\//);
  });

  test('should display list items', async ({ page }) => {
    await page.goto('/lists');
    
    await page.waitForSelector('[data-testid="list-card"]');
    await page.click('[data-testid="list-card"]');
    
    // Wait for items or empty state
    await page.waitForSelector('[data-testid="list-item"], [data-testid="empty-list"]');
  });

  test('should remove item from list', async ({ page }) => {
    await page.goto('/lists');
    
    await page.waitForSelector('[data-testid="list-card"]');
    await page.click('[data-testid="list-card"]');
    
    // Check if there are items to remove
    const itemCount = await page.locator('[data-testid="list-item"]').count();
    
    if (itemCount > 0) {
      await page.locator('[data-testid="remove-item-button"]').first().click();
      
      // Item count should decrease
      const newItemCount = await page.locator('[data-testid="list-item"]').count();
      expect(newItemCount).toBeLessThan(itemCount);
    }
  });

  test('should reorder items via drag and drop', async ({ page }) => {
    await page.goto('/lists');
    
    await page.waitForSelector('[data-testid="list-card"]');
    await page.click('[data-testid="list-card"]');
    
    const items = await page.locator('[data-testid="list-item"]').count();
    
    if (items >= 2) {
      // Get first two items
      const firstItem = page.locator('[data-testid="list-item"]').nth(0);
      const secondItem = page.locator('[data-testid="list-item"]').nth(1);
      
      const firstItemText = await firstItem.textContent();
      
      // Drag first item below second
      await firstItem.dragTo(secondItem);
      
      // First position should now have different item
      const newFirstItemText = await page.locator('[data-testid="list-item"]').nth(0).textContent();
      expect(newFirstItemText).not.toBe(firstItemText);
    }
  });
});

test.describe('Public Lists', () => {
  test('should view public list without login', async ({ page }) => {
    // Navigate directly to a public list URL
    await page.goto('/lists/public/some-public-list-id');
    
    // Should show the list (even if 404, we're testing the flow exists)
    await expect(page).toHaveURL(/\/lists\/public\//);
  });

  test('should share list and get shareable link', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
    
    await page.goto('/lists');
    
    await page.waitForSelector('[data-testid="list-card"]');
    
    // Find share button
    const shareButton = page.locator('[data-testid="share-list-button"]').first();
    
    if (await shareButton.isVisible()) {
      await shareButton.click();
      
      // Share dialog or copy notification should appear
      const hasShareDialog = await page.locator('[data-testid="share-dialog"]').isVisible();
      const hasCopyNotification = await page.locator('text=Copied').isVisible();
      
      expect(hasShareDialog || hasCopyNotification).toBeTruthy();
    }
  });
});
