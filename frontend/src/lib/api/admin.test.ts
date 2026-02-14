/**
 * Admin API Service Tests.
 *
 * Unit tests for admin API client functions.
 */

import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import {
  adminAnalyticsApi,
  adminUserApi,
  adminProjectApi,
  adminDesignApi,
  adminTemplateApi,
  adminJobApi,
  adminModerationApi,
  adminApi,
} from './admin';
import { apiClient } from './client';

// Mock the API client
vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockApiClient = apiClient as unknown as {
  get: Mock;
  post: Mock;
  patch: Mock;
  delete: Mock;
};

describe('adminAnalyticsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getOverview', () => {
    it('fetches analytics overview', async () => {
      const mockData = {
        total_users: 100,
        active_users_today: 25,
        total_projects: 50,
      };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminAnalyticsApi.getOverview();

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/analytics/overview');
      expect(result).toEqual(mockData);
    });
  });

  describe('getUserAnalytics', () => {
    it('fetches user analytics with default period', async () => {
      const mockData = [{ period: '2024-01', new_users: 10 }];
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminAnalyticsApi.getUserAnalytics();

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/analytics/users', {
        params: { period: '30d' },
      });
      expect(result).toEqual(mockData);
    });

    it('fetches user analytics with custom period', async () => {
      const mockData = [{ period: '2024-01', new_users: 10 }];
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminAnalyticsApi.getUserAnalytics('7d');

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/analytics/users', {
        params: { period: '7d' },
      });
      expect(result).toEqual(mockData);
    });
  });

  describe('getGenerationAnalytics', () => {
    it('fetches generation analytics', async () => {
      const mockData = [{ period: '2024-01', total_generations: 100 }];
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminAnalyticsApi.getGenerationAnalytics('30d');

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/analytics/generations', {
        params: { period: '30d' },
      });
      expect(result).toEqual(mockData);
    });
  });

  describe('getStorageAnalytics', () => {
    it('fetches storage analytics', async () => {
      const mockData = {
        total_storage_bytes: 1000000,
        used_storage_bytes: 500000,
      };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminAnalyticsApi.getStorageAnalytics();

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/analytics/storage');
      expect(result).toEqual(mockData);
    });
  });
});

describe('adminUserApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listUsers', () => {
    it('lists users without filters', async () => {
      const mockData = { users: [], total: 0, page: 1, page_size: 20 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminUserApi.listUsers();

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/users?');
      expect(result).toEqual(mockData);
    });

    it('lists users with filters', async () => {
      const mockData = { users: [], total: 0, page: 1, page_size: 20 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      await adminUserApi.listUsers({
        search: 'test',
        role: 'admin',
        page: 2,
      });

      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('search=test')
      );
      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('role=admin')
      );
    });
  });

  describe('getUser', () => {
    it('fetches user details', async () => {
      const mockUser = { id: '123', email: 'test@example.com' };
      mockApiClient.get.mockResolvedValueOnce({ data: mockUser });

      const result = await adminUserApi.getUser('123');

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/users/123');
      expect(result).toEqual(mockUser);
    });
  });

  describe('updateUser', () => {
    it('updates user details', async () => {
      const mockUser = { id: '123', email: 'test@example.com', role: 'admin' };
      mockApiClient.patch.mockResolvedValueOnce({ data: mockUser });

      const result = await adminUserApi.updateUser('123', { role: 'admin' });

      expect(mockApiClient.patch).toHaveBeenCalledWith('/admin/users/123', { role: 'admin' });
      expect(result).toEqual(mockUser);
    });
  });

  describe('suspendUser', () => {
    it('suspends user with reason', async () => {
      const mockResponse = { message: 'User suspended' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminUserApi.suspendUser('123', 'Policy violation');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/users/123/suspend', {
        reason: 'Policy violation',
        duration_days: undefined,
      });
      expect(result).toEqual(mockResponse);
    });

    it('suspends user with duration', async () => {
      const mockResponse = { message: 'User suspended' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      await adminUserApi.suspendUser('123', 'Policy violation', 7);

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/users/123/suspend', {
        reason: 'Policy violation',
        duration_days: 7,
      });
    });
  });

  describe('unsuspendUser', () => {
    it('unsuspends user', async () => {
      const mockResponse = { message: 'User unsuspended' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminUserApi.unsuspendUser('123');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/users/123/unsuspend');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('deleteUser', () => {
    it('deletes user', async () => {
      mockApiClient.delete.mockResolvedValueOnce({});

      await adminUserApi.deleteUser('123');

      expect(mockApiClient.delete).toHaveBeenCalledWith('/admin/users/123');
    });
  });

  describe('warnUser', () => {
    it('warns user with reason and severity', async () => {
      const mockResponse = { message: 'Warning issued' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminUserApi.warnUser('123', 'Inappropriate content', 'medium');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/users/123/warn', {
        reason: 'Inappropriate content',
        severity: 'medium',
      });
      expect(result).toEqual(mockResponse);
    });
  });
});

