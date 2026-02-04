import { test as setup } from '@playwright/test';

/**
 * Global setup for E2E tests.
 * Seeds test data and performs any required initialization.
 */

// Test user credentials
const TEST_USER = {
  email: 'e2e-test@example.com',
  password: 'TestPassword123!',
  displayName: 'E2E Test User',
};

const ADMIN_USER = {
  email: 'e2e-admin@example.com',
  password: 'AdminPassword123!',
  displayName: 'E2E Admin User',
};

setup('seed test database', async ({ request }) => {
  const baseURL = process.env.PLAYWRIGHT_API_URL || 'http://localhost:8000';

  // Check if test users already exist, if not create them
  try {
    // Try to register test user (will fail if already exists, which is fine)
    await request.post(`${baseURL}/api/v1/auth/register`, {
      data: {
        email: TEST_USER.email,
        password: TEST_USER.password,
        display_name: TEST_USER.displayName,
      },
    });
  } catch (e) {
    // User may already exist, continue
  }

  try {
    // Try to register admin user
    await request.post(`${baseURL}/api/v1/auth/register`, {
      data: {
        email: ADMIN_USER.email,
        password: ADMIN_USER.password,
        display_name: ADMIN_USER.displayName,
      },
    });
  } catch (e) {
    // User may already exist, continue
  }

  // Force-verify test users (dev endpoint)
  try {
    await request.post(`${baseURL}/api/v1/auth/dev/verify-user`, {
      data: { email: TEST_USER.email },
    });
    await request.post(`${baseURL}/api/v1/auth/dev/verify-user`, {
      data: { email: ADMIN_USER.email },
    });
  } catch (e) {
    // Verification may fail if users don't exist, continue
    console.log('Note: Could not force-verify users (may already be verified)');
  }

  console.log('✅ Test database seeded');
});

setup('verify API is running', async ({ request }) => {
  const baseURL = process.env.PLAYWRIGHT_API_URL || 'http://localhost:8000';

  const response = await request.get(`${baseURL}/api/v1/health`);
  
  if (!response.ok()) {
    throw new Error(`API health check failed: ${response.status()}`);
  }

  console.log('✅ API is running');
});
