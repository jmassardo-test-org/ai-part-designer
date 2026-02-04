import { Routes, Route } from 'react-router-dom';
import { AdminRoute } from './components/auth/AdminRoute';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { OnboardingProvider } from './components/onboarding';
import { ErrorBoundary, NotFoundPage, OfflineIndicator } from './components/ui';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { AuthLayout } from './layouts/AuthLayout';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { AssemblyPage } from './pages/AssemblyPage';
import { AuthCallbackPage } from './pages/auth/AuthCallbackPage';
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage';
import { VerifyEmailPage } from './pages/auth/VerifyEmailPage';
import { ContactPage } from './pages/ContactPage';
import { CreatePage } from './pages/CreatePage';
import { DashboardPage } from './pages/DashboardPage';
import { DemoPage } from './pages/DemoPage';
import { DocsPage } from './pages/DocsPage';
import { FilesPage } from './pages/FilesPage';
import { GeneratePageV2 } from './pages/GeneratePageV2';
import { LandingPage } from './pages/LandingPage';
import { ListsPage } from './pages/ListsPage';
import { MarketplacePage } from './pages/MarketplacePage';
import { PrivacyPage } from './pages/PrivacyPage';
import { StartersPage } from './pages/StartersPage';
import { StarterDetailPage } from './pages/StarterDetailPage';
import { DesignDetailPage } from './pages/DesignDetailPage';
import { TemplatesPage } from './pages/TemplatesPage';
import { TermsPage } from './pages/TermsPage';
import { TemplateDetailPage } from './pages/TemplateDetailPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { SettingsPage } from './pages/SettingsPage';
import { SharedWithMePage } from './pages/SharedWithMePage';
import { ComponentLibraryPage } from './pages/ComponentLibraryPage';
import { ComponentUploadPage } from './pages/ComponentUploadPage';
import TrashPage from './pages/TrashPage';
import PricingPage from './pages/PricingPage';
import { UsageBillingPage } from './pages/UsageBillingPage';
import { CheckoutSuccessPage, CheckoutCancelPage } from './pages/checkout';
import { MainLayout } from './layouts/MainLayout';
import { ThemeProvider } from './contexts/ThemeContext';

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="dark">
        <WebSocketProvider>
          <OnboardingProvider>
            <OfflineIndicator />
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/demo" element={<DemoPage />} />
              <Route path="/pricing" element={<PricingPage />} />
              <Route path="/terms" element={<TermsPage />} />
              <Route path="/privacy" element={<PrivacyPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/docs" element={<DocsPage />} />
              
              {/* Checkout routes (post-Stripe redirect) */}
              <Route path="/checkout/success" element={<CheckoutSuccessPage />} />
              <Route path="/checkout/cancel" element={<CheckoutCancelPage />} />
          
          {/* Auth routes */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
          </Route>
          
          {/* OAuth callback (no layout - handles redirect) */}
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          
          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<MainLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/create" element={<CreatePage />} />
              <Route path="/generate" element={<GeneratePageV2 />} />
              <Route path="/templates" element={<TemplatesPage />} />
              <Route path="/templates/:slug" element={<TemplateDetailPage />} />
              <Route path="/starters" element={<StartersPage />} />
              <Route path="/starters/:starterId" element={<StarterDetailPage />} />
              <Route path="/marketplace" element={<MarketplacePage />} />
              <Route path="/lists" element={<ListsPage />} />
              <Route path="/files" element={<FilesPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/:projectId" element={<ProjectsPage />} />
              <Route path="/designs/:designId" element={<DesignDetailPage />} />
              <Route path="/assemblies/:assemblyId" element={<AssemblyPage />} />
              <Route path="/components" element={<ComponentLibraryPage />} />
              <Route path="/components/upload" element={<ComponentUploadPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/settings/notifications" element={<SettingsPage />} />
              <Route path="/settings/billing" element={<UsageBillingPage />} />
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
        </WebSocketProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
