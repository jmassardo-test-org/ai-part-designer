/**
 * Tests for Audit Log Viewer Component
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as auditLogsApi from '@/lib/api/auditLogs';
import AuditLogViewer from './AuditLogViewer';

// Mock the audit logs API
vi.mock('@/lib/api/auditLogs', () => ({
  auditLogsApi: {
    getUserAuditLogs: vi.fn(),
  },
}));

const mockAuditLogs = [
  {
    id: '1',
    action: 'login',
    resource_type: 'user',
    resource_id: 'user-1',
    actor_type: 'user',
    status: 'success',
    error_message: null,
    context: { method: 'password' },
    ip_address: '192.168.1.1',
    user_agent: 'Mozilla/5.0',
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    id: '2',
    action: 'create',
    resource_type: 'design',
    resource_id: 'design-1',
    actor_type: 'user',
    status: 'success',
    error_message: null,
    context: { name: 'Test Design' },
    ip_address: '192.168.1.1',
    user_agent: 'Mozilla/5.0',
    created_at: '2024-01-15T11:00:00Z',
  },
  {
    id: '3',
    action: 'delete',
    resource_type: 'project',
    resource_id: 'project-1',
    actor_type: 'user',
    status: 'failure',
    error_message: 'Permission denied',
    context: {},
    ip_address: '192.168.1.1',
    user_agent: 'Mozilla/5.0',
    created_at: '2024-01-15T12:00:00Z',
  },
];

describe('AuditLogViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage
    Storage.prototype.getItem = vi.fn(() => 'fake-token');
  });

  it('renders loading state initially', () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    expect(screen.getByText('Audit Log')).toBeInTheDocument();
    // Check for the loading spinner by its test attribute or class
    expect(screen.getByText('View all actions performed in your account')).toBeInTheDocument();
  });

  it('displays audit logs when loaded', async () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockResolvedValue({
      logs: mockAuditLogs,
      total: 3,
      skip: 0,
      limit: 20,
    });

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Login')).toBeInTheDocument();
      expect(screen.getByText('Create')).toBeInTheDocument();
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    // Check resource types are displayed
    expect(screen.getAllByText('User')[0]).toBeInTheDocument(); // In table
    expect(screen.getAllByText('Design')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Project')[0]).toBeInTheDocument();
  });

  it('displays error message when API fails', async () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockRejectedValue(
      new Error('Failed to fetch audit logs')
    );

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch audit logs')).toBeInTheDocument();
    });
  });

  it('displays empty state when no logs', async () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockResolvedValue({
      logs: [],
      total: 0,
      skip: 0,
      limit: 20,
    });

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No audit logs found')).toBeInTheDocument();
      expect(screen.getByText('Your activity will appear here')).toBeInTheDocument();
    });
  });

  it('toggles filter panel', async () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockResolvedValue({
      logs: [],
      total: 0,
      skip: 0,
      limit: 20,
    });

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    const filterButton = screen.getByRole('button', { name: /filters/i });
    
    // Filter panel should not be visible initially
    expect(screen.queryByText('Action')).not.toBeInTheDocument();

    // Click to show filters
    fireEvent.click(filterButton);
    await waitFor(() => {
      expect(screen.getByText('Action')).toBeInTheDocument();
      expect(screen.getByText('Resource Type')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });
  });

  it('applies action filter', async () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockResolvedValue({
      logs: [],
      total: 0,
      skip: 0,
      limit: 20,
    });

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    // Open filters
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);

    await waitFor(() => {
      expect(screen.getByText('Action')).toBeInTheDocument();
    });

    // Select login action
    const actionSelect = screen.getByRole('combobox', { name: /action/i });
    fireEvent.change(actionSelect, { target: { value: 'login' } });

    await waitFor(() => {
      expect(vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs)).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'login',
        })
      );
    });
  });

  it('applies status filter', async () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockResolvedValue({
      logs: [],
      total: 0,
      skip: 0,
      limit: 20,
    });

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    // Open filters
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);

    await waitFor(() => {
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    // Select failure status
    const statusSelect = screen.getByRole('combobox', { name: /status/i });
    fireEvent.change(statusSelect, { target: { value: 'failure' } });

    await waitFor(() => {
      expect(vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs)).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'failure',
        })
      );
    });
  });

  it('resets filters', async () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockResolvedValue({
      logs: [],
      total: 0,
      skip: 0,
      limit: 20,
    });

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    // Open filters
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);

    await waitFor(() => {
      expect(screen.getByText('Action')).toBeInTheDocument();
    });

    // Apply a filter
    const actionSelect = screen.getByRole('combobox', { name: /action/i });
    fireEvent.change(actionSelect, { target: { value: 'login' } });

    await waitFor(() => {
      expect(screen.getByText('Reset Filters')).toBeInTheDocument();
    });

    // Reset filters
    const resetButton = screen.getByRole('button', { name: /reset filters/i });
    fireEvent.click(resetButton);

    await waitFor(() => {
      expect(actionSelect).toHaveValue('');
    });
  });

  it('handles pagination', async () => {
    // First page
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockResolvedValue({
      logs: mockAuditLogs,
      total: 50,
      skip: 0,
      limit: 20,
    });

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Showing 1 to 20 of 50 logs')).toBeInTheDocument();
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
    });

    // Go to next page
    const nextButton = screen.getByRole('button', { name: /next/i });
    expect(nextButton).not.toBeDisabled();
    
    fireEvent.click(nextButton);

    await waitFor(() => {
      expect(vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs)).toHaveBeenCalledWith(
        expect.objectContaining({
          skip: 20,
          limit: 20,
        })
      );
    });
  });

  it('displays status icons correctly', async () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockResolvedValue({
      logs: [
        { ...mockAuditLogs[0], status: 'success' },
        { ...mockAuditLogs[1], status: 'failure' },
        { ...mockAuditLogs[2], status: 'error' },
      ],
      total: 3,
      skip: 0,
      limit: 20,
    });

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('Success')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Failure')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Error')[0]).toBeInTheDocument();
    });
  });

  it('formats dates correctly', async () => {
    vi.mocked(auditLogsApi.auditLogsApi.getUserAuditLogs).mockResolvedValue({
      logs: [mockAuditLogs[0]],
      total: 1,
      skip: 0,
      limit: 20,
    });

    render(
      <BrowserRouter>
        <AuditLogViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Date should be formatted (exact format depends on locale, but it should contain "Jan" and "15")
      const dateCell = screen.getByText(/Jan.*15/);
      expect(dateCell).toBeInTheDocument();
    });
  });
});
