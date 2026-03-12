/**
 * SecurityDashboardTab Tests.
 *
 * Unit tests for the SecurityDashboardTab component.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminApi } from '@/lib/api/admin';
import type {
  SecurityEventListResponse,
  FailedLoginListResponse,
  ActiveSessionListResponse,
} from '@/types/admin';

// Mock the admin API
vi.mock('@/lib/api/admin', () => ({
  adminApi: {
    security: {
      getDashboard: vi.fn(),
      getEvents: vi.fn(),
      getFailedLogins: vi.fn(),
      getBlockedIPs: vi.fn(),
      blockIP: vi.fn(),
      unblockIP: vi.fn(),
      getSessions: vi.fn(),
      terminateSession: vi.fn(),
    },
  },
}));

const mockAdminApi = vi.mocked(adminApi, true);

// Import after mocks
import { SecurityDashboardTab } from './SecurityDashboardTab';

describe('SecurityDashboardTab', () => {
  const mockDashboardResponse = {
    threat_level: 'low',
    failed_logins_24h: 12,
    blocked_ips_count: 3,
    active_sessions: 150,
    security_events_24h: 45,
  };

  const mockEventsResponse: SecurityEventListResponse = {
    items: [
      {
        id: 'evt-1',
        event_type: 'login_failure',
        severity: 'medium',
        user_id: 'user-1',
        user_email: 'alice@example.com',
        resource_type: null,
        ip_address: '192.168.1.100',
        details: {},
        created_at: '2024-03-15T10:30:00Z',
      },
      {
        id: 'evt-2',
        event_type: 'suspicious_activity',
        severity: 'high',
        user_id: null,
        user_email: null,
        resource_type: null,
        ip_address: '10.0.0.50',
        details: {},
        created_at: '2024-03-15T11:00:00Z',
      },
    ],
    total: 2,
    page: 1,
    page_size: 20,
  };

  const mockFailedLoginsResponse: FailedLoginListResponse = {
    items: [
      {
        user_email: 'eve@evil.com',
        user_id: null,
        ip_address: '203.0.113.1',
        timestamp: '2024-03-15T09:00:00Z',
        details: {},
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  };

  const mockBlockedIPsResponse = [
    {
      ip_address: '203.0.113.1',
      reason: 'Brute force attempt',
      blocked_at: '2024-03-14T00:00:00Z',
      blocked_by: 'admin@example.com',
    },
  ];

  const mockSessionsResponse: ActiveSessionListResponse = {
    items: [
      {
        session_id: 'sess-1',
        user_id: 'user-1',
        user_email: 'alice@example.com',
        ip_address: '192.168.1.50',
        user_agent: 'Mozilla/5.0',
        created_at: '2024-03-15T08:00:00Z',
        last_activity: '2024-03-15T12:00:00Z',
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockAdminApi.security.getDashboard.mockResolvedValue(mockDashboardResponse);
    mockAdminApi.security.getEvents.mockResolvedValue(mockEventsResponse);
    mockAdminApi.security.getFailedLogins.mockResolvedValue(mockFailedLoginsResponse);
    mockAdminApi.security.getBlockedIPs.mockResolvedValue(mockBlockedIPsResponse);
    mockAdminApi.security.getSessions.mockResolvedValue(mockSessionsResponse);
  });

  it('renders the security dashboard heading', async () => {
    render(<SecurityDashboardTab />);

    expect(screen.getByText('Security Dashboard')).toBeInTheDocument();
  });

  it('fetches and displays dashboard overview on mount', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(mockAdminApi.security.getDashboard).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('low')).toBeInTheDocument(); // Threat Level
      expect(screen.getByText('12')).toBeInTheDocument(); // Failed Logins
      expect(screen.getByText('3')).toBeInTheDocument(); // Blocked IPs
      expect(screen.getByText('150')).toBeInTheDocument(); // Active Sessions
      expect(screen.getByText('45')).toBeInTheDocument(); // Events
    });
  });

  it('displays navigation cards for sub-views', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Security Events/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Failed Logins/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Blocked IPs/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Active Sessions/i })).toBeInTheDocument();
    });
  });

  it('navigates to security events view', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByText('Security Events')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Security Events'));

    await waitFor(() => {
      expect(mockAdminApi.security.getEvents).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('login_failure')).toBeInTheDocument();
      expect(screen.getByText('suspicious_activity')).toBeInTheDocument();
    });
  });

  it('navigates to failed logins view', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByText('Failed Logins')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Failed Logins'));

    await waitFor(() => {
      expect(mockAdminApi.security.getFailedLogins).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('eve@evil.com')).toBeInTheDocument();
      expect(screen.getByText('203.0.113.1')).toBeInTheDocument();
    });
  });

  it('navigates to blocked IPs view', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Blocked IPs/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Blocked IPs/i }));

    await waitFor(() => {
      expect(mockAdminApi.security.getBlockedIPs).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('203.0.113.1')).toBeInTheDocument();
      expect(screen.getByText('Brute force attempt')).toBeInTheDocument();
    });
  });

  it('navigates to active sessions view', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Active Sessions/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Active Sessions/i }));

    await waitFor(() => {
      expect(mockAdminApi.security.getSessions).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    });
  });

  it('opens block IP modal', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Blocked IPs/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Blocked IPs/i }));

    await waitFor(() => {
      expect(screen.getByText('Block IP')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Block IP'));

    await waitFor(() => {
      expect(screen.getByText('Block IP Address')).toBeInTheDocument();
    });
  });

  it('blocks a new IP', async () => {
    mockAdminApi.security.blockIP.mockResolvedValue({ message: 'Blocked' });

    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Blocked IPs/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Blocked IPs/i }));

    await waitFor(() => {
      expect(screen.getByText('Block IP')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Block IP'));

    await waitFor(() => {
      expect(screen.getByText('Block IP Address')).toBeInTheDocument();
    });

    const ipInput = screen.getByPlaceholderText('e.g. 192.168.1.100');
    fireEvent.change(ipInput, { target: { value: '10.10.10.10' } });

    const reasonInputs = screen.getAllByRole('textbox');
    const reasonInput = reasonInputs.find(el => el !== ipInput);
    if (reasonInput) {
      fireEvent.change(reasonInput, { target: { value: 'Suspicious activity' } });
    }

    fireEvent.click(screen.getByText('Block'));

    await waitFor(() => {
      expect(mockAdminApi.security.blockIP).toHaveBeenCalledWith({
        ip_address: '10.10.10.10',
        reason: 'Suspicious activity',
      });
    });
  });

  it('unblocks an IP', async () => {
    mockAdminApi.security.unblockIP.mockResolvedValue({ message: 'Unblocked' });

    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Blocked IPs/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Blocked IPs/i }));

    await waitFor(() => {
      expect(screen.getByText('203.0.113.1')).toBeInTheDocument();
    });

    const unblockButton = screen.getByTitle('Unblock');
    fireEvent.click(unblockButton);

    await waitFor(() => {
      expect(mockAdminApi.security.unblockIP).toHaveBeenCalledWith('203.0.113.1');
    });
  });

  it('shows terminate session confirmation', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Active Sessions/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Active Sessions/i }));

    await waitFor(() => {
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    });

    const terminateButton = screen.getByTitle('Terminate');
    fireEvent.click(terminateButton);

    await waitFor(() => {
      expect(screen.getByText('Terminate Session')).toBeInTheDocument();
      expect(screen.getByText(/force-terminate/i)).toBeInTheDocument();
    });
  });

  it('terminates a session', async () => {
    mockAdminApi.security.terminateSession.mockResolvedValue({ message: 'Terminated' });

    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Active Sessions/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Active Sessions/i }));

    await waitFor(() => {
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTitle('Terminate'));

    await waitFor(() => {
      expect(screen.getByText('Terminate Session')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Terminate'));

    await waitFor(() => {
      expect(mockAdminApi.security.terminateSession).toHaveBeenCalledWith('sess-1');
    });
  });

  it('filters events by type', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByText('Security Events')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Security Events'));

    await waitFor(() => {
      expect(mockAdminApi.security.getEvents).toHaveBeenCalledTimes(1);
    });

    const typeSelect = screen.getAllByRole('combobox')[0];
    fireEvent.change(typeSelect, { target: { value: 'login_failure' } });

    await waitFor(() => {
      expect(mockAdminApi.security.getEvents).toHaveBeenCalledTimes(2);
    });
  });

  it('shows back button from sub-views', async () => {
    render(<SecurityDashboardTab />);

    await waitFor(() => {
      expect(screen.getByText('Security Events')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Security Events'));

    await waitFor(() => {
      expect(screen.getByText('Back')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Back'));

    await waitFor(() => {
      expect(screen.getByText('Security Dashboard')).toBeInTheDocument();
    });
  });
});
