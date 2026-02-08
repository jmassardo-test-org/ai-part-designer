import { test, expect, Page } from '@playwright/test';
import { generateUniqueEmail, login } from './fixtures';

/**
 * E2E Tests for Organization RBAC.
 * 
 * Tests verify that role-based access control is properly enforced
 * in the UI and backend for organization operations.
 */

// Helper to create a test user
async function createTestUser(page: Page, role: string) {
  const email = generateUniqueEmail();
  const password = 'SecurePassword123!';
  const displayName = `Test ${role} User`;

  // Register user
  await page.goto('/register');
  await page.fill('input[name="display_name"]', displayName);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.check('input[name="accepted_terms"]');
  await page.click('button[type="submit"]');

  // Wait for registration to complete
  await page.waitForTimeout(2000);

  return { email, password, displayName };
}

// Helper to create organization
async function createOrganization(page: Page, name: string, slug: string) {
  await page.goto('/organizations/new');
  await page.fill('input[name="name"]', name);
  await page.fill('input[name="slug"]', slug);
  await page.click('button[type="submit"]');
  
  // Wait for creation and capture org ID from URL
  await page.waitForURL(/\/organizations\/[a-f0-9-]+/);
  const url = page.url();
  const orgId = url.match(/\/organizations\/([a-f0-9-]+)/)?.[1];
  
  return orgId;
}

