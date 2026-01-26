/**
 * Email verification page component.
 */

import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Loader2, CheckCircle2, AlertCircle, Mail } from 'lucide-react';
import { authApi } from '@/lib/auth';
import { AxiosError } from 'axios';

type VerificationState = 'loading' | 'success' | 'error' | 'no-token';

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [state, setState] = useState<VerificationState>('loading');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isResending, setIsResending] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setState('no-token');
      return;
    }

    const verifyEmail = async () => {
      try {
        await authApi.verifyEmail({ token });
        setState('success');
      } catch (error) {
        if (error instanceof AxiosError) {
          setErrorMessage(error.response?.data?.detail || 'Verification failed');
        } else {
          setErrorMessage('An unexpected error occurred');
        }
        setState('error');
      }
    };

    verifyEmail();
  }, [token]);

  const handleResend = async () => {
    setIsResending(true);
    try {
      await authApi.resendVerification();
      setResendSuccess(true);
    } catch {
      // Ignore errors - user may not be logged in
    } finally {
      setIsResending(false);
    }
  };

  if (state === 'loading') {
    return (
      <div className="w-full max-w-md text-center">
        <Loader2 className="h-16 w-16 animate-spin text-primary-600 mx-auto mb-6" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Verifying your email...</h1>
        <p className="text-gray-600">Please wait while we verify your email address.</p>
      </div>
    );
  }

  if (state === 'success') {
    return (
      <div className="w-full max-w-md text-center">
        <div className="mb-6">
          <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Email verified!</h1>
        <p className="text-gray-600 mb-6">
          Your email has been verified. You can now access all features.
        </p>
        <Link to="/login" className="btn-primary btn-lg inline-flex">
          Continue to login
        </Link>
      </div>
    );
  }

  if (state === 'no-token') {
    return (
      <div className="w-full max-w-md text-center">
        <div className="mb-6">
          <Mail className="h-16 w-16 text-gray-400 mx-auto" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Check your email</h1>
        <p className="text-gray-600 mb-6">
          We&apos;ve sent a verification link to your email address. Click the link to
          verify your account.
        </p>
        {resendSuccess ? (
          <p className="text-green-600 text-sm">Verification email sent!</p>
        ) : (
          <button
            onClick={handleResend}
            disabled={isResending}
            className="text-primary-600 hover:text-primary-700 text-sm font-medium"
          >
            {isResending ? 'Sending...' : "Didn't receive the email? Resend"}
          </button>
        )}
      </div>
    );
  }

  // Error state
  return (
    <div className="w-full max-w-md text-center">
      <div className="mb-6">
        <AlertCircle className="h-16 w-16 text-red-500 mx-auto" />
      </div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Verification failed</h1>
      <p className="text-gray-600 mb-6">{errorMessage}</p>
      <div className="space-y-3">
        <Link to="/login" className="btn-primary btn-lg w-full inline-flex justify-center">
          Go to login
        </Link>
        {resendSuccess ? (
          <p className="text-green-600 text-sm">Verification email sent!</p>
        ) : (
          <button
            onClick={handleResend}
            disabled={isResending}
            className="text-primary-600 hover:text-primary-700 text-sm font-medium"
          >
            {isResending ? 'Sending...' : 'Request new verification link'}
          </button>
        )}
      </div>
    </div>
  );
}
