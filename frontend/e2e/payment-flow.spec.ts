import { test, expect } from '@playwright/test';
import { testUser, login, waitForLoading } from './fixtures';

/**
 * E2E Tests for Payment & Subscription Flows.
 * Tests: Pricing page, Checkout flow, Billing management.
 * 
 * Note: Actual Stripe checkout is tested in test mode.
 * These tests verify the UI flow up to and after Stripe redirect.
 */

test.describe('Payment & Subscription', () => {
  test.describe('Pricing Page', () => {
    test('should display pricing page with all tiers', async ({ page }) => {
      await page.goto('/pricing');
      await waitForLoading(page);

      // Should show pricing title
      await expect(page.locator('h1')).toContainText(/pricing/i);

      // Should show Free, Pro, and Enterprise tiers
      await expect(page.locator('text=/free/i').first()).toBeVisible();
      await expect(page.locator('text=/pro/i').first()).toBeVisible();
      await expect(page.locator('text=/enterprise/i').first()).toBeVisible();
    });

    test('should show plan comparison features', async ({ page }) => {
      await page.goto('/pricing');
      await waitForLoading(page);

      // Should show key feature comparisons
      const features = [
        /designs|generation/i,
        /export|download/i,
      ];

      for (const feature of features) {
        await expect(page.locator(`text=${feature}`).first()).toBeVisible();
      }
    });

    test('should toggle between monthly and yearly billing', async ({ page }) => {
      await page.goto('/pricing');
      await waitForLoading(page);

      // Look for billing toggle
      const billingToggle = page.locator(
        '[data-testid="billing-toggle"], button:has-text("Yearly"), button:has-text("Monthly")'
      );

      if (await billingToggle.first().isVisible()) {
        // Click yearly
        await billingToggle.filter({ hasText: /yearly|annual/i }).first().click();
        
        // Should update prices (yearly should show savings)
        await expect(page.locator('text=/save|year/i').first()).toBeVisible();
      }
    });

    test('should require login to start checkout', async ({ page }) => {
      await page.goto('/pricing');
      await waitForLoading(page);

      // Click upgrade button for Pro (without being logged in)
      const upgradeButton = page.locator('button:has-text("Upgrade"), button:has-text("Get Pro")').first();
      
      if (await upgradeButton.isVisible()) {
        await upgradeButton.click();

        // Should redirect to login
        await expect(page).toHaveURL(/\/(login|register)/);
      }
    });
  });

  test.describe('Checkout Flow', () => {
    test.beforeEach(async ({ page }) => {
      await login(page, testUser.email, testUser.password);
    });

    test('should navigate to pricing from dashboard', async ({ page }) => {
      await page.goto('/dashboard');
      await waitForLoading(page);

      // Look for upgrade button or pricing link
      const pricingLink = page.locator('a:has-text("Pricing"), a:has-text("Upgrade")').first();
      
      if (await pricingLink.isVisible()) {
        await pricingLink.click();
        await expect(page).toHaveURL(/\/pricing/);
      } else {
        // Navigate directly
        await page.goto('/pricing');
        await expect(page).toHaveURL(/\/pricing/);
      }
    });

    test('should highlight current plan when logged in', async ({ page }) => {
      await page.goto('/pricing');
      await waitForLoading(page);

      // Current plan should be indicated
      const currentPlanIndicator = page.locator(
        'text=/current plan|your plan/i, [data-current="true"]'
      );

      // Either shows current plan or upgrade buttons
      const upgradeButtons = page.locator('button:has-text("Upgrade")');
      const hasIndicator = await currentPlanIndicator.first().isVisible().catch(() => false);
      const hasButtons = await upgradeButtons.first().isVisible().catch(() => false);

      expect(hasIndicator || hasButtons).toBe(true);
    });

    test('should initiate checkout for Pro plan', async ({ page }) => {
      await page.goto('/pricing');
      await waitForLoading(page);

      // Click Pro upgrade button
      const proCard = page.locator('[data-testid="plan-pro"], :has(h3:text("Pro"))');
      const upgradeButton = proCard.locator('button:has-text("Upgrade"), button:has-text("Get Started")');

      if (await upgradeButton.isVisible()) {
        // Listen for navigation (Stripe redirect)
        const navigationPromise = page.waitForEvent('request', (req) =>
          req.url().includes('checkout.stripe.com') || req.url().includes('/checkout')
        ).catch(() => null);

        await upgradeButton.click();

        // Should either redirect to Stripe or show checkout modal
        const stripeRedirect = await navigationPromise;
        const checkoutModal = page.locator('[data-testid="checkout-modal"]');

        expect(stripeRedirect || await checkoutModal.isVisible().catch(() => false)).toBeTruthy();
      }
    });
  });

  test.describe('Billing Management', () => {
    test.beforeEach(async ({ page }) => {
      await login(page, testUser.email, testUser.password);
    });

    test('should access usage and billing page', async ({ page }) => {
      await page.goto('/settings/billing');
      await waitForLoading(page);

      // Should show billing section
      await expect(page.locator('h1, h2').filter({ hasText: /billing|subscription/i })).toBeVisible();
    });

    test('should display current subscription status', async ({ page }) => {
      await page.goto('/settings/billing');
      await waitForLoading(page);

      // Should show current plan info
      const planInfo = page.locator('text=/free|pro|enterprise/i').first();
      await expect(planInfo).toBeVisible();
    });

    test('should show usage statistics', async ({ page }) => {
      await page.goto('/settings/billing');
      await waitForLoading(page);

      // Should show usage metrics
      const usageSection = page.locator(
        '[data-testid="usage-stats"], text=/designs.*used|generation/i'
      );

      // Either shows usage or placeholder for free tier
      const hasUsage = await usageSection.first().isVisible().catch(() => false);
      const hasPlan = await page.locator('text=/free|subscription/i').first().isVisible().catch(() => false);

      expect(hasUsage || hasPlan).toBe(true);
    });

    test('should access billing portal button', async ({ page }) => {
      await page.goto('/settings/billing');
      await waitForLoading(page);

      // Look for billing portal button (only for paying customers)
      const portalButton = page.locator(
        'button:has-text("Manage Billing"), button:has-text("Update Payment")'
      );

      if (await portalButton.isVisible()) {
        // Should be clickable
        await expect(portalButton).toBeEnabled();
      }
    });
  });

  test.describe('Checkout Success/Cancel', () => {
    test('should show success page after payment', async ({ page }) => {
      // Simulate success return from Stripe
      await page.goto('/checkout/success?session_id=test_session');
      await waitForLoading(page);

      // Should show success message
      const successIndicator = page.locator(
        'text=/thank you|success|welcome to pro/i, [data-testid="checkout-success"]'
      );
      const hasSuccess = await successIndicator.first().isVisible().catch(() => false);

      // Or redirect to dashboard
      const isDashboard = page.url().includes('/dashboard');

      expect(hasSuccess || isDashboard).toBe(true);
    });

    test('should handle canceled checkout', async ({ page }) => {
      await page.goto('/checkout/cancel');
      await waitForLoading(page);

      // Should show cancel message or redirect to pricing
      const cancelMessage = page.locator('text=/cancel|try again/i');
      const hasCancelMessage = await cancelMessage.first().isVisible().catch(() => false);
      const isPricing = page.url().includes('/pricing');

      expect(hasCancelMessage || isPricing).toBe(true);
    });
  });
});
