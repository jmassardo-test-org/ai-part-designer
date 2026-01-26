/**
 * Reset password page component.
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { authApi } from '@/lib/auth';
import { AxiosError } from 'axios';

const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .refine((val) => /[a-z]/.test(val), 'Must contain a lowercase letter')
  .refine((val) => /[A-Z]/.test(val), 'Must contain an uppercase letter')
  .refine((val) => /\d/.test(val), 'Must contain a number')
  .refine((val) => /[!@#$%^&*(),.?":{}|<>]/.test(val), 'Must contain a special character');

const schema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type FormData = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      password: '',
      confirmPassword: '',
    },
  });

  // Invalid or missing token
  if (!token) {
    return (
      <div className="w-full max-w-md text-center">
        <div className="mb-6">
          <AlertCircle className="h-16 w-16 text-red-500 mx-auto" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Invalid reset link</h1>
        <p className="text-gray-600 mb-6">
          This password reset link is invalid or has expired.
        </p>
        <Link to="/forgot-password" className="btn-primary btn-md inline-flex">
          Request new link
        </Link>
      </div>
    );
  }

  const onSubmit = async (data: FormData) => {
    setServerError(null);

    try {
      await authApi.resetPassword({
        token,
        new_password: data.password,
      });
      setIsSuccess(true);
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login', {
          state: { message: 'Password reset successful! You can now log in.' },
        });
      }, 3000);
    } catch (error) {
      if (error instanceof AxiosError) {
        setServerError(error.response?.data?.detail || 'Failed to reset password');
      } else {
        setServerError('An unexpected error occurred.');
      }
    }
  };

  if (isSuccess) {
    return (
      <div className="w-full max-w-md text-center">
        <div className="mb-6">
          <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Password reset!</h1>
        <p className="text-gray-600 mb-6">
          Your password has been successfully reset. Redirecting to login...
        </p>
        <Link to="/login" className="btn-primary btn-md inline-flex">
          Go to login
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Set new password</h1>
        <p className="mt-2 text-gray-600">
          Your new password must be different from previously used passwords.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {serverError && (
          <div className="flex items-center gap-2 rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{serverError}</span>
          </div>
        )}

        <div>
          <label htmlFor="password" className="label block mb-1.5">
            New Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              className={`input pr-10 ${errors.password ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
              {...register('password')}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
          {errors.password && (
            <p className="mt-1.5 text-sm text-red-600">{errors.password.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="confirmPassword" className="label block mb-1.5">
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            type="password"
            autoComplete="new-password"
            className={`input ${errors.confirmPassword ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
            {...register('confirmPassword')}
          />
          {errors.confirmPassword && (
            <p className="mt-1.5 text-sm text-red-600">{errors.confirmPassword.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-primary btn-lg w-full"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Resetting...
            </>
          ) : (
            'Reset password'
          )}
        </button>
      </form>
    </div>
  );
}
