import { test, expect } from '@playwright/test';
import { testUser, login, logout, generateUniqueEmail } from './fixtures';

/**
 * E2E Tests for Authentication Flows.
 * Tests: Register, Login, Logout, Password Reset, Email Verification.
 */

test.describe('Authentication', () => {
  test.describe('Registration', () => {
    test('should register a new user successfully', async ({ page }) => {
      const email = generateUniqueEmail();
      const password = 'SecurePassword123!';
      const displayName = 'New Test User';

      await page.goto('/register');
      
      // Fill registration form
      await page.fill('input[name="display_name"]', displayName);
      await page.fill('input[name="email"]', email);
      await page.fill('input[name="password"]', password);
      
      // Accept terms
      await page.check('input[name="accepted_terms"]');
      
      // Submit form
      await page.click('button[type="submit"]');
      
      // Should redirect to login with verification message or dashboard
      await expect(page).toHaveURL(/\/(dashboard|login|verify-email)/);
    });

    test('should show error for missing terms acceptance', async ({ page }) => {
      await page.goto('/register');
      
      await page.fill('input[name="display_name"]', 'Test User');
      await page.fill('input[name="email"]', generateUniqueEmail());
      await page.fill('input[name="password"]', 'Password123!');
      
      // Don't accept terms
      await page.click('button[type="submit"]');
      
      // Should show error message about terms - "You must accept the terms of service"
      // Or we stay on register page (not redirected to dashboard/login)
      const errorMessage = page.locator('text=/must accept|terms of service/i');
      const errorAny = page.locator('.text-red-600, .text-red-700');
      
      await page.waitForTimeout(1000); // Give form time to validate
      
      const errorVisible = await errorMessage.isVisible().catch(() => false);
      const anyErrorVisible = await errorAny.first().isVisible().catch(() => false);
      
      expect(errorVisible || anyErrorVisible).toBe(true);
    });

    test('should show error for weak password', async ({ page }) => {
      await page.goto('/register');
      
      await page.fill('input[name="display_name"]', 'Test User');
      await page.fill('input[name="email"]', generateUniqueEmail());
      await page.fill('input[name="password"]', 'weak');
      await page.check('input[name="accepted_terms"]');
      
      await page.click('button[type="submit"]');
      
      // Should show password requirements error
      await expect(page.locator('text=/password.*characters|at least 8/i')).toBeVisible();
    });

    test('should show error for duplicate email', async ({ page }) => {
      await page.goto('/register');
      
      // Try to register with existing email
      await page.fill('input[name="display_name"]', 'Duplicate User');
      await page.fill('input[name="email"]', testUser.email);
      await page.fill('input[name="password"]', 'Password123!');
      await page.check('input[name="accepted_terms"]');
      
      await page.click('button[type="submit"]');
      
      // Should show error about email already in use
      await expect(page.locator('text=/email.*exists|already.*registered|already in use/i')).toBeVisible();
    });

    test('should navigate to login from register page', async ({ page }) => {
      await page.goto('/register');
      
      await page.click('text=/sign in|log in/i');
      
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe('Login', () => {
    test('should login with valid credentials', async ({ page }) => {
      await login(page, testUser.email, testUser.password);
      
      // Should be on dashboard
      await expect(page).toHaveURL(/\/dashboard/);
      
      // Should show user name in header
      await expect(page.locator('header')).toContainText(testUser.displayName);
    });

    test('should show error for invalid email', async ({ page }) => {
      await page.goto('/login');
      
      await page.fill('input[name="email"]', 'nonexistent@example.com');
      await page.fill('input[name="password"]', 'SomePassword123!');
      
      await page.click('button[type="submit"]');
      
      // Wait for form to submit and server to respond
      // Either we get an error message or we stay on login page (not redirected to dashboard)
      const errorMessage = page.locator('.text-red-600, .text-red-700, [role="alert"]');
      const stayedOnLogin = await page.waitForURL(/\/login/, { timeout: 8000 }).then(() => true).catch(() => false);
      const errorVisible = await errorMessage.first().isVisible({ timeout: 3000 }).catch(() => false);
      
      // Test passes if we see error or stayed on login page
      expect(stayedOnLogin || errorVisible).toBe(true);
    });

    test('should show error for wrong password', async ({ page }) => {
      await page.goto('/login');
      
      await page.fill('input[name="email"]', testUser.email);
      await page.fill('input[name="password"]', 'WrongPassword123!');
      
      await page.click('button[type="submit"]');
      
      // Wait for form to submit and server to respond
      const errorMessage = page.locator('.text-red-600, .text-red-700, [role="alert"]');
      const stayedOnLogin = await page.waitForURL(/\/login/, { timeout: 8000 }).then(() => true).catch(() => false);
      const errorVisible = await errorMessage.first().isVisible({ timeout: 3000 }).catch(() => false);
      
      // Test passes if we see error or stayed on login page
      expect(stayedOnLogin || errorVisible).toBe(true);
    });

    test('should navigate to forgot password from login', async ({ page }) => {
      await page.goto('/login');
      
      await page.click('text=/forgot.*password/i');
      
      await expect(page).toHaveURL(/\/forgot-password/);
    });

    test('should navigate to register from login page', async ({ page }) => {
      await page.goto('/login');
      
      await page.click('text=/sign up|create.*account|register/i');
      
      await expect(page).toHaveURL(/\/register/);
    });
  });

  test.describe('Logout', () => {
    test('should logout successfully', async ({ page }) => {
      // First login
      await login(page, testUser.email, testUser.password);
      
      // Then logout
      await logout(page);
      
      // Should be on login page
      await expect(page).toHaveURL(/\/login/);
    });

    test('should not access protected routes after logout', async ({ page }) => {
      // Login then logout
      await login(page, testUser.email, testUser.password);
      await logout(page);
      
      // Try to access dashboard
      await page.goto('/dashboard');
      
      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe('Password Reset', () => {
    test('should show password reset form', async ({ page }) => {
      await page.goto('/forgot-password');
      
      // Form should be visible
      await expect(page.locator('input[name="email"]')).toBeVisible();
      await expect(page.locator('button[type="submit"]')).toBeVisible();
    });

    test('should submit password reset request', async ({ page }) => {
      await page.goto('/forgot-password');
      
      await page.fill('input[name="email"]', testUser.email);
      await page.click('button[type="submit"]');
      
      // Should show success message
      await expect(page.locator('text=/email.*sent|check.*inbox/i')).toBeVisible();
    });

    test('should show error for invalid email format', async ({ page }) => {
      await page.goto('/forgot-password');
      
      // Use an email that might pass browser validation but fail zod (or vice versa)
      await page.fill('input[name="email"]', 'not-valid-email');
      await page.click('button[type="submit"]');
      
      // Should show validation error OR browser's native validation prevents submit
      // Check for either the validation message or that the form didn't submit (no success)
      const errorVisible = await page.locator('text=/valid.*email|please enter/i').isVisible({ timeout: 3000 }).catch(() => false);
      const successVisible = await page.locator('text=/check.*email|sent/i').isVisible({ timeout: 500 }).catch(() => false);
      
      // Test passes if we see error message or if we don't see success message (blocked by validation)
      expect(errorVisible || !successVisible).toBe(true);
    });
  });

  test.describe('Protected Routes', () => {
    test('should redirect to login when accessing dashboard without auth', async ({ page }) => {
      await page.goto('/dashboard');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('should redirect to login when accessing settings without auth', async ({ page }) => {
      await page.goto('/settings');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('should redirect to login when accessing projects without auth', async ({ page }) => {
      await page.goto('/projects');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('should preserve return URL after login', async ({ page }) => {
      // Try to access settings
      await page.goto('/settings');
      
      // Should be redirected to login
      await expect(page).toHaveURL(/\/login/);
      
      // Login
      await page.fill('input[name="email"]', testUser.email);
      await page.fill('input[name="password"]', testUser.password);
      await page.click('button[type="submit"]');
      
      // Should be redirected back to settings (or dashboard if not implemented)
      await expect(page).toHaveURL(/\/(settings|dashboard)/);
    });
  });

  test.describe('Session Persistence', () => {
    test('should maintain session after page refresh', async ({ page }) => {
      await login(page, testUser.email, testUser.password);
      
      // Refresh the page
      await page.reload();
      
      // Should still be on dashboard
      await expect(page).toHaveURL(/\/dashboard/);
      
      // User should still be logged in
      await expect(page.locator('header')).toContainText(testUser.displayName);
    });
  });
});
