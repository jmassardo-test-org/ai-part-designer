import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

// Mock all page components
vi.mock('./pages/auth/LoginPage', () => ({
  LoginPage: () => <div data-testid="login-page">Login Page</div>,
}));

vi.mock('./pages/auth/RegisterPage', () => ({
  RegisterPage: () => <div data-testid="register-page">Register Page</div>,
}));

vi.mock('./pages/auth/ForgotPasswordPage', () => ({
  ForgotPasswordPage: () => <div data-testid="forgot-password-page">Forgot Password Page</div>,
}));

vi.mock('./pages/auth/ResetPasswordPage', () => ({
  ResetPasswordPage: () => <div data-testid="reset-password-page">Reset Password Page</div>,
}));

vi.mock('./pages/auth/VerifyEmailPage', () => ({
  VerifyEmailPage: () => <div data-testid="verify-email-page">Verify Email Page</div>,
}));

vi.mock('./pages/DashboardPage', () => ({
  DashboardPage: () => <div data-testid="dashboard-page">Dashboard Page</div>,
}));

vi.mock('./pages/LandingPage', () => ({
  LandingPage: () => <div data-testid="landing-page">Landing Page</div>,
}));

vi.mock('./pages/TemplatesPage', () => ({
  TemplatesPage: () => <div data-testid="templates-page">Templates Page</div>,
}));

vi.mock('./pages/TemplateDetailPage', () => ({
  TemplateDetailPage: () => <div data-testid="template-detail-page">Template Detail Page</div>,
}));

vi.mock('./pages/GeneratePage', () => ({
  GeneratePage: () => <div data-testid="generate-page">Generate Page</div>,
}));

vi.mock('./pages/FilesPage', () => ({
  FilesPage: () => <div data-testid="files-page">Files Page</div>,
}));

vi.mock('./pages/ProjectsPage', () => ({
  ProjectsPage: () => <div data-testid="projects-page">Projects Page</div>,
}));

vi.mock('./pages/AssemblyPage', () => ({
  AssemblyPage: () => <div data-testid="assembly-page">Assembly Page</div>,
}));

vi.mock('./pages/SettingsPage', () => ({
  SettingsPage: () => <div data-testid="settings-page">Settings Page</div>,
}));

vi.mock('./pages/SharedWithMePage', () => ({
  SharedWithMePage: () => <div data-testid="shared-with-me-page">Shared With Me Page</div>,
}));

vi.mock('./pages/ComponentLibraryPage', () => ({
  ComponentLibraryPage: () => <div data-testid="component-library-page">Component Library Page</div>,
}));

vi.mock('./pages/ComponentUploadPage', () => ({
  ComponentUploadPage: () => <div data-testid="component-upload-page">Component Upload Page</div>,
}));

vi.mock('./pages/TrashPage', () => ({
  default: () => <div data-testid="trash-page">Trash Page</div>,
}));

vi.mock('./pages/admin/AdminDashboard', () => ({
  AdminDashboard: () => <div data-testid="admin-dashboard">Admin Dashboard</div>,
}));