test.describe('Organization RBAC', () => {
  test.describe('Owner Permissions', () => {
    test('owner can view, update, and delete organization', async ({ page }) => {
      // Create owner account and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `RBAC Test Org ${Date.now()}`;
      const orgSlug = `rbac-test-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);
      
      if (!orgId) {
        throw new Error('Failed to create organization');
      }

      // Verify owner can view organization
      await page.goto(`/organizations/${orgId}`);
      await expect(page.locator('h1')).toContainText(orgName);

      // Verify owner can update organization
      await page.click('button:has-text("Settings")');
      await page.fill('input[name="name"]', `${orgName} Updated`);
      await page.click('button:has-text("Save")');
      await expect(page.locator('text=Organization updated')).toBeVisible();

      // Verify owner can see delete option
      await expect(page.locator('button:has-text("Delete Organization")')).toBeVisible();

      // Verify owner can invite members
      await page.goto(`/organizations/${orgId}/members`);
      await expect(page.locator('button:has-text("Invite Member")')).toBeVisible();
    });

    test('owner can transfer ownership', async ({ page, context }) => {
      // Create owner and future owner accounts
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Transfer Test ${Date.now()}`;
      const orgSlug = `transfer-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);

      // Create second user in new tab
      const newOwnerPage = await context.newPage();
      const newOwner = await createTestUser(newOwnerPage, 'NewOwner');
      
      // Invite new owner as admin first
      await page.goto(`/organizations/${orgId}/members`);
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', newOwner.email);
      await page.selectOption('select[name="role"]', 'admin');
      await page.click('button:has-text("Send Invitation")');
      
      // New owner accepts invite
      await login(newOwnerPage, newOwner.email, newOwner.password);
      await newOwnerPage.goto('/invitations');
      await newOwnerPage.click(`button:has-text("Accept")`);
      
      // Transfer ownership
      await page.goto(`/organizations/${orgId}/settings`);
      await page.click('button:has-text("Transfer Ownership")');
      await page.selectOption('select[name="new_owner"]', newOwner.email);
      await page.click('button:has-text("Confirm Transfer")');
      
      await expect(page.locator('text=Ownership transferred')).toBeVisible();
      
      // Verify original owner is now admin
      await page.goto(`/organizations/${orgId}/members`);
      const ownerRow = page.locator(`tr:has-text("${owner.email}")`);
      await expect(ownerRow.locator('td:has-text("admin")')).toBeVisible();
      
      await newOwnerPage.close();
    });
  });

  test.describe('Admin Permissions', () => {
    test('admin can update org but not delete', async ({ page, context }) => {
      // Create owner and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Admin Test ${Date.now()}`;
      const orgSlug = `admin-test-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);

      // Create admin user
      const adminPage = await context.newPage();
      const admin = await createTestUser(adminPage, 'Admin');
      
      // Invite admin
      await page.goto(`/organizations/${orgId}/members`);
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', admin.email);
      await page.selectOption('select[name="role"]', 'admin');
      await page.click('button:has-text("Send Invitation")');
      
      // Admin accepts and logs in
      await login(adminPage, admin.email, admin.password);
      await adminPage.goto('/invitations');
      await adminPage.click(`button:has-text("Accept")`);
      
      // Verify admin can view and update
      await adminPage.goto(`/organizations/${orgId}`);
      await adminPage.click('button:has-text("Settings")');
      await adminPage.fill('input[name="description"]', 'Updated by admin');
      await adminPage.click('button:has-text("Save")');
      await expect(adminPage.locator('text=Organization updated')).toBeVisible();
      
      // Verify admin CANNOT delete organization
      await expect(adminPage.locator('button:has-text("Delete Organization")')).not.toBeVisible();
      
      // Verify admin can invite members
      await adminPage.goto(`/organizations/${orgId}/members`);
      await expect(adminPage.locator('button:has-text("Invite Member")')).toBeVisible();
      
      // Verify admin can change member roles
      await expect(adminPage.locator('button:has-text("Change Role")')).toBeVisible();
      
      await adminPage.close();
    });

    test('admin cannot transfer ownership', async ({ page, context }) => {
      // Setup owner and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Transfer Deny Test ${Date.now()}`;
      const orgSlug = `transfer-deny-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);

      // Create admin
      const adminPage = await context.newPage();
      const admin = await createTestUser(adminPage, 'Admin');
      
      await page.goto(`/organizations/${orgId}/members`);
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', admin.email);
      await page.selectOption('select[name="role"]', 'admin');
      await page.click('button:has-text("Send Invitation")');
      
      await login(adminPage, admin.email, admin.password);
      await adminPage.goto('/invitations');
      await adminPage.click(`button:has-text("Accept")`);
      
      // Verify admin cannot see transfer ownership option
      await adminPage.goto(`/organizations/${orgId}/settings`);
      await expect(adminPage.locator('button:has-text("Transfer Ownership")')).not.toBeVisible();
      
      await adminPage.close();
    });
  });

  test.describe('Member Permissions', () => {
    test('member can view but not update organization', async ({ page, context }) => {
      // Create owner and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Member Test ${Date.now()}`;
      const orgSlug = `member-test-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);

      // Create member user
      const memberPage = await context.newPage();
      const member = await createTestUser(memberPage, 'Member');
      
      await page.goto(`/organizations/${orgId}/members`);
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', member.email);
      await page.selectOption('select[name="role"]', 'member');
      await page.click('button:has-text("Send Invitation")');
      
      await login(memberPage, member.email, member.password);
      await memberPage.goto('/invitations');
      await memberPage.click(`button:has-text("Accept")`);
      
      // Member can view organization
      await memberPage.goto(`/organizations/${orgId}`);
      await expect(memberPage.locator('h1')).toContainText(orgName);
      
      // Member can view members list
      await memberPage.goto(`/organizations/${orgId}/members`);
      await expect(memberPage.locator('text=Members')).toBeVisible();
      
      // Member CANNOT update org settings
      await memberPage.goto(`/organizations/${orgId}`);
      await expect(memberPage.locator('button:has-text("Settings")')).not.toBeVisible();
      
      // Member CANNOT invite others
      await memberPage.goto(`/organizations/${orgId}/members`);
      await expect(memberPage.locator('button:has-text("Invite Member")')).not.toBeVisible();
      
      // Member CANNOT change roles
      await expect(memberPage.locator('button:has-text("Change Role")')).not.toBeVisible();
      
      await memberPage.close();
    });

    test('member can leave organization', async ({ page, context }) => {
      // Create owner and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Leave Test ${Date.now()}`;
      const orgSlug = `leave-test-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);

      // Create member
      const memberPage = await context.newPage();
      const member = await createTestUser(memberPage, 'Member');
      
      await page.goto(`/organizations/${orgId}/members`);
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', member.email);
      await page.selectOption('select[name="role"]', 'member');
      await page.click('button:has-text("Send Invitation")');
      
      await login(memberPage, member.email, member.password);
      await memberPage.goto('/invitations');
      await memberPage.click(`button:has-text("Accept")`);
      
      // Member leaves organization
      await memberPage.goto(`/organizations/${orgId}/members`);
      await memberPage.click('button:has-text("Leave Organization")');
      await memberPage.click('button:has-text("Confirm")');
      
      await expect(memberPage.locator('text=You have left')).toBeVisible();
      
      // Verify member no longer in org
      await memberPage.goto(`/organizations/${orgId}`);
      await expect(memberPage.locator('text=Not found')).toBeVisible();
      
      await memberPage.close();
    });
  });

  test.describe('Viewer Permissions', () => {
    test('viewer has read-only access', async ({ page, context }) => {
      // Create owner and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Viewer Test ${Date.now()}`;
      const orgSlug = `viewer-test-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);

      // Create viewer user
      const viewerPage = await context.newPage();
      const viewer = await createTestUser(viewerPage, 'Viewer');
      
      await page.goto(`/organizations/${orgId}/members`);
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', viewer.email);
      await page.selectOption('select[name="role"]', 'viewer');
      await page.click('button:has-text("Send Invitation")');
      
      await login(viewerPage, viewer.email, viewer.password);
      await viewerPage.goto('/invitations');
      await viewerPage.click(`button:has-text("Accept")`);
      
      // Viewer can view organization
      await viewerPage.goto(`/organizations/${orgId}`);
      await expect(viewerPage.locator('h1')).toContainText(orgName);
      
      // Viewer can view members
      await viewerPage.goto(`/organizations/${orgId}/members`);
      await expect(viewerPage.locator('text=Members')).toBeVisible();
      
      // Viewer CANNOT access settings
      await expect(viewerPage.locator('button:has-text("Settings")')).not.toBeVisible();
      
      // Viewer CANNOT invite members
      await expect(viewerPage.locator('button:has-text("Invite Member")')).not.toBeVisible();
      
      // Viewer CANNOT change roles
      await expect(viewerPage.locator('button:has-text("Change Role")')).not.toBeVisible();
      
      // Viewer CANNOT remove members
      await expect(viewerPage.locator('button:has-text("Remove")')).not.toBeVisible();
      
      await viewerPage.close();
    });
  });

  test.describe('Non-Member Access', () => {
    test('non-member cannot access organization', async ({ page, context }) => {
      // Create owner and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Private Org ${Date.now()}`;
      const orgSlug = `private-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);

      // Create outsider user
      const outsiderPage = await context.newPage();
      const outsider = await createTestUser(outsiderPage, 'Outsider');
      await login(outsiderPage, outsider.email, outsider.password);
      
      // Try to access organization
      await outsiderPage.goto(`/organizations/${orgId}`);
      await expect(outsiderPage.locator('text=/not found|access denied|forbidden/i')).toBeVisible();
      
      // Try to access members
      await outsiderPage.goto(`/organizations/${orgId}/members`);
      await expect(outsiderPage.locator('text=/not found|access denied|forbidden/i')).toBeVisible();
      
      // Try to access settings
      await outsiderPage.goto(`/organizations/${orgId}/settings`);
      await expect(outsiderPage.locator('text=/not found|access denied|forbidden/i')).toBeVisible();
      
      await outsiderPage.close();
    });
  });

  test.describe('Privilege Escalation Prevention', () => {
    test('admin cannot escalate member to owner via UI', async ({ page, context }) => {
      // Create owner and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Escalation Test ${Date.now()}`;
      const orgSlug = `escalation-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);

      // Create admin and member
      const adminPage = await context.newPage();
      const admin = await createTestUser(adminPage, 'Admin');
      
      const memberPage = await context.newPage();
      const member = await createTestUser(memberPage, 'Member');
      
      // Invite both
      await page.goto(`/organizations/${orgId}/members`);
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', admin.email);
      await page.selectOption('select[name="role"]', 'admin');
      await page.click('button:has-text("Send Invitation")');
      
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', member.email);
      await page.selectOption('select[name="role"]', 'member');
      await page.click('button:has-text("Send Invitation")');
      
      // Both accept
      await login(adminPage, admin.email, admin.password);
      await adminPage.goto('/invitations');
      await adminPage.click(`button:has-text("Accept")`);
      
      await login(memberPage, member.email, member.password);
      await memberPage.goto('/invitations');
      await memberPage.click(`button:has-text("Accept")`);
      
      // Admin tries to change member to owner
      await adminPage.goto(`/organizations/${orgId}/members`);
      const memberRow = adminPage.locator(`tr:has-text("${member.email}")`);
      await memberRow.locator('button:has-text("Change Role")').click();
      
      // "Owner" option should not be available
      const roleSelect = adminPage.locator('select[name="role"]');
      const ownerOption = roleSelect.locator('option[value="owner"]');
      await expect(ownerOption).not.toBeVisible();
      
      await adminPage.close();
      await memberPage.close();
    });

    test('admin cannot remove or demote owner', async ({ page, context }) => {
      // Create owner and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Owner Protection ${Date.now()}`;
      const orgSlug = `owner-protect-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);

      // Create admin
      const adminPage = await context.newPage();
      const admin = await createTestUser(adminPage, 'Admin');
      
      await page.goto(`/organizations/${orgId}/members`);
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', admin.email);
      await page.selectOption('select[name="role"]', 'admin');
      await page.click('button:has-text("Send Invitation")');
      
      await login(adminPage, admin.email, admin.password);
      await adminPage.goto('/invitations');
      await adminPage.click(`button:has-text("Accept")`);
      
      // Admin views members
      await adminPage.goto(`/organizations/${orgId}/members`);
      const ownerRow = adminPage.locator(`tr:has-text("${owner.email}")`);
      
      // Owner row should not have "Change Role" or "Remove" buttons
      await expect(ownerRow.locator('button:has-text("Change Role")')).not.toBeVisible();
      await expect(ownerRow.locator('button:has-text("Remove")')).not.toBeVisible();
      
      await adminPage.close();
    });

    test('invite enforces member limit', async ({ page }) => {
      // Create owner
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      // Create org with limit of 2 members (owner + 1)
      const orgName = `Limited Org ${Date.now()}`;
      const orgSlug = `limited-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);
      
      // Update max_members to 2 (via settings if available, or via API)
      // For this test, assume we can set it during creation or via settings
      await page.goto(`/organizations/${orgId}/settings`);
      await page.fill('input[name="max_members"]', '2');
      await page.click('button:has-text("Save")');
      
      // Invite first member (should succeed)
      await page.goto(`/organizations/${orgId}/members`);
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', 'first@example.com');
      await page.click('button:has-text("Send Invitation")');
      await expect(page.locator('text=Invitation sent')).toBeVisible();
      
      // Try to invite second member (should fail - limit reached)
      await page.click('button:has-text("Invite Member")');
      await page.fill('input[name="email"]', 'second@example.com');
      await page.click('button:has-text("Send Invitation")');
      await expect(page.locator('text=/limit|maximum/i')).toBeVisible();
    });
  });

  test.describe('Audit Trail', () => {
    test('organization actions are logged', async ({ page }) => {
      // Create owner and org
      const owner = await createTestUser(page, 'Owner');
      await login(page, owner.email, owner.password);
      
      const orgName = `Audit Test ${Date.now()}`;
      const orgSlug = `audit-${Date.now()}`;
      const orgId = await createOrganization(page, orgName, orgSlug);
      
      // Perform various actions
      await page.goto(`/organizations/${orgId}`);
      await page.click('button:has-text("Settings")');
      await page.fill('input[name="description"]', 'Updated description');
      await page.click('button:has-text("Save")');
      
      // View audit log
      await page.goto(`/organizations/${orgId}/audit-log`);
      
      // Verify key actions are logged
      await expect(page.locator('text=organization_created')).toBeVisible();
      await expect(page.locator('text=organization_updated')).toBeVisible();
    });
  });
});
