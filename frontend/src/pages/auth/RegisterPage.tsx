/**
 * Registration page component.
 *
 * Provides a registration form with:
 * - Email, password, display name fields
 * - Password strength indicator
 * - Terms acceptance checkbox
 * - Form validation with Zod
 * - Error handling and display
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link } from 'react-router-dom';
import { Eye, EyeOff, Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { AxiosError } from 'axios';

// Password requirements
const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .max(128, 'Password must be less than 128 characters')
  .refine((val) => /[a-z]/.test(val), 'Must contain a lowercase letter')
  .refine((val) => /[A-Z]/.test(val), 'Must contain an uppercase letter')
  .refine((val) => /\d/.test(val), 'Must contain a number')
  .refine((val) => /[!@#$%^&*(),.?":{}|<>]/.test(val), 'Must contain a special character');

// Form validation schema
const registerSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: passwordSchema,
  display_name: z
    .string()
    .min(2, 'Display name must be at least 2 characters')
    .max(50, 'Display name must be less than 50 characters'),
  accepted_terms: z.literal(true, {
    errorMap: () => ({ message: 'You must accept the terms of service' }),
  }),
});

type RegisterFormData = z.infer<typeof registerSchema>;

// Password strength calculation
function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  let score = 0;

  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password)) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;

  if (score <= 2) return { score, label: 'Weak', color: 'bg-red-500' };
  if (score <= 4) return { score, label: 'Fair', color: 'bg-yellow-500' };
  if (score <= 5) return { score, label: 'Good', color: 'bg-blue-500' };
  return { score, label: 'Strong', color: 'bg-green-500' };
}

// Password requirement component
function PasswordRequirement({
  met,
  text,
}: {
  met: boolean;
  text: string;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {met ? (
        <CheckCircle2 className="h-4 w-4 text-green-500" />
      ) : (
        <XCircle className="h-4 w-4 text-gray-400" />
      )}
      <span className={met ? 'text-green-700' : 'text-gray-500'}>{text}</span>
    </div>
  );
}

export function RegisterPage() {
  const { register: registerUser } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: '',
      password: '',
      display_name: '',
      accepted_terms: false as unknown as true, // Type workaround for literal
    },
  });

  const password = watch('password', '');
  const strength = getPasswordStrength(password);

  const onSubmit = async (data: RegisterFormData) => {
    setServerError(null);

    try {
      await registerUser({
        email: data.email,
        password: data.password,
        display_name: data.display_name,
        accepted_terms: data.accepted_terms,
      });
    } catch (error) {
      if (error instanceof AxiosError) {
        const detail = error.response?.data?.detail;
        if (typeof detail === 'string') {
          setServerError(detail);
        } else if (Array.isArray(detail)) {
          setServerError(detail.map((e) => e.msg).join(', '));
        } else {
          setServerError('Registration failed. Please try again.');
        }
      } else {
        setServerError('An unexpected error occurred.');
      }
    }
  };

  return (
    <div className="w-full max-w-md">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Create your account</h1>
        <p className="mt-2 text-gray-600">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
            Sign in
          </Link>
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* Server Error */}
        {serverError && (
          <div className="flex items-center gap-2 rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{serverError}</span>
          </div>
        )}

        {/* Display Name */}
        <div>
          <label htmlFor="display_name" className="label block mb-1.5">
            Display Name
          </label>
          <input
            id="display_name"
            type="text"
            autoComplete="name"
            className={`input ${errors.display_name ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
            {...register('display_name')}
          />
          {errors.display_name && (
            <p className="mt-1.5 text-sm text-red-600">{errors.display_name.message}</p>
          )}
        </div>

        {/* Email */}
        <div>
          <label htmlFor="email" className="label block mb-1.5">
            Email Address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className={`input ${errors.email ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
            {...register('email')}
          />
          {errors.email && (
            <p className="mt-1.5 text-sm text-red-600">{errors.email.message}</p>
          )}
        </div>

        {/* Password */}
        <div>
          <label htmlFor="password" className="label block mb-1.5">
            Password
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

          {/* Password Strength Indicator */}
          {password && (
            <div className="mt-3 space-y-2">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${strength.color}`}
                    style={{ width: `${(strength.score / 6) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-600">{strength.label}</span>
              </div>

              <div className="grid grid-cols-2 gap-1">
                <PasswordRequirement met={password.length >= 8} text="8+ characters" />
                <PasswordRequirement met={/[a-z]/.test(password)} text="Lowercase" />
                <PasswordRequirement met={/[A-Z]/.test(password)} text="Uppercase" />
                <PasswordRequirement met={/\d/.test(password)} text="Number" />
                <PasswordRequirement
                  met={/[!@#$%^&*(),.?":{}|<>]/.test(password)}
                  text="Special char"
                />
              </div>
            </div>
          )}

          {errors.password && (
            <p className="mt-1.5 text-sm text-red-600">{errors.password.message}</p>
          )}
        </div>

        {/* Terms Checkbox */}
        <div className="flex items-start">
          <div className="flex items-center h-5">
            <input
              id="accepted_terms"
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              {...register('accepted_terms')}
            />
          </div>
          <div className="ml-3 text-sm">
            <label htmlFor="accepted_terms" className="text-gray-600">
              I agree to the{' '}
              <a href="/terms" className="text-primary-600 hover:text-primary-700">
                Terms of Service
              </a>{' '}
              and{' '}
              <a href="/privacy" className="text-primary-600 hover:text-primary-700">
                Privacy Policy
              </a>
            </label>
          </div>
        </div>
        {errors.accepted_terms && (
          <p className="text-sm text-red-600">{errors.accepted_terms.message}</p>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-primary btn-lg w-full"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Creating account...
            </>
          ) : (
            'Create account'
          )}
        </button>
      </form>
    </div>
  );
}
