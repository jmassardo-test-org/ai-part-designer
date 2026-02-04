/**
 * Privacy Policy Page.
 * 
 * Displays the privacy policy with data handling practices,
 * GDPR/CCPA compliance information, and user rights.
 */

import { Link } from 'react-router-dom';
import { Shield, Eye, Lock, Globe, Database, UserCheck, Trash2, Download, Mail } from 'lucide-react';
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
  { id: 'overview', title: '1. Overview' },
  { id: 'data-collection', title: '2. Data We Collect' },
  { id: 'data-usage', title: '3. How We Use Your Data' },
  { id: 'ai-processing', title: '4. AI Data Processing' },
  { id: 'data-sharing', title: '5. Data Sharing' },
  { id: 'data-retention', title: '6. Data Retention' },
  { id: 'your-rights', title: '7. Your Rights (GDPR/CCPA)' },
  { id: 'security', title: '8. Security Measures' },
  { id: 'cookies', title: '9. Cookies & Tracking' },
  { id: 'children', title: '10. Children\'s Privacy' },
  { id: 'international', title: '11. International Transfers' },
  { id: 'changes', title: '12. Policy Changes' },
  { id: 'contact', title: '13. Contact Us' },
];

// =============================
// Data Rights Card Component
// =============================

interface RightsCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function RightsCard({ icon, title, description }: RightsCardProps) {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 text-cyan-400">{icon}</div>
        <div>
          <h4 className="font-medium text-white mb-1">{title}</h4>
          <p className="text-sm text-gray-400">{description}</p>
        </div>
      </div>
    </div>
  );
}

// =============================
// Main Privacy Page Component
// =============================

