/**
 * Checkout Cancel Page.
 *
 * Displayed when user cancels Stripe checkout. Offers options
 * to return to pricing or dashboard.
 */

import { XCircle, ArrowLeft, CreditCard } from 'lucide-react';
import { Link } from 'react-router-dom';

// =============================
// Main Component
// =============================

export function CheckoutCancelPage() {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4 py-12">
      <div className="max-w-lg w-full">
        {/* Cancel Card */}
        <div className="bg-gray-800 rounded-2xl p-8 text-center shadow-xl border border-gray-700">
          {/* Icon */}
          <div className="mx-auto w-20 h-20 rounded-full bg-gray-700 flex items-center justify-center mb-6">
            <XCircle className="w-10 h-10 text-gray-400" />
          </div>

          {/* Heading */}
          <h1 className="text-2xl font-bold text-white mb-2">
            Checkout Canceled
          </h1>
          <p className="text-gray-400 mb-8">
            No worries! You haven't been charged. Your account remains on the 
            free plan with all its features.
          </p>

          {/* Info Box */}
          <div className="bg-gray-900/50 rounded-lg p-4 mb-8 text-left">
            <h2 className="text-white font-medium mb-2 flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-cyan-400" />
              Ready when you are
            </h2>
            <p className="text-gray-400 text-sm">
              You can upgrade anytime from the pricing page or your account 
              settings. Premium features include unlimited generations, 
              priority processing, and STEP exports.
            </p>
          </div>

          {/* CTAs */}
          <div className="space-y-3">
            <Link
              to="/pricing"
              className="block w-full py-3 px-4 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-medium hover:from-cyan-600 hover:to-blue-600 transition-all"
            >
              View Plans Again
            </Link>
            <Link
              to="/dashboard"
              className="flex items-center justify-center gap-2 w-full py-3 px-4 rounded-lg bg-gray-700 text-white font-medium hover:bg-gray-600 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Dashboard
            </Link>
          </div>
        </div>

        {/* Help Link */}
        <p className="text-center text-gray-500 text-sm mt-6">
          Have questions?{' '}
          <a 
            href="mailto:support@aipartdesigner.com" 
            className="text-cyan-400 hover:underline"
          >
            Contact support
          </a>
        </p>
      </div>
    </div>
  );
}

export default CheckoutCancelPage;
