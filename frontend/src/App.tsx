import { Routes, Route } from 'react-router-dom';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage';
import { VerifyEmailPage } from './pages/auth/VerifyEmailPage';
import { DashboardPage } from './pages/DashboardPage';
import { LandingPage } from './pages/LandingPage';
import { TemplatesPage } from './pages/TemplatesPage';
import { TemplateDetailPage } from './pages/TemplateDetailPage';
import { CreatePage } from './pages/CreatePage';
import { FilesPage } from './pages/FilesPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { AssemblyPage } from './pages/AssemblyPage';
import { SettingsPage } from './pages/SettingsPage';
import { SharedWithMePage } from './pages/SharedWithMePage';
import { ComponentLibraryPage } from './pages/ComponentLibraryPage';
import { ComponentUploadPage } from './pages/ComponentUploadPage';
import TrashPage from './pages/TrashPage';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AdminRoute } from './components/auth/AdminRoute';
import { AuthLayout } from './layouts/AuthLayout';
import { MainLayout } from './layouts/MainLayout';
import { ErrorBoundary, NotFoundPage, OfflineIndicator } from './components/ui';
import { OnboardingProvider } from './components/onboarding';

function App() {
  return (
    <ErrorBoundary>
      <OnboardingProvider>
        <OfflineIndicator />
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<LandingPage />} />
          
          {/* Auth routes */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
          </Route>
          
          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<MainLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/create" element={<CreatePage />} />
              <Route path="/templates" element={<TemplatesPage />} />
              <Route path="/templates/:slug" element={<TemplateDetailPage />} />
              <Route path="/files" element={<FilesPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/:projectId" element={<ProjectsPage />} />
              <Route path="/assemblies/:assemblyId" element={<AssemblyPage />} />
              <Route path="/components" element={<ComponentLibraryPage />} />
              <Route path="/components/upload" element={<ComponentUploadPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/shared" element={<SharedWithMePage />} />
              <Route path="/trash" element={<TrashPage />} />
              
              {/* Admin routes */}
              <Route element={<AdminRoute />}>
                <Route path="/admin" element={<AdminDashboard />} />
              </Route>
            </Route>
          </Route>

          {/* 404 Not Found */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </OnboardingProvider>
    </ErrorBoundary>
  );
}

export default App;