export function PrivacyPage() {
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
          <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/20 rounded-full px-4 py-1.5 mb-6">
            <Shield className="h-4 w-4 text-green-400" />
            <span className="text-sm font-medium text-green-400">Privacy</span>
          </div>
          <h1 className="text-4xl font-bold text-white">Privacy Policy</h1>
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
            <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-6 mb-12">
              <div className="flex items-start gap-4">
                <Shield className="h-6 w-6 text-green-400 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-white mb-2">Your Privacy Matters</h3>
                  <p className="text-gray-400 text-sm">
                    At AssemblematicAI, we're committed to protecting your privacy and being
                    transparent about how we handle your data. This policy explains what data
                    we collect, how we use it, and your rights regarding your information.
                  </p>
                </div>
              </div>
            </div>

            <Section id="overview" title="1. Overview">
              <p>
                AssemblematicAI ("we", "our", "us") operates the AssemblematicAI platform,
                which provides AI-powered CAD generation services. This Privacy Policy
                describes how we collect, use, and protect your personal information when
                you use our Service.
              </p>
              <p>
                We comply with applicable data protection laws, including the General Data
                Protection Regulation (GDPR) for European users and the California Consumer
                Privacy Act (CCPA) for California residents.
              </p>
            </Section>

            <Section id="data-collection" title="2. Data We Collect">
              <h3 className="text-lg font-medium text-white mb-2">Information You Provide</h3>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong className="text-white">Account Information:</strong> Name, email address, password (hashed), profile picture</li>
                <li><strong className="text-white">Billing Information:</strong> Payment method details (processed by Stripe), billing address</li>
                <li><strong className="text-white">Design Data:</strong> Prompts you enter, CAD files you upload, generated models</li>
                <li><strong className="text-white">Communications:</strong> Support tickets, feedback, and correspondence with us</li>
              </ul>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">Information We Collect Automatically</h3>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong className="text-white">Usage Data:</strong> Features used, generation counts, session duration</li>
                <li><strong className="text-white">Device Information:</strong> Browser type, operating system, device type</li>
                <li><strong className="text-white">Log Data:</strong> IP address, access times, pages viewed, error logs</li>
                <li><strong className="text-white">Cookies:</strong> Session identifiers, preferences (see Cookie section)</li>
              </ul>
            </Section>

            <Section id="data-usage" title="3. How We Use Your Data">
              <p>We use your information to:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Provide, maintain, and improve the Service</li>
                <li>Process your CAD generation requests</li>
                <li>Process payments and manage subscriptions</li>
                <li>Send service-related communications and updates</li>
                <li>Provide customer support</li>
                <li>Detect and prevent fraud or abuse</li>
                <li>Comply with legal obligations</li>
                <li>Analyze usage patterns to improve the Service (anonymized)</li>
              </ul>

              <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-4 mt-6">
                <p className="text-sm text-cyan-300">
                  <strong>Important:</strong> We do NOT sell your personal information to third parties.
                  We do NOT use your designs or prompts to train our AI models.
                </p>
              </div>
            </Section>

            <Section id="ai-processing" title="4. AI Data Processing">
              <p>
                When you use our AI-powered features, your data is processed as follows:
              </p>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">Ollama (Self-Hosted Models)</h3>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Runs on our secure servers</li>
                <li>Your prompts are processed locally and not sent to third parties</li>
                <li>No data retention by the model itself</li>
              </ul>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">OpenAI API (When Used)</h3>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Used for complex natural language understanding</li>
                <li>Data processed under OpenAI's Enterprise Data Processing Agreement</li>
                <li>OpenAI does NOT use our API data to train their models</li>
                <li>Data is deleted from OpenAI's systems after processing</li>
              </ul>

              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 mt-6">
                <p className="text-sm text-yellow-300">
                  <strong>Note:</strong> We never use your designs, prompts, or generated content
                  to train any AI models. Your creative work remains exclusively yours.
                </p>
              </div>
            </Section>

            <Section id="data-sharing" title="5. Data Sharing">
              <p>We may share your information with:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong className="text-white">Service Providers:</strong> Stripe (payments), AWS (hosting), Cloudflare (CDN/security)</li>
                <li><strong className="text-white">Analytics Partners:</strong> Anonymized usage data only</li>
                <li><strong className="text-white">Legal Authorities:</strong> When required by law or to protect rights</li>
                <li><strong className="text-white">Business Transfers:</strong> In case of merger, acquisition, or sale</li>
              </ul>

              <p className="mt-4">
                All third-party service providers are bound by data processing agreements
                that ensure they handle your data in accordance with this policy.
              </p>
            </Section>

            <Section id="data-retention" title="6. Data Retention">
              <p>We retain your data as follows:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong className="text-white">Account Data:</strong> While your account is active, plus 30 days after deletion</li>
                <li><strong className="text-white">Design Data:</strong> While your account is active; moved to trash for 30 days before permanent deletion</li>
                <li><strong className="text-white">Billing Records:</strong> 7 years (legal/tax requirements)</li>
                <li><strong className="text-white">Log Data:</strong> 90 days for security purposes</li>
                <li><strong className="text-white">Support Communications:</strong> 3 years or as required by law</li>
              </ul>
            </Section>

            <Section id="your-rights" title="7. Your Rights (GDPR/CCPA)">
              <p>You have the following rights regarding your personal data:</p>
              
              <div className="grid md:grid-cols-2 gap-4 mt-6">
                <RightsCard
                  icon={<Eye className="h-5 w-5" />}
                  title="Right to Access"
                  description="Request a copy of all personal data we hold about you."
                />
                <RightsCard
                  icon={<UserCheck className="h-5 w-5" />}
                  title="Right to Rectification"
                  description="Update or correct inaccurate personal information."
                />
                <RightsCard
                  icon={<Trash2 className="h-5 w-5" />}
                  title="Right to Deletion"
                  description="Request deletion of your personal data ('right to be forgotten')."
                />
                <RightsCard
                  icon={<Download className="h-5 w-5" />}
                  title="Right to Portability"
                  description="Export your data in a machine-readable format."
                />
                <RightsCard
                  icon={<Lock className="h-5 w-5" />}
                  title="Right to Restrict"
                  description="Limit how we process your personal data."
                />
                <RightsCard
                  icon={<Mail className="h-5 w-5" />}
                  title="Right to Object"
                  description="Object to processing for marketing or legitimate interests."
                />
              </div>

              <p className="mt-6">
                To exercise any of these rights, please contact us at{' '}
                <a href="mailto:privacy@assemblematicai.com" className="text-cyan-400 hover:underline">
                  privacy@assemblematicai.com
                </a>. We will respond within 30 days.
              </p>

              <h3 className="text-lg font-medium text-white mt-6 mb-2">California Residents (CCPA)</h3>
              <p>
                If you are a California resident, you have additional rights under the CCPA:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Right to know what personal information is collected</li>
                <li>Right to know if your data is sold or disclosed</li>
                <li>Right to opt-out of the sale of personal information</li>
                <li>Right to non-discrimination for exercising your rights</li>
              </ul>
              <p className="mt-2">
                <strong className="text-white">We do not sell your personal information.</strong>
              </p>
            </Section>

            <Section id="security" title="8. Security Measures">
              <p>We implement industry-standard security measures:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong className="text-white">Encryption:</strong> TLS 1.3 for data in transit, AES-256 for data at rest</li>
                <li><strong className="text-white">Access Controls:</strong> Role-based access, multi-factor authentication</li>
                <li><strong className="text-white">Infrastructure:</strong> SOC 2 compliant cloud providers</li>
                <li><strong className="text-white">Monitoring:</strong> 24/7 security monitoring and intrusion detection</li>
                <li><strong className="text-white">Audits:</strong> Regular security assessments and penetration testing</li>
              </ul>

              <p className="mt-4">
                While we take extensive measures to protect your data, no method of transmission
                or storage is 100% secure. We encourage you to use strong passwords and enable
                two-factor authentication on your account.
              </p>
            </Section>

            <Section id="cookies" title="9. Cookies & Tracking">
              <p>We use cookies and similar technologies for:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong className="text-white">Essential Cookies:</strong> Required for the Service to function (authentication, security)</li>
                <li><strong className="text-white">Preference Cookies:</strong> Remember your settings (theme, language)</li>
                <li><strong className="text-white">Analytics Cookies:</strong> Understand how you use the Service (can be disabled)</li>
              </ul>

              <p className="mt-4">
                You can control cookies through your browser settings. Note that disabling
                essential cookies may affect the functionality of the Service.
              </p>
            </Section>

            <Section id="children" title="10. Children's Privacy">
              <p>
                Our Service is not intended for children under 18 years of age. We do not
                knowingly collect personal information from children. If you believe we have
                collected information from a child, please contact us immediately.
              </p>
            </Section>

            <Section id="international" title="11. International Transfers">
              <p>
                Your data may be processed in countries other than your own. We ensure
                appropriate safeguards are in place for international transfers:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Standard Contractual Clauses (SCCs) for EU data transfers</li>
                <li>Data Processing Agreements with all service providers</li>
                <li>Compliance with applicable data protection frameworks</li>
              </ul>
            </Section>

            <Section id="changes" title="12. Policy Changes">
              <p>
                We may update this Privacy Policy from time to time. We will notify you of
                significant changes by email or through a prominent notice on the Service
                at least 30 days before changes take effect.
              </p>
              <p>
                We encourage you to review this policy periodically for any updates.
              </p>
            </Section>

            <Section id="contact" title="13. Contact Us">
              <p>
                For privacy-related inquiries, please contact our Data Protection Officer:
              </p>
              <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 mt-4">
                <p className="text-white font-medium">Data Protection Officer</p>
                <p className="text-gray-400">Email: privacy@assemblematicai.com</p>
                <p className="text-gray-400">Address: 123 Innovation Way, San Francisco, CA 94107</p>
              </div>

              <p className="mt-6">
                You also have the right to lodge a complaint with a supervisory authority if
                you believe your data protection rights have been violated.
              </p>
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
              <Link to="/terms" className="hover:text-white">Terms</Link>
              <Link to="/privacy" className="hover:text-white text-cyan-400">Privacy</Link>
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

export default PrivacyPage;
