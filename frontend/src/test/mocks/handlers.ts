/**
 * MSW handlers for API mocking.
 * 
 * Defines mock responses for all API endpoints used in tests.
 */

import { http, HttpResponse } from 'msw';

const API_BASE = '/api/v1';

// Mock user data
export const mockUser = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  email: 'test@example.com',
  display_name: 'Test User',
  role: 'user',
  status: 'active',
  email_verified_at: '2024-01-01T00:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
};

export const mockTokens = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
  expires_in: 3600,
};

export const handlers = [
  // ==========================================================================
  // Auth Endpoints
  // ==========================================================================
  
  // Login
  http.post(`${API_BASE}/auth/login`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string };
    
    if (body.email === 'test@example.com' && body.password === 'password123') {
      return HttpResponse.json({
        ...mockTokens,
        user: mockUser,
      });
    }
    
    return HttpResponse.json(
      { detail: 'Invalid email or password' },
      { status: 401 }
    );
  }),
  
  // Register
  http.post(`${API_BASE}/auth/register`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string; display_name: string };
    
    if (body.email === 'existing@example.com') {
      return HttpResponse.json(
        { detail: 'Email already registered' },
        { status: 400 }
      );
    }
    
    return HttpResponse.json({
      ...mockTokens,
      user: {
        ...mockUser,
        email: body.email,
        display_name: body.display_name,
      },
    }, { status: 201 });
  }),
  
  // Get current user
  http.get(`${API_BASE}/auth/me`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    return HttpResponse.json(mockUser);
  }),
  
  // Refresh token
  http.post(`${API_BASE}/auth/refresh`, () => {
    return HttpResponse.json(mockTokens);
  }),
  
  // Logout
  http.post(`${API_BASE}/auth/logout`, () => {
    return HttpResponse.json({ message: 'Logged out successfully' });
  }),
  
  // Forgot password
  http.post(`${API_BASE}/auth/forgot-password`, () => {
    return HttpResponse.json({ message: 'Reset email sent' });
  }),
  
  // Reset password
  http.post(`${API_BASE}/auth/reset-password`, () => {
    return HttpResponse.json({ message: 'Password reset successfully' });
  }),
  
  // Verify email
  http.post(`${API_BASE}/auth/verify-email`, () => {
    return HttpResponse.json({ message: 'Email verified' });
  }),
  
  // ==========================================================================
  // Templates Endpoints
  // ==========================================================================
  
  http.get(`${API_BASE}/templates`, () => {
    return HttpResponse.json({
      templates: [
        {
          id: '1',
          name: 'Simple Box',
          slug: 'simple-box',
          category: 'mechanical',
          description: 'A simple parametric box',
          tier_required: 'free',
          thumbnail_url: null,
          usage_count: 100,
        },
        {
          id: '2',
          name: 'Mounting Bracket',
          slug: 'mounting-bracket',
          category: 'mechanical',
          description: 'L-shaped mounting bracket',
          tier_required: 'free',
          thumbnail_url: null,
          usage_count: 50,
        },
      ],
      total: 2,
      categories: ['mechanical', 'enclosures'],
    });
  }),
  
  http.get(`${API_BASE}/templates/:slug`, ({ params }) => {
    const { slug } = params;
    
    if (slug === 'not-found') {
      return HttpResponse.json(
        { detail: 'Template not found' },
        { status: 404 }
      );
    }
    
    return HttpResponse.json({
      id: '1',
      name: 'Simple Box',
      slug: slug,
      category: 'mechanical',
      description: 'A simple parametric box',
      tier_required: 'free',
      thumbnail_url: null,
      preview_url: null,
      parameters: {
        length: { type: 'number', label: 'Length', default: 100, min: 1, max: 500, unit: 'mm' },
        width: { type: 'number', label: 'Width', default: 50, min: 1, max: 500, unit: 'mm' },
        height: { type: 'number', label: 'Height', default: 30, min: 1, max: 500, unit: 'mm' },
      },
      usage_count: 100,
    });
  }),
  
  // ==========================================================================
  // Files Endpoints
  // ==========================================================================
  
  http.get(`${API_BASE}/files`, () => {
    return HttpResponse.json({
      files: [],
      total: 0,
      skip: 0,
      limit: 20,
      has_more: false,
      total_size_bytes: 0,
    });
  }),
  
  http.get(`${API_BASE}/files/quota`, () => {
    return HttpResponse.json({
      used_bytes: 0,
      limit_bytes: 104857600,
      file_count: 0,
      remaining_bytes: 104857600,
      usage_percent: 0,
    });
  }),
  
  // ==========================================================================
  // Jobs Endpoints
  // ==========================================================================
  
  http.get(`${API_BASE}/jobs`, () => {
    return HttpResponse.json({
      jobs: [],
      total: 0,
      skip: 0,
      limit: 20,
      has_more: false,
    });
  }),
  
  // ==========================================================================
  // Dashboard Endpoints
  // ==========================================================================
  
  http.get(`${API_BASE}/dashboard/stats`, () => {
    return HttpResponse.json({
      project_count: 0,
      design_count: 0,
      generations_this_month: 0,
      storage_used_bytes: 0,
    });
  }),
  
  http.get(`${API_BASE}/dashboard/recent`, () => {
    return HttpResponse.json({
      designs: [],
    });
  }),
];
