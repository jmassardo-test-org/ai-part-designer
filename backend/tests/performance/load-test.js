/**
 * Performance Testing Script using k6
 * 
 * Run with: k6 run tests/performance/load-test.js
 * 
 * Prerequisites:
 * - Install k6: brew install k6
 * - Start the backend API server
 * - Set BASE_URL environment variable if not localhost
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// =============================================================================
// Configuration
// =============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_URL = `${BASE_URL}/api/v1`;

// Custom metrics
const errorRate = new Rate('errors');
const authDuration = new Trend('auth_duration');
const designDuration = new Trend('design_duration');
const templateDuration = new Trend('template_duration');

// Test configuration for 100 concurrent users
export const options = {
  stages: [
    { duration: '30s', target: 20 },   // Ramp up to 20 users
    { duration: '1m', target: 50 },    // Ramp up to 50 users
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '3m', target: 100 },   // Stay at 100 users
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests under 500ms
    'http_req_duration{name:auth}': ['p(95)<300'],
    'http_req_duration{name:designs}': ['p(95)<500'],
    'http_req_duration{name:templates}': ['p(95)<400'],
    errors: ['rate<0.01'],  // Error rate under 1%
  },
};

// =============================================================================
// Helper Functions
// =============================================================================

function getAuthHeaders(token) {
  return {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  };
}

function randomEmail() {
  return `perf-test-${Date.now()}-${Math.random().toString(36).substring(7)}@example.com`;
}

// =============================================================================
// Test Scenarios
// =============================================================================

export default function () {
  let authToken = null;

  group('Authentication', () => {
    // Login
    const loginPayload = JSON.stringify({
      email: 'perf-test@example.com',
      password: 'TestPassword123!',
    });

    const loginStart = Date.now();
    const loginRes = http.post(`${API_URL}/auth/login`, loginPayload, {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'auth' },
    });
    authDuration.add(Date.now() - loginStart);

    const loginSuccess = check(loginRes, {
      'login status is 200': (r) => r.status === 200,
      'login has access_token': (r) => r.json('access_token') !== undefined,
    });

    errorRate.add(!loginSuccess);

    if (loginSuccess) {
      authToken = loginRes.json('access_token');
    }
  });

  if (!authToken) {
    console.log('Authentication failed, skipping remaining tests');
    return;
  }

  const headers = getAuthHeaders(authToken);

  group('Dashboard & Designs', () => {
    // Get user's designs
    const designStart = Date.now();
    const designsRes = http.get(`${API_URL}/designs?limit=10`, {
      ...headers,
      tags: { name: 'designs' },
    });
    designDuration.add(Date.now() - designStart);

    const designsSuccess = check(designsRes, {
      'designs status is 200': (r) => r.status === 200,
      'designs returns array': (r) => Array.isArray(r.json('items') || r.json()),
    });

    errorRate.add(!designsSuccess);

    sleep(0.5);

    // Get single design detail (if designs exist)
    const designs = designsRes.json('items') || designsRes.json() || [];
    if (designs.length > 0) {
      const designId = designs[0].id;
      const detailRes = http.get(`${API_URL}/designs/${designId}`, {
        ...headers,
        tags: { name: 'designs' },
      });

      check(detailRes, {
        'design detail status is 200': (r) => r.status === 200,
      });
    }
  });

  group('Templates', () => {
    // Get templates
    const templateStart = Date.now();
    const templatesRes = http.get(`${API_URL}/templates?limit=20`, {
      ...headers,
      tags: { name: 'templates' },
    });
    templateDuration.add(Date.now() - templateStart);

    const templatesSuccess = check(templatesRes, {
      'templates status is 200': (r) => r.status === 200,
    });

    errorRate.add(!templatesSuccess);

    sleep(0.3);

    // Get template categories
    const categoriesRes = http.get(`${API_URL}/templates/categories`, {
      ...headers,
      tags: { name: 'templates' },
    });

    check(categoriesRes, {
      'categories status is 200 or 404': (r) => [200, 404].includes(r.status),
    });
  });

  group('User Profile', () => {
    // Get current user
    const meRes = http.get(`${API_URL}/users/me`, {
      ...headers,
      tags: { name: 'auth' },
    });

    check(meRes, {
      'me status is 200': (r) => r.status === 200,
      'me has user data': (r) => r.json('email') !== undefined,
    });

    sleep(0.3);

    // Get subscription status
    const subRes = http.get(`${API_URL}/subscriptions/current`, {
      ...headers,
      tags: { name: 'subscription' },
    });

    check(subRes, {
      'subscription status is 200 or 404': (r) => [200, 404].includes(r.status),
    });
  });

  group('Notifications', () => {
    // Get notifications
    const notifRes = http.get(`${API_URL}/notifications?limit=20`, {
      ...headers,
      tags: { name: 'notifications' },
    });

    check(notifRes, {
      'notifications status is 200': (r) => r.status === 200,
    });
  });

  group('Projects', () => {
    // Get projects
    const projectsRes = http.get(`${API_URL}/projects?limit=10`, {
      ...headers,
      tags: { name: 'projects' },
    });

    check(projectsRes, {
      'projects status is 200': (r) => r.status === 200,
    });
  });

  // Simulate user think time
  sleep(Math.random() * 2 + 1);
}

// =============================================================================
// Teardown
// =============================================================================

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data, null, 2),
    stdout: generateTextSummary(data),
  };
}

function generateTextSummary(data) {
  const { metrics } = data;
  
  return `
================================================================================
                        PERFORMANCE TEST RESULTS
================================================================================

Test Duration: ${Math.round(data.state.testRunDurationMs / 1000)}s
Virtual Users: ${data.metrics.vus_max ? data.metrics.vus_max.values.max : 'N/A'}

HTTP Request Duration (p95):
  - Overall: ${Math.round(metrics.http_req_duration?.values?.['p(95)'] || 0)}ms
  - Auth:    ${Math.round(metrics['http_req_duration{name:auth}']?.values?.['p(95)'] || 0)}ms
  - Designs: ${Math.round(metrics['http_req_duration{name:designs}']?.values?.['p(95)'] || 0)}ms
  - Templates: ${Math.round(metrics['http_req_duration{name:templates}']?.values?.['p(95)'] || 0)}ms

Request Statistics:
  - Total Requests: ${metrics.http_reqs?.values?.count || 0}
  - Failed Requests: ${metrics.http_req_failed?.values?.passes || 0}
  - Error Rate: ${((metrics.errors?.values?.rate || 0) * 100).toFixed(2)}%

Custom Metrics:
  - Auth Duration (avg): ${Math.round(metrics.auth_duration?.values?.avg || 0)}ms
  - Design Duration (avg): ${Math.round(metrics.design_duration?.values?.avg || 0)}ms
  - Template Duration (avg): ${Math.round(metrics.template_duration?.values?.avg || 0)}ms

Threshold Results:
${Object.entries(data.thresholds || {}).map(([name, result]) => 
  `  - ${name}: ${result.ok ? '✅ PASS' : '❌ FAIL'}`
).join('\n')}

================================================================================
`;
}
