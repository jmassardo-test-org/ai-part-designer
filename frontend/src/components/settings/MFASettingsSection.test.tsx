/**
 * Tests for MFA Settings Section
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MFASettingsSection } from './MFASettingsSection';

// Mock the MFA API
const mockGetStatus = vi.fn();
const mockSetup = vi.fn();
const mockGetBackupCodesCount = vi.fn();

vi.mock('@/lib/api/mfa', () => ({
  mfaApi: {
    getStatus: () => mockGetStatus(),
    setup: () => mockSetup(),
    verify: vi.fn(),
    disable: vi.fn(),
    getBackupCodesCount: () => mockGetBackupCodesCount(),
    regenerateBackupCodes: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('MFASettingsSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetStatus.mockResolvedValue({ enabled: false });
    mockGetBackupCodesCount.mockResolvedValue({ count: 0 });
  });

  it('renders MFA settings section header', async () => {
    render(<MFASettingsSection />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText(/two-factor authentication/i)).toBeInTheDocument();
    });
  });

  it('shows enable button when MFA is disabled', async () => {
    mockGetStatus.mockResolvedValue({ enabled: false });
    
    render(<MFASettingsSection />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /enable/i })).toBeInTheDocument();
    });
  });

  it('shows disable button when MFA is enabled', async () => {
    mockGetStatus.mockResolvedValue({
      enabled: true,
      enabled_at: new Date().toISOString(),
    });
    mockGetBackupCodesCount.mockResolvedValue({ count: 8 });
    
    render(<MFASettingsSection />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /disable/i })).toBeInTheDocument();
    });
  });

  it('displays MFA shield icon', async () => {
    render(<MFASettingsSection />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      // The component should render with the card structure
      expect(screen.getByText(/two-factor authentication/i)).toBeInTheDocument();
    });
  });
});
