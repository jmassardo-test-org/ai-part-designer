/**
 * Terms of Service Page.
 * 
 * Displays the terms of service with AI model disclosure
 * and legal terms for using the platform.
 */

import { Link } from 'react-router-dom';
import { FileText, Shield, Scale, AlertTriangle, ExternalLink } from 'lucide-react';
import { LogoLight, LogoIcon } from '@/components/brand';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

// =============================
// Section Component
// =============================

interface SectionProps {
  id: string;
  title: string;
  children: React.ReactNode;
}

function Section({ id, title, children }: SectionProps) {
  return (
    <section id={id} className="mb-12">
      <h2 className="text-xl font-semibold text-white mb-4">{title}</h2>
      <div className="text-gray-400 space-y-4 leading-relaxed">
        {children}
      </div>
    </section>
  );
}

// =============================
// Table of Contents
// =============================

const TOC_ITEMS = [
  { id: 'acceptance', title: '1. Acceptance of Terms' },
  { id: 'ai-disclosure', title: '2. AI Technology Disclosure' },
  { id: 'account', title: '3. Account Terms' },
  { id: 'usage', title: '4. Acceptable Use' },
  { id: 'intellectual-property', title: '5. Intellectual Property' },
  { id: 'subscriptions', title: '6. Subscriptions & Billing' },
  { id: 'liability', title: '7. Limitation of Liability' },
  { id: 'indemnification', title: '8. Indemnification' },
  { id: 'termination', title: '9. Termination' },
  { id: 'changes', title: '10. Changes to Terms' },
  { id: 'contact', title: '11. Contact Us' },
];

// =============================
// Main Terms Page Component
// =============================