describe('adminProjectApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listProjects', () => {
    it('lists projects', async () => {
      const mockData = { projects: [], total: 0, page: 1, page_size: 20 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminProjectApi.listProjects();

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/projects?');
      expect(result).toEqual(mockData);
    });
  });

  describe('getProject', () => {
    it('fetches project details', async () => {
      const mockProject = { id: '123', name: 'Test Project' };
      mockApiClient.get.mockResolvedValueOnce({ data: mockProject });

      const result = await adminProjectApi.getProject('123');

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/projects/123');
      expect(result).toEqual(mockProject);
    });
  });

  describe('deleteProject', () => {
    it('deletes project', async () => {
      mockApiClient.delete.mockResolvedValueOnce({});

      await adminProjectApi.deleteProject('123');

      expect(mockApiClient.delete).toHaveBeenCalledWith('/admin/projects/123');
    });
  });

  describe('transferProject', () => {
    it('transfers project to new owner', async () => {
      const mockResponse = { message: 'Project transferred' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminProjectApi.transferProject('123', '456');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/projects/123/transfer', {
        new_owner_id: '456',
      });
      expect(result).toEqual(mockResponse);
    });
  });
});

describe('adminDesignApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listDesigns', () => {
    it('lists designs', async () => {
      const mockData = { designs: [], total: 0, page: 1, page_size: 20 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminDesignApi.listDesigns();

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/designs?');
      expect(result).toEqual(mockData);
    });
  });

  describe('deleteDesign', () => {
    it('deletes design', async () => {
      mockApiClient.delete.mockResolvedValueOnce({});

      await adminDesignApi.deleteDesign('123');

      expect(mockApiClient.delete).toHaveBeenCalledWith('/admin/designs/123');
    });
  });

  describe('restoreDesign', () => {
    it('restores deleted design', async () => {
      const mockResponse = { message: 'Design restored' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminDesignApi.restoreDesign('123');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/designs/123/restore');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('setVisibility', () => {
    it('updates design visibility', async () => {
      const mockResponse = { message: 'Visibility updated' };
      mockApiClient.patch.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminDesignApi.setVisibility('123', true);

      expect(mockApiClient.patch).toHaveBeenCalledWith('/admin/designs/123/visibility', {
        is_public: true,
      });
      expect(result).toEqual(mockResponse);
    });
  });
});

describe('adminTemplateApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listTemplates', () => {
    it('lists templates', async () => {
      const mockData = { templates: [], total: 0, page: 1, page_size: 20 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminTemplateApi.listTemplates();

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/templates?');
      expect(result).toEqual(mockData);
    });
  });

  describe('createTemplate', () => {
    it('creates template', async () => {
      const mockTemplate = { id: '123', name: 'New Template' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockTemplate });

      const result = await adminTemplateApi.createTemplate({
        name: 'New Template',
        slug: 'new-template',
        category: 'enclosure',
        parameters: {},
        default_values: {},
        cadquery_script: 'script',
      });

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/templates', {
        name: 'New Template',
        slug: 'new-template',
        category: 'enclosure',
        parameters: {},
        default_values: {},
        cadquery_script: 'script',
      });
      expect(result).toEqual(mockTemplate);
    });
  });

  describe('enableTemplate', () => {
    it('enables template', async () => {
      const mockResponse = { message: 'Template enabled' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminTemplateApi.enableTemplate('123');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/templates/123/enable');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('disableTemplate', () => {
    it('disables template', async () => {
      const mockResponse = { message: 'Template disabled' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminTemplateApi.disableTemplate('123');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/templates/123/disable');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('featureTemplate', () => {
    it('features template', async () => {
      const mockResponse = { message: 'Template featured' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminTemplateApi.featureTemplate('123');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/templates/123/feature');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('cloneTemplate', () => {
    it('clones template', async () => {
      const mockTemplate = { id: '456', name: 'Cloned Template' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockTemplate });

      const result = await adminTemplateApi.cloneTemplate('123', 'Cloned Template');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/templates/123/clone', {
        name: 'Cloned Template',
      });
      expect(result).toEqual(mockTemplate);
    });
  });

  describe('deleteTemplate', () => {
    it('deletes template', async () => {
      mockApiClient.delete.mockResolvedValueOnce({});

      await adminTemplateApi.deleteTemplate('123');

      expect(mockApiClient.delete).toHaveBeenCalledWith('/admin/templates/123');
    });
  });
});

describe('adminJobApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listJobs', () => {
    it('lists jobs', async () => {
      const mockData = { jobs: [], total: 0, page: 1, page_size: 20 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminJobApi.listJobs();

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/jobs?');
      expect(result).toEqual(mockData);
    });

    it('lists jobs with filters', async () => {
      const mockData = { jobs: [], total: 0, page: 1, page_size: 20 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      await adminJobApi.listJobs({ status: 'pending', type: 'cad_generation' });

      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('status=pending')
      );
    });
  });

  describe('getJob', () => {
    it('fetches job details', async () => {
      const mockJob = { id: '123', status: 'completed' };
      mockApiClient.get.mockResolvedValueOnce({ data: mockJob });

      const result = await adminJobApi.getJob('123');

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/jobs/123');
      expect(result).toEqual(mockJob);
    });
  });

  describe('cancelJob', () => {
    it('cancels job', async () => {
      const mockResponse = { message: 'Job cancelled' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminJobApi.cancelJob('123');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/jobs/123/cancel');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('retryJob', () => {
    it('retries job', async () => {
      const mockResponse = { message: 'Job retried' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminJobApi.retryJob('123');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/jobs/123/retry');
      expect(result).toEqual(mockResponse);
    });
  });
});

describe('adminModerationApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getQueue', () => {
    it('fetches moderation queue', async () => {
      const mockData = { items: [], total: 0 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      const result = await adminModerationApi.getQueue();

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/admin/moderation/queue?status_filter=pending_review'
      );
      expect(result).toEqual(mockData);
    });

    it('fetches moderation queue with custom filter', async () => {
      const mockData = { items: [], total: 0 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockData });

      await adminModerationApi.getQueue('escalated');

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/admin/moderation/queue?status_filter=escalated'
      );
    });
  });

  describe('getStats', () => {
    it('fetches moderation stats', async () => {
      const mockStats = { pending_count: 5, escalated_count: 2 };
      mockApiClient.get.mockResolvedValueOnce({ data: mockStats });

      const result = await adminModerationApi.getStats();

      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/moderation/stats');
      expect(result).toEqual(mockStats);
    });
  });

  describe('approveItem', () => {
    it('approves moderation item', async () => {
      const mockResponse = { message: 'Item approved' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminModerationApi.approveItem('123');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/moderation/123/approve', {
        notes: undefined,
      });
      expect(result).toEqual(mockResponse);
    });

    it('approves moderation item with notes', async () => {
      const mockResponse = { message: 'Item approved' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      await adminModerationApi.approveItem('123', 'Looks good');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/moderation/123/approve', {
        notes: 'Looks good',
      });
    });
  });

  describe('rejectItem', () => {
    it('rejects moderation item', async () => {
      const mockResponse = { message: 'Item rejected' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminModerationApi.rejectItem('123', 'Policy violation');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/moderation/123/reject', {
        reason: 'Policy violation',
        warn_user: true,
      });
      expect(result).toEqual(mockResponse);
    });

    it('rejects moderation item without warning user', async () => {
      const mockResponse = { message: 'Item rejected' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      await adminModerationApi.rejectItem('123', 'Policy violation', false);

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/moderation/123/reject', {
        reason: 'Policy violation',
        warn_user: false,
      });
    });
  });

  describe('escalateItem', () => {
    it('escalates moderation item', async () => {
      const mockResponse = { message: 'Item escalated' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await adminModerationApi.escalateItem('123', 'Needs review');

      expect(mockApiClient.post).toHaveBeenCalledWith('/admin/moderation/123/escalate', {
        notes: 'Needs review',
      });
      expect(result).toEqual(mockResponse);
    });
  });
});

describe('adminApi', () => {
  it('exports all sub-APIs', () => {
    expect(adminApi.analytics).toBe(adminAnalyticsApi);
    expect(adminApi.users).toBe(adminUserApi);
    expect(adminApi.projects).toBe(adminProjectApi);
    expect(adminApi.designs).toBe(adminDesignApi);
    expect(adminApi.templates).toBe(adminTemplateApi);
    expect(adminApi.jobs).toBe(adminJobApi);
    expect(adminApi.moderation).toBe(adminModerationApi);
  });
});
