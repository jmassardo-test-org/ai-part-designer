/**
 * Landing page component.
 */

import { Link } from 'react-router-dom';
import { Sparkles, Layers, Download, ArrowRight } from 'lucide-react';
import { LogoLight, LogoIcon } from '@/components/brand';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center">
              <LogoLight size="md" />
            </Link>

            <div className="flex items-center gap-4">
              <Link
                to="/login"
                className="text-gray-600 hover:text-gray-900 font-medium"
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
            <h1 className="text-4xl lg:text-6xl font-bold text-gray-900 leading-tight">
              Design 3D parts with{' '}
              <span className="text-primary-600">natural language</span>
            </h1>
            <p className="mt-6 text-xl text-gray-600">
              Describe what you need, and our AI will generate production-ready CAD files.
              Export to STEP or STL for 3D printing or manufacturing.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register" className="btn-primary btn-lg">
                Start designing free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <button className="btn-outline btn-lg">Watch demo</button>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900">How it works</h2>
            <p className="mt-4 text-xl text-gray-600">
              From idea to manufactured part in minutes
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100">
              <div className="h-12 w-12 bg-primary-100 rounded-lg flex items-center justify-center mb-6">
                <Sparkles className="h-6 w-6 text-primary-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Describe your part
              </h3>
              <p className="text-gray-600">
                Use natural language to describe dimensions, features, and requirements.
                &quot;A box 100x50x30mm with a 10mm mounting hole in each corner.&quot;
              </p>
            </div>

            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100">
              <div className="h-12 w-12 bg-primary-100 rounded-lg flex items-center justify-center mb-6">
                <Layers className="h-6 w-6 text-primary-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Preview & customize
              </h3>
              <p className="text-gray-600">
                See your part rendered in 3D. Adjust parameters, add fillets, or refine
                details until it&apos;s perfect.
              </p>
            </div>

            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100">
              <div className="h-12 w-12 bg-primary-100 rounded-lg flex items-center justify-center mb-6">
                <Download className="h-6 w-6 text-primary-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Export & manufacture
              </h3>
              <p className="text-gray-600">
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
          <div className="bg-primary-600 rounded-2xl p-12 text-center">
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to start designing?
            </h2>
            <p className="text-xl text-primary-100 mb-8">
              Create your first part in under 5 minutes. No CAD experience required.
            </p>
            <Link to="/register" className="btn bg-white text-primary-600 hover:bg-gray-100 btn-lg">
              Create free account
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center gap-2 mb-4 md:mb-0">
              <LogoIcon size={24} />
              <span className="font-semibold text-gray-900">AssemblematicAI</span>
            </div>
            <div className="flex gap-6 text-sm text-gray-500">
              <a href="/terms" className="hover:text-gray-700">Terms</a>
              <a href="/privacy" className="hover:text-gray-700">Privacy</a>
              <a href="/docs" className="hover:text-gray-700">Documentation</a>
              <a href="/contact" className="hover:text-gray-700">Contact</a>
            </div>
          </div>
          <p className="mt-8 text-center text-sm text-gray-400">
            © 2026 AssemblematicAI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
