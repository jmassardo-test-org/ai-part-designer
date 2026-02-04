/**
 * OAuth callback page.
 *
 * Handles OAuth provider callback with tokens or errors.
 * Extracts tokens from URL, stores them, and redirects to app.
 */

import { Loader2, CheckCircle2, AlertCircle, RefreshCw, Mail } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

type CallbackStatus = 'processing' | 'success' | 'error';

// Error message mappings for user-friendly display
const ERROR_MESSAGES: Record<string, { title: string; description: string; suggestion: string }> = {
  oauth_error: {
    title: 'OAuth Provider Error',
    description: 'The authentication provider returned an error.',
    suggestion: 'This may be a temporary issue. Try again or use a different sign-in method.',
  },
  access_denied: {
    title: 'Access Denied',
    description: 'You cancelled the sign-in process or denied access.',
    suggestion: 'If you want to continue, try again and allow access when prompted.',
  },
  server_error: {
    title: 'Server Error',
    description: 'Our servers encountered an error processing your request.',
    suggestion: 'Please try again in a few moments. If the issue persists, contact support.',
  },
  email_conflict: {
    title: 'Account Already Exists',
    description: 'An account with this email already exists using a different sign-in method.',
    suggestion: 'Try signing in with your email and password, then link your OAuth account from settings.',
  },
  provider_unavailable: {
    title: 'Provider Unavailable',
    description: 'This authentication provider is currently unavailable.',
    suggestion: 'Please try a different sign-in method or try again later.',
  },
  default: {
    title: 'Authentication Failed',
    description: 'We could not complete your sign-in request.',
    suggestion: 'Please try again. If the problem continues, try a different sign-in method.',
  },
};

function getErrorInfo(errorCode: string | null) {
  if (!errorCode) return ERROR_MESSAGES.default;
  return ERROR_MESSAGES[errorCode] || ERROR_MESSAGES.default;
}

export function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState<CallbackStatus>('processing');
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [isNewUser, setIsNewUser] = useState(false);

  useEffect(() => {
    const handleCallback = async () => {
      // Check for error params
      const error = searchParams.get('error');
      const errorMessage = searchParams.get('message');

      if (error) {
        setStatus('error');
        setErrorCode(error);
        setErrorDetail(errorMessage);
        return;
      }

      // Check for success tokens
      const accessToken = searchParams.get('access_token');
      const refreshToken = searchParams.get('refresh_token');
      const newUser = searchParams.get('is_new_user') === 'true';

      if (!accessToken || !refreshToken) {
        setStatus('error');
        setErrorCode('server_error');
        setErrorDetail('No authentication tokens received');
        return;
      }

      try {
        // Store tokens
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);

        setIsNewUser(newUser);
        setStatus('success');

        // Refresh user data
        await refreshUser();

        // Redirect after brief delay to show success message
        setTimeout(() => {
          // New users go to dashboard - OnboardingProvider will trigger onboarding
          navigate('/dashboard', { replace: true });
        }, 1500);
      } catch (err) {
        console.error('Failed to process OAuth callback:', err);
        setStatus('error');
        setErrorCode('server_error');
        setErrorDetail('Failed to complete authentication');
      }
    };

    handleCallback();
  }, [searchParams, navigate, refreshUser]);

  const errorInfo = getErrorInfo(errorCode);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full p-8 bg-white rounded-lg shadow-md text-center">
        {status === 'processing' && (
          <>
            <Loader2 className="h-12 w-12 text-primary-600 animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Authenticating...
            </h2>
            <p className="text-gray-600">Please wait while we verify your identity.</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {isNewUser ? 'Welcome to AssemblematicAI!' : 'Welcome back!'}
            </h2>
            <p className="text-gray-600">
              {isNewUser
                ? 'Your account has been created. Redirecting to get you started...'
                : 'Login successful! Redirecting to your dashboard...'}
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {errorInfo.title}
            </h2>
            <p className="text-gray-600 mb-2">{errorInfo.description}</p>
            {errorDetail && (
              <p className="text-sm text-gray-500 mb-4 p-2 bg-gray-50 rounded">
                {errorDetail}
              </p>
            )}
            <p className="text-sm text-gray-500 mb-6">{errorInfo.suggestion}</p>

            <div className="space-y-3">
              <button
                onClick={() => navigate('/login', { replace: true })}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>

              <Link
                to="/login"
                className="w-full flex items-center justify-center gap-2 px-4 py-2 border rounded-lg text-gray-700 hover:bg-gray-50"
              >
                <Mail className="w-4 h-4" />
                Sign in with Email
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default AuthCallbackPage;
