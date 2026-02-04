/**
 * Contact Page.
 * 
 * Contact form for visitors to reach out to the team.
 * Includes honeypot spam protection and form validation.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Send, 
  Mail, 
  MessageSquare, 
  User, 
  Loader2, 
  CheckCircle, 
  AlertCircle,
  MapPin,
  Clock,
  HelpCircle,
} from 'lucide-react';
import { LogoLight, LogoIcon } from '@/components/brand';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { cn } from '@/lib/utils';

// =============================
// Types
// =============================

interface ContactFormData {
  name: string;
  email: string;
  subject: string;
  message: string;
  // Honeypot field - should remain empty
  website: string;
}

type FormStatus = 'idle' | 'submitting' | 'success' | 'error';

interface FormErrors {
  name?: string;
  email?: string;
  subject?: string;
  message?: string;
}

// =============================
// Contact Info Card
// =============================

interface ContactInfoCardProps {
  icon: React.ReactNode;
  title: string;
  content: string;
  link?: string;
}

function ContactInfoCard({ icon, title, content, link }: ContactInfoCardProps) {
  const ContentWrapper = link ? 'a' : 'div';
  const wrapperProps = link ? { href: link, className: 'hover:text-cyan-400 transition-colors' } : {};

  return (
    <div className="flex items-start gap-4">
      <div className="flex-shrink-0 w-10 h-10 bg-cyan-500/10 rounded-lg flex items-center justify-center text-cyan-400">
        {icon}
      </div>
      <div>
        <h3 className="font-medium text-white mb-1">{title}</h3>
        <ContentWrapper {...wrapperProps}>
          <p className="text-gray-400 text-sm">{content}</p>
        </ContentWrapper>
      </div>
    </div>
  );
}

// =============================
// Form Field Component
// =============================

interface FormFieldProps {
  label: string;
  name: string;
  type?: 'text' | 'email' | 'textarea';
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  error?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}

function FormField({ 
  label, 
  name, 
  type = 'text', 
  value, 
  onChange, 
  error, 
  placeholder,
  required = false,
  disabled = false,
}: FormFieldProps) {
  const baseClasses = cn(
    'w-full bg-gray-800/50 border rounded-lg px-4 py-3 text-white placeholder-gray-500',
    'focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
    'disabled:opacity-50 disabled:cursor-not-allowed',
    error ? 'border-red-500' : 'border-gray-700'
  );

  return (
    <div className="space-y-2">
      <label htmlFor={name} className="block text-sm font-medium text-gray-300">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      {type === 'textarea' ? (
        <textarea
          id={name}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          rows={5}
          className={cn(baseClasses, 'resize-none')}
        />
      ) : (
        <input
          type={type}
          id={name}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          className={baseClasses}
        />
      )}
      {error && (
        <p className="text-sm text-red-400 flex items-center gap-1">
          <AlertCircle className="h-4 w-4" />
          {error}
        </p>
      )}
    </div>
  );
}

// =============================
// Validation Functions
// =============================

function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function validateForm(data: ContactFormData): FormErrors {
  const errors: FormErrors = {};

  if (!data.name.trim()) {
    errors.name = 'Name is required';
  } else if (data.name.trim().length < 2) {
    errors.name = 'Name must be at least 2 characters';
  }

  if (!data.email.trim()) {
    errors.email = 'Email is required';
  } else if (!validateEmail(data.email)) {
    errors.email = 'Please enter a valid email address';
  }

  if (!data.subject.trim()) {
    errors.subject = 'Subject is required';
  } else if (data.subject.trim().length < 5) {
    errors.subject = 'Subject must be at least 5 characters';
  }

  if (!data.message.trim()) {
    errors.message = 'Message is required';
  } else if (data.message.trim().length < 20) {
    errors.message = 'Message must be at least 20 characters';
  }

  return errors;
}

// =============================
// Main Contact Page Component
// =============================

export function ContactPage() {
  const [formData, setFormData] = useState<ContactFormData>({
    name: '',
    email: '',
    subject: '',
    message: '',
    website: '', // Honeypot
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [status, setStatus] = useState<FormStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Honeypot check - if website field is filled, it's likely a bot
    if (formData.website) {
      // Silently pretend success to bots
      setStatus('success');
      return;
    }

    // Validate form
    const validationErrors = validateForm(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setStatus('submitting');
    setErrorMessage('');

    try {
      const response = await fetch('/api/v1/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name.trim(),
          email: formData.email.trim(),
          subject: formData.subject.trim(),
          message: formData.message.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to send message');
      }

      setStatus('success');
      setFormData({ name: '', email: '', subject: '', message: '', website: '' });
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'An unexpected error occurred');
    }
  };

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
          <div className="inline-flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/20 rounded-full px-4 py-1.5 mb-6">
            <MessageSquare className="h-4 w-4 text-cyan-400" />
            <span className="text-sm font-medium text-cyan-400">Get in Touch</span>
          </div>
          <h1 className="text-4xl font-bold text-white">Contact Us</h1>
          <p className="mt-4 text-gray-400 max-w-2xl mx-auto">
            Have questions about AssemblematicAI? We'd love to hear from you.
            Send us a message and we'll respond as soon as possible.
          </p>
        </div>
      </section>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid lg:grid-cols-3 gap-12">
          {/* Contact Information */}
          <div className="lg:col-span-1 space-y-8">
            <div>
              <h2 className="text-xl font-semibold text-white mb-6">Contact Information</h2>
              <div className="space-y-6">
                <ContactInfoCard
                  icon={<Mail className="h-5 w-5" />}
                  title="Email"
                  content="support@assemblematicai.com"
                  link="mailto:support@assemblematicai.com"
                />
                <ContactInfoCard
                  icon={<MapPin className="h-5 w-5" />}
                  title="Address"
                  content="123 Innovation Way, San Francisco, CA 94107"
                />
                <ContactInfoCard
                  icon={<Clock className="h-5 w-5" />}
                  title="Response Time"
                  content="We typically respond within 24-48 hours"
                />
              </div>
            </div>

            {/* FAQ Link */}
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center text-purple-400">
                  <HelpCircle className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-medium text-white mb-1">Looking for Answers?</h3>
                  <p className="text-gray-400 text-sm mb-3">
                    Check out our FAQ section for quick answers to common questions.
                  </p>
                  <Link 
                    to="/pricing#faq"
                    className="text-sm text-cyan-400 hover:text-cyan-300 font-medium"
                  >
                    View FAQ →
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Contact Form */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-6 lg:p-8">
              <h2 className="text-xl font-semibold text-white mb-6">Send Us a Message</h2>

              {/* Success Message */}
              {status === 'success' && (
                <div className="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-medium text-green-400">Message Sent!</h3>
                    <p className="text-sm text-gray-400 mt-1">
                      Thank you for reaching out. We'll get back to you within 24-48 hours.
                    </p>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {status === 'error' && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-medium text-red-400">Failed to Send</h3>
                    <p className="text-sm text-gray-400 mt-1">
                      {errorMessage || 'Something went wrong. Please try again or email us directly.'}
                    </p>
                  </div>
                </div>
              )}

              {status !== 'success' && (
                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Honeypot field - hidden from users */}
                  <div className="hidden" aria-hidden="true">
                    <label htmlFor="website">Website</label>
                    <input
                      type="text"
                      id="website"
                      name="website"
                      value={formData.website}
                      onChange={handleChange}
                      tabIndex={-1}
                      autoComplete="off"
                    />
                  </div>

                  <div className="grid md:grid-cols-2 gap-6">
                    <FormField
                      label="Your Name"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      error={errors.name}
                      placeholder="John Doe"
                      required
                      disabled={status === 'submitting'}
                    />
                    <FormField
                      label="Email Address"
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={handleChange}
                      error={errors.email}
                      placeholder="john@example.com"
                      required
                      disabled={status === 'submitting'}
                    />
                  </div>

                  <FormField
                    label="Subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    error={errors.subject}
                    placeholder="How can we help you?"
                    required
                    disabled={status === 'submitting'}
                  />

                  <FormField
                    label="Message"
                    name="message"
                    type="textarea"
                    value={formData.message}
                    onChange={handleChange}
                    error={errors.message}
                    placeholder="Tell us more about your inquiry..."
                    required
                    disabled={status === 'submitting'}
                  />

                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-500">
                      <span className="text-red-400">*</span> Required fields
                    </p>
                    <button
                      type="submit"
                      disabled={status === 'submitting'}
                      className={cn(
                        'flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all',
                        'bg-cyan-500 text-white hover:bg-cyan-600',
                        'disabled:opacity-50 disabled:cursor-not-allowed'
                      )}
                    >
                      {status === 'submitting' ? (
                        <>
                          <Loader2 className="h-5 w-5 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        <>
                          <Send className="h-5 w-5" />
                          Send Message
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}

              {status === 'success' && (
                <button
                  onClick={() => setStatus('idle')}
                  className="text-sm text-cyan-400 hover:text-cyan-300 font-medium"
                >
                  Send another message →
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-12 mt-8">
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
              <Link to="/privacy" className="hover:text-white">Privacy</Link>
              <Link to="/contact" className="hover:text-white text-cyan-400">Contact</Link>
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

export default ContactPage;