export function TermsPage() {
  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center">
              <LogoLight size="md" />
            </Link>

            <div className="flex items-center gap-4">
              <ThemeToggle size="sm" />
              <Link
                to="/login"
                className="text-gray-300 hover:text-white font-medium"
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

      {/* Hero Section */}
      <section className="py-12 lg:py-16 border-b border-gray-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 mb-6">
            <FileText className="h-4 w-4 text-blue-400" />
            <span className="text-sm font-medium text-blue-400">Legal</span>
          </div>
          <h1 className="text-4xl font-bold text-white">Terms of Service</h1>
          <p className="mt-4 text-gray-400">
            Last updated: January 15, 2026
          </p>
        </div>
      </section>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid lg:grid-cols-4 gap-8">
          {/* Table of Contents - Sidebar */}
          <nav className="lg:col-span-1">
            <div className="sticky top-8">
              <h3 className="text-sm font-semibold text-white mb-4">Contents</h3>
              <ul className="space-y-2">
                {TOC_ITEMS.map((item) => (
                  <li key={item.id}>
                    <a
                      href={`#${item.id}`}
                      className="text-sm text-gray-400 hover:text-cyan-400 transition-colors"
                    >
                      {item.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </nav>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {/* Introduction */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6 mb-12">
              <div className="flex items-start gap-4">
                <Scale className="h-6 w-6 text-blue-400 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-white mb-2">Welcome to AssemblematicAI</h3>
                  <p className="text-gray-400 text-sm">
                    These Terms of Service ("Terms") govern your use of the AssemblematicAI platform
                    and services. By using our service, you agree to be bound by these terms.
                    Please read them carefully.
                  </p>
                </div>
              </div>
            </div>

            <Section id="acceptance" title="1. Acceptance of Terms">
              <p>
                By accessing or using AssemblematicAI ("Service", "Platform", "we", "our", "us"),
                you agree to be bound by these Terms of Service and all applicable laws and
                regulations. If you do not agree with any of these terms, you are prohibited
                from using or accessing this Service.
              </p>
              <p>
                These Terms apply to all visitors, users, and others who access or use the
                Service, including free and paid subscription tiers.
              </p>
            </Section>

            <Section id="ai-disclosure" title="2. AI Technology Disclosure">
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 mb-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-yellow-400 mb-1">Important AI Disclosure</h4>
                    <p className="text-sm text-gray-400">
                      AssemblematicAI uses artificial intelligence to generate CAD models and code.
                      Please review this section carefully.
                    </p>
                  </div>
                </div>
              </div>

              <h3 className="text-lg font-medium text-white mb-2">AI Models Used</h3>
              <p>Our platform utilizes the following AI technologies:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>
                  <strong className="text-white">Ollama (Local Models)</strong>: For local processing
                  of CAD generation requests. Models run on our secure servers and do not transmit
                  your data to third parties.
                </li>
                <li>
                  <strong className="text-white">OpenAI API</strong>: For complex natural language
                  understanding and code generation. Data is processed according to OpenAI's
                  enterprise data handling policies.
                </li>
                <li>
                  <strong className="text-white">CadQuery</strong>: Open-source parametric CAD engine
                  for generating 3D models from Python code.
                </li>
              </ul>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">AI Limitations</h3>
              <p>You acknowledge and agree that:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>AI-generated outputs may contain errors and should be reviewed before use</li>
                <li>Generated CAD models require verification for structural and dimensional accuracy</li>
                <li>The AI may not always produce optimal designs for your specific use case</li>
                <li>Critical applications require professional engineering review</li>
              </ul>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">Data Handling</h3>
              <p>
                We do <strong className="text-white">NOT</strong> use your designs, prompts, or
                generated content to train our AI models. Your data remains your property and is
                processed solely to provide the Service.
              </p>
            </Section>

            <Section id="account" title="3. Account Terms">
              <p>
                To access certain features of the Service, you must register for an account.
                You agree to:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Provide accurate, current, and complete information during registration</li>
                <li>Maintain and promptly update your account information</li>
                <li>Maintain the security of your password and account</li>
                <li>Accept responsibility for all activities under your account</li>
                <li>Notify us immediately of any unauthorized use of your account</li>
              </ul>
              <p className="mt-4">
                You must be at least 18 years old to create an account. By creating an account,
                you represent that you meet this age requirement.
              </p>
            </Section>

            <Section id="usage" title="4. Acceptable Use">
              <p>You agree not to use the Service to:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Violate any applicable laws or regulations</li>
                <li>Generate designs for weapons, illegal items, or harmful purposes</li>
                <li>Infringe upon intellectual property rights of others</li>
                <li>Attempt to reverse-engineer our AI models or algorithms</li>
                <li>Overwhelm our systems with excessive requests (rate limiting applies)</li>
                <li>Share account credentials or resell access to the Service</li>
                <li>Upload malicious code or attempt to compromise system security</li>
              </ul>
              <p className="mt-4">
                We reserve the right to suspend or terminate accounts that violate these terms.
              </p>
            </Section>

            <Section id="intellectual-property" title="5. Intellectual Property">
              <h3 className="text-lg font-medium text-white mb-2">Your Content</h3>
              <p>
                You retain all rights to designs, prompts, and content you create using the
                Service. By using the Service, you grant us a limited license to process,
                store, and display your content solely to provide the Service to you.
              </p>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">Generated Content</h3>
              <p>
                CAD models and code generated by our AI are provided to you for your use.
                You own the generated outputs and may use them for personal or commercial
                purposes, subject to these Terms.
              </p>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">Our Platform</h3>
              <p>
                The Service, including its original content, features, and functionality,
                is owned by AssemblematicAI and is protected by international copyright,
                trademark, and other intellectual property laws.
              </p>
            </Section>

            <Section id="subscriptions" title="6. Subscriptions & Billing">
              <p>
                Some features of the Service are available only through paid subscriptions.
                By subscribing, you agree to:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Pay all applicable fees based on your selected plan</li>
                <li>Provide accurate billing information</li>
                <li>Authorize recurring charges for subscription renewals</li>
              </ul>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">Billing & Renewal</h3>
              <p>
                Subscriptions automatically renew at the end of each billing period unless
                cancelled. You may cancel at any time; access continues until the end of
                the current billing period.
              </p>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">Refunds</h3>
              <p>
                Refunds are provided at our discretion. If you're unsatisfied with the
                Service within the first 14 days of a paid subscription, contact us for
                a review of your refund request.
              </p>
            </Section>

            <Section id="liability" title="7. Limitation of Liability">
              <p>
                TO THE MAXIMUM EXTENT PERMITTED BY LAW, ASSEMBLEMATICAI SHALL NOT BE LIABLE
                FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES,
                INCLUDING BUT NOT LIMITED TO:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Loss of profits, data, or business opportunities</li>
                <li>Manufacturing defects from generated designs</li>
                <li>Errors or inaccuracies in AI-generated content</li>
                <li>Service interruptions or downtime</li>
              </ul>
              <p className="mt-4">
                Our total liability for any claim arising from the Service shall not exceed
                the amount paid by you for the Service in the twelve (12) months preceding
                the claim.
              </p>
            </Section>

            <Section id="indemnification" title="8. Indemnification">
              <p>
                You agree to indemnify and hold harmless AssemblematicAI, its officers,
                directors, employees, and agents from any claims, damages, losses, or
                expenses (including reasonable attorneys' fees) arising from:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Your use of the Service</li>
                <li>Your violation of these Terms</li>
                <li>Your violation of any third-party rights</li>
                <li>Products manufactured using generated designs</li>
              </ul>
            </Section>

            <Section id="termination" title="9. Termination">
              <p>
                We may terminate or suspend your account and access to the Service
                immediately, without prior notice or liability, for any reason, including
                breach of these Terms.
              </p>
              <p>
                Upon termination, your right to use the Service will cease immediately.
                You may export your designs before account closure. We will retain your
                data for 30 days after termination to allow for data export, after which
                it will be permanently deleted.
              </p>
            </Section>

            <Section id="changes" title="10. Changes to Terms">
              <p>
                We reserve the right to modify these Terms at any time. We will notify
                users of material changes via email or through the Service at least 30
                days before they take effect.
              </p>
              <p>
                Your continued use of the Service after changes become effective
                constitutes acceptance of the modified Terms.
              </p>
            </Section>

            <Section id="contact" title="11. Contact Us">
              <p>
                If you have questions about these Terms, please contact us:
              </p>
              <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 mt-4">
                <p className="text-white font-medium">AssemblematicAI Legal Team</p>
                <p className="text-gray-400">Email: legal@assemblematicai.com</p>
                <p className="text-gray-400">Address: 123 Innovation Way, San Francisco, CA 94107</p>
              </div>
            </Section>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center gap-2 mb-4 md:mb-0">
              <LogoIcon size={24} />
              <span className="font-semibold text-white">AssemblematicAI</span>
            </div>
            <div className="flex gap-6 text-sm text-gray-400">
              <Link to="/demo" className="hover:text-white">Demo</Link>
              <Link to="/pricing" className="hover:text-white">Pricing</Link>
              <Link to="/terms" className="hover:text-white text-cyan-400">Terms</Link>
              <Link to="/privacy" className="hover:text-white">Privacy</Link>
              <Link to="/contact" className="hover:text-white">Contact</Link>
            </div>
          </div>
          <p className="mt-8 text-center text-sm text-gray-500">
            © 2026 AssemblematicAI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default TermsPage;