// Mock auth components
vi.mock('./components/auth/ProtectedRoute', () => ({
  ProtectedRoute: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

vi.mock('./components/auth/AdminRoute', () => ({
  AdminRoute: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

// Mock layouts
vi.mock('./layouts/AuthLayout', () => ({
  AuthLayout: ({ children }: { children?: React.ReactNode }) => <div data-testid="auth-layout">{children}</div>,
}));

vi.mock('./layouts/MainLayout', () => ({
  MainLayout: ({ children }: { children?: React.ReactNode }) => <div data-testid="main-layout">{children}</div>,
}));

// Mock UI components
vi.mock('./components/ui', () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  NotFoundPage: () => <div data-testid="not-found-page">Not Found</div>,
  OfflineIndicator: () => null,
}));

// Mock onboarding
vi.mock('./components/onboarding', () => ({
  OnboardingProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Need to import React for the mocked components
import React from 'react';
import { Outlet } from 'react-router-dom';

// Update mocks to use Outlet for nested routes
vi.mock('./components/auth/ProtectedRoute', () => ({
  ProtectedRoute: () => <Outlet />,
}));

vi.mock('./components/auth/AdminRoute', () => ({
  AdminRoute: () => <Outlet />,
}));

vi.mock('./layouts/AuthLayout', () => ({
  AuthLayout: () => (
    <div data-testid="auth-layout">
      <Outlet />
    </div>
  ),
}));

vi.mock('./layouts/MainLayout', () => ({
  MainLayout: () => (
    <div data-testid="main-layout">
      <Outlet />
    </div>
  ),
}));

describe('App', () => {
  const renderWithRouter = (initialRoute: string) => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <App />
      </MemoryRouter>
    );
  };

  describe('public routes', () => {
    it('renders landing page at root', () => {
      renderWithRouter('/');
      expect(screen.getByTestId('landing-page')).toBeInTheDocument();
    });
  });

  describe('auth routes', () => {
    it('renders login page', () => {
      renderWithRouter('/login');
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('renders register page', () => {
      renderWithRouter('/register');
      expect(screen.getByTestId('register-page')).toBeInTheDocument();
    });

    it('renders forgot password page', () => {
      renderWithRouter('/forgot-password');
      expect(screen.getByTestId('forgot-password-page')).toBeInTheDocument();
    });

    it('renders reset password page', () => {
      renderWithRouter('/reset-password');
      expect(screen.getByTestId('reset-password-page')).toBeInTheDocument();
    });

    it('renders verify email page', () => {
      renderWithRouter('/verify-email');
      expect(screen.getByTestId('verify-email-page')).toBeInTheDocument();
    });
  });

  describe('protected routes', () => {
    it('renders dashboard page', () => {
      renderWithRouter('/dashboard');
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    it('renders generate page', () => {
      renderWithRouter('/generate');
      expect(screen.getByTestId('generate-page')).toBeInTheDocument();
    });

    it('renders templates page', () => {
      renderWithRouter('/templates');
      expect(screen.getByTestId('templates-page')).toBeInTheDocument();
    });

    it('renders template detail page', () => {
      renderWithRouter('/templates/some-template');
      expect(screen.getByTestId('template-detail-page')).toBeInTheDocument();
    });

    it('renders files page', () => {
      renderWithRouter('/files');
      expect(screen.getByTestId('files-page')).toBeInTheDocument();
    });

    it('renders projects page', () => {
      renderWithRouter('/projects');
      expect(screen.getByTestId('projects-page')).toBeInTheDocument();
    });

    it('renders project detail page', () => {
      renderWithRouter('/projects/project-123');
      expect(screen.getByTestId('projects-page')).toBeInTheDocument();
    });

    it('renders assembly page', () => {
      renderWithRouter('/assemblies/assembly-123');
      expect(screen.getByTestId('assembly-page')).toBeInTheDocument();
    });

    it('renders component library page', () => {
      renderWithRouter('/components');
      expect(screen.getByTestId('component-library-page')).toBeInTheDocument();
    });

    it('renders component upload page', () => {
      renderWithRouter('/components/upload');
      expect(screen.getByTestId('component-upload-page')).toBeInTheDocument();
    });

    it('renders settings page', () => {
      renderWithRouter('/settings');
      expect(screen.getByTestId('settings-page')).toBeInTheDocument();
    });

    it('renders shared with me page', () => {
      renderWithRouter('/shared');
      expect(screen.getByTestId('shared-with-me-page')).toBeInTheDocument();
    });

    it('renders trash page', () => {
      renderWithRouter('/trash');
      expect(screen.getByTestId('trash-page')).toBeInTheDocument();
    });
  });

  describe('admin routes', () => {
    it('renders admin dashboard', () => {
      renderWithRouter('/admin');
      expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
    });
  });

  describe('404 handling', () => {
    it('renders not found page for unknown routes', () => {
      renderWithRouter('/unknown-route');
      expect(screen.getByTestId('not-found-page')).toBeInTheDocument();
    });

    it('renders not found for deeply nested unknown routes', () => {
      renderWithRouter('/some/deeply/nested/unknown/path');
      expect(screen.getByTestId('not-found-page')).toBeInTheDocument();
    });
  });
});
