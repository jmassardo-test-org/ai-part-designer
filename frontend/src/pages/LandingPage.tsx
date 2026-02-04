/**
 * Landing page component.
 * Supports light and dark themes.
 */

import { Sparkles, Layers, Download, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LogoLight, LogoIcon } from '@/components/brand';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-industrial-bg-primary">
      {/* Header */}
      <header className="border-b border-gray-100 dark:border-industrial-border-DEFAULT">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center">
              <LogoLight size="md" />
            </Link>

            <div className="flex items-center gap-4">
              <ThemeToggle size="sm" />
              <Link
                to="/login"
                className="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white font-medium"
              >
                Sign in
              </Link>
              <Link to="/register" className="btn-primary btn-md">
                Get started
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-20 lg:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-4xl lg:text-6xl font-bold text-gray-900 dark:text-white leading-tight">
              Design 3D parts with{' '}
              <span className="text-primary-600 dark:text-accent-400">natural language</span>
            </h1>
            <p className="mt-6 text-xl text-gray-600 dark:text-gray-300">
              Describe what you need, and our AI will generate production-ready CAD files.
              Export to STEP or STL for 3D printing or manufacturing.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register" className="btn-primary btn-lg">
                Start designing free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link to="/demo" className="btn-outline btn-lg">Watch demo</Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-gray-50 dark:bg-industrial-bg-secondary">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">How it works</h2>
            <p className="mt-4 text-xl text-gray-600 dark:text-gray-300">
              From idea to manufactured part in minutes
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white dark:bg-industrial-bg-elevated p-8 rounded-xl shadow-sm border border-gray-100 dark:border-industrial-border-DEFAULT">
              <div className="h-12 w-12 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center mb-6">
                <Sparkles className="h-6 w-6 text-primary-600 dark:text-accent-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Describe your part
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Use natural language to describe dimensions, features, and requirements.
                &quot;A box 100x50x30mm with a 10mm mounting hole in each corner.&quot;
              </p>
            </div>

            <div className="bg-white dark:bg-industrial-bg-elevated p-8 rounded-xl shadow-sm border border-gray-100 dark:border-industrial-border-DEFAULT">
              <div className="h-12 w-12 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center mb-6">
                <Layers className="h-6 w-6 text-primary-600 dark:text-accent-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Preview & customize
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                See your part rendered in 3D. Adjust parameters, add fillets, or refine
                details until it&apos;s perfect.
              </p>
            </div>

            <div className="bg-white dark:bg-industrial-bg-elevated p-8 rounded-xl shadow-sm border border-gray-100 dark:border-industrial-border-DEFAULT">
              <div className="h-12 w-12 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center mb-6">
                <Download className="h-6 w-6 text-primary-600 dark:text-accent-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Export & manufacture
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Download STEP files for CNC machining or STL for 3D printing.
                Production-ready quality guaranteed.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-primary-600 dark:bg-gradient-to-r dark:from-primary-700 dark:to-accent-700 rounded-2xl p-12 text-center">
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to start designing?
            </h2>
            <p className="text-xl text-primary-100 dark:text-white/80 mb-8">
              Create your first part in under 5 minutes. No CAD experience required.
            </p>
            <Link to="/register" className="btn bg-white text-primary-600 hover:bg-gray-100 btn-lg">
              Create free account
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 dark:border-industrial-border-DEFAULT py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center gap-2 mb-4 md:mb-0">
              <LogoIcon size={24} />
              <span className="font-semibold text-gray-900 dark:text-white">AssemblematicAI</span>
            </div>
            <div className="flex gap-6 text-sm text-gray-600 dark:text-gray-400">
              <Link to="/terms" className="hover:text-gray-900 dark:hover:text-white">Terms</Link>
              <Link to="/privacy" className="hover:text-gray-900 dark:hover:text-white">Privacy</Link>
              <Link to="/docs" className="hover:text-gray-900 dark:hover:text-white">Documentation</Link>
              <Link to="/contact" className="hover:text-gray-900 dark:hover:text-white">Contact</Link>
            </div>
          </div>
          <p className="mt-8 text-center text-sm text-gray-400 dark:text-gray-500">
            © 2026 AssemblematicAI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
