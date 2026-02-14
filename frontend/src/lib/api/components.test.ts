import { describe, it, expect, vi, beforeEach } from 'vitest';
// Mock the client
vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));
import { apiClient } from './client';
import { componentsApi } from './components';

describe('componentsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getComponents', () => {
    it('fetches components list', async () => {
      const mockData = { items: [{ id: '1', name: 'Component 1' }], total: 1 };
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.getComponents();

      expect(apiClient.get).toHaveBeenCalledWith('/components', { params: undefined });
      expect(result).toEqual(mockData);
    });

    it('fetches components with search params', async () => {
      const mockData = { items: [], total: 0 };
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      await componentsApi.getComponents({ page: 2, search: 'test', category: 'electronics' });

      expect(apiClient.get).toHaveBeenCalledWith('/components', {
        params: { page: 2, search: 'test', category: 'electronics' },
      });
    });
  });

  describe('getComponent', () => {
    it('fetches single component by id', async () => {
      const mockData = { id: 'comp-123', name: 'Test Component' };
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.getComponent('comp-123');

      expect(apiClient.get).toHaveBeenCalledWith('/components/comp-123');
      expect(result).toEqual(mockData);
    });
  });

  describe('createComponent', () => {
    it('creates a new component', async () => {
      const createData = {
        name: 'New Component',
        category: 'connectors',
        description: 'A test component',
      };
      const mockData = { id: 'new-id', ...createData };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.createComponent(createData);

      expect(apiClient.post).toHaveBeenCalledWith('/components', createData);
      expect(result).toEqual(mockData);
    });
  });

  describe('updateComponent', () => {
    it('updates a component', async () => {
      const updateData = { name: 'Updated Name' };
      const mockData = { id: 'comp-123', name: 'Updated Name' };
      (apiClient.patch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.updateComponent('comp-123', updateData);

      expect(apiClient.patch).toHaveBeenCalledWith('/components/comp-123', updateData);
      expect(result).toEqual(mockData);
    });
  });

  describe('deleteComponent', () => {
    it('deletes a component', async () => {
      (apiClient.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: { success: true } });

      const result = await componentsApi.deleteComponent('comp-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/components/comp-123');
      expect(result).toEqual({ success: true });
    });
  });

  describe('uploadComponent', () => {
    it('uploads component file with progress tracking', async () => {
      const mockData = { id: 'uploaded-id', name: 'Uploaded Component' };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const formData = new FormData();
      formData.append('file', new Blob(['test']), 'test.step');

      const onProgress = vi.fn();
      const result = await componentsApi.uploadComponent(formData, onProgress);

      expect(apiClient.post).toHaveBeenCalledWith('/components/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: expect.any(Function),
      });
      expect(result).toEqual(mockData);
    });

    it('calls progress callback with percentage', async () => {
      (apiClient.post as ReturnType<typeof vi.fn>).mockImplementation(
        async (_url, _data, config) => {
          // Simulate progress event
          if (config?.onUploadProgress) {
            config.onUploadProgress({ loaded: 50, total: 100 });
          }
          return { data: {} };
        }
      );

      const onProgress = vi.fn();
      await componentsApi.uploadComponent(new FormData(), onProgress);

      expect(onProgress).toHaveBeenCalledWith(50);
    });
  });

  describe('browseLibrary', () => {
    it('fetches library components with search params', async () => {
      const mockData = { items: [], total: 0, page: 1 };
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      await componentsApi.browseLibrary({
        search: 'arduino',
        category: 'microcontrollers',
        featured: true,
        sort_by: 'popularity',
      });

      expect(apiClient.get).toHaveBeenCalledWith('/components/library', {
        params: {
          search: 'arduino',
          category: 'microcontrollers',
          featured: true,
          sort_by: 'popularity',
        },
      });
    });
  });

  describe('getLibraryComponent', () => {
    it('fetches library component by id', async () => {
      const mockData = { id: 'lib-123', name: 'Library Component' };
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.getLibraryComponent('lib-123');

      expect(apiClient.get).toHaveBeenCalledWith('/components/library/lib-123');
      expect(result).toEqual(mockData);
    });
  });

  describe('getCategories', () => {
    it('fetches available categories', async () => {
      const mockData = ['electronics', 'connectors', 'enclosures'];
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.getCategories();

      expect(apiClient.get).toHaveBeenCalledWith('/components/library/categories');
      expect(result).toEqual(mockData);
    });
  });

  describe('getManufacturers', () => {
    it('fetches available manufacturers', async () => {
      const mockData = ['Arduino', 'Raspberry Pi', 'Adafruit'];
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.getManufacturers();

      expect(apiClient.get).toHaveBeenCalledWith('/components/library/manufacturers');
      expect(result).toEqual(mockData);
    });
  });

  describe('addToProject', () => {
    it('adds library component to project', async () => {
      const mockData = { id: 'added-123' };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.addToProject('lib-123', 'proj-456');

      expect(apiClient.post).toHaveBeenCalledWith('/components/library/lib-123/add', {
        project_id: 'proj-456',
      });
      expect(result).toEqual(mockData);
    });

    it('adds without project id', async () => {
      const mockData = { id: 'added-123' };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      await componentsApi.addToProject('lib-123');

      expect(apiClient.post).toHaveBeenCalledWith('/components/library/lib-123/add', {
        project_id: undefined,
      });
    });
  });

  describe('getProjectComponents', () => {
    it('fetches project components', async () => {
      const mockData = [{ id: '1' }, { id: '2' }];
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.getProjectComponents('proj-123');

      expect(apiClient.get).toHaveBeenCalledWith('/projects/proj-123/components');
      expect(result).toEqual(mockData);
    });
  });

  describe('updateProjectComponent', () => {
    it('updates project component', async () => {
      const mockData = { id: 'comp-123', quantity: 5 };
      (apiClient.patch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.updateProjectComponent('proj-123', 'comp-123', {
        quantity: 5,
      });

      expect(apiClient.patch).toHaveBeenCalledWith(
        '/projects/proj-123/components/comp-123',
        { quantity: 5 }
      );
      expect(result).toEqual(mockData);
    });
  });

  describe('removeFromProject', () => {
    it('removes component from project', async () => {
      const mockData = { success: true };
      (apiClient.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.removeFromProject('proj-123', 'comp-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/projects/proj-123/components/comp-123');
      expect(result).toEqual(mockData);
    });
  });

  describe('reorderProjectComponents', () => {
    it('reorders components in project', async () => {
      const mockData = { success: true };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.reorderProjectComponents('proj-123', ['c1', 'c2', 'c3']);

      expect(apiClient.post).toHaveBeenCalledWith('/projects/proj-123/components/reorder', {
        component_ids: ['c1', 'c2', 'c3'],
      });
      expect(result).toEqual(mockData);
    });
  });

  describe('getExtractionJob', () => {
    it('fetches extraction job status', async () => {
      const mockData = { id: 'job-123', status: 'completed' };
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await componentsApi.getExtractionJob('job-123');

      expect(apiClient.get).toHaveBeenCalledWith('/components/extraction/job-123');
      expect(result).toEqual(mockData);
    });
  });
});
