/**
 * Contact Page Tests.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { server } from '@/test/mocks/server';
import { ContactPage } from './ContactPage';

// Mock the ThemeContext
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    resolvedTheme: 'dark',
    setTheme: vi.fn(),
    toggleTheme: vi.fn(),
    isLoading: false,
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock the WebSocketContext
vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({
    isConnected: false,
    connectionState: 'disconnected',
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    sendMessage: vi.fn(),
  }),
}));

// Mock the brand components
vi.mock('@/components/brand', () => ({
  LogoLight: () => <div data-testid="logo-light">Logo</div>,
  LogoIcon: () => <div data-testid="logo-icon">Icon</div>,
}));

// Helper to render with router
const renderWithRouter = (ui: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {ui}
    </BrowserRouter>
  );
};

describe('ContactPage', () => {
  beforeEach(() => {
    // Reset any runtime request handlers we may add during tests
    server.resetHandlers();
  });

  describe('Rendering', () => {
    it('renders the contact page with header', () => {
      renderWithRouter(<ContactPage />);

      expect(screen.getByText('Contact Us')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /get started/i })).toBeInTheDocument();
    });

    it('displays contact information', () => {
      renderWithRouter(<ContactPage />);

      expect(screen.getByText('Contact Information')).toBeInTheDocument();
      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('Address')).toBeInTheDocument();
      expect(screen.getByText('Response Time')).toBeInTheDocument();
    });

    it('renders the contact form', () => {
      renderWithRouter(<ContactPage />);

      expect(screen.getByText('Send Us a Message')).toBeInTheDocument();
      expect(screen.getByLabelText(/your name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/subject/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/message/i)).toBeInTheDocument();
    });

    it('renders the submit button', () => {
      renderWithRouter(<ContactPage />);

      expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument();
    });

    it('renders FAQ link', () => {
      renderWithRouter(<ContactPage />);

      expect(screen.getByText('Looking for Answers?')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /view faq/i })).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('shows error when submitting with empty name', async () => {
      renderWithRouter(<ContactPage />);

      const submitButton = screen.getByRole('button', { name: /send message/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument();
      });
    });

    it('shows error for short name', async () => {
      renderWithRouter(<ContactPage />);

      const nameInput = screen.getByLabelText(/your name/i);
      fireEvent.change(nameInput, { target: { value: 'J' } });

      const submitButton = screen.getByRole('button', { name: /send message/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/name must be at least 2 characters/i)).toBeInTheDocument();
      });
    });

    it('shows error for invalid email', async () => {
      renderWithRouter(<ContactPage />);

      const nameInput = screen.getByLabelText(/your name/i);
      const emailInput = screen.getByLabelText(/email address/i);
      const subjectInput = screen.getByLabelText(/subject/i);
      const messageInput = screen.getByLabelText(/message/i);
      
      // Fill all fields, but with an invalid email
      fireEvent.change(nameInput, { target: { value: 'John Doe' } });
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
      fireEvent.change(subjectInput, { target: { value: 'Question about pricing' } });
      fireEvent.change(messageInput, { target: { value: 'I would like to learn more about your products and services.' } });

      // Submit the form by submitting the form element directly
      const form = screen.getByRole('button', { name: /send message/i }).closest('form');
      expect(form).toBeInTheDocument();
      fireEvent.submit(form!);

      await waitFor(() => {
        expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
      });
    });

    it('shows error for short subject', async () => {
      renderWithRouter(<ContactPage />);

      const nameInput = screen.getByLabelText(/your name/i);
      const emailInput = screen.getByLabelText(/email address/i);
      const subjectInput = screen.getByLabelText(/subject/i);
      
      fireEvent.change(nameInput, { target: { value: 'John Doe' } });
      fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
      fireEvent.change(subjectInput, { target: { value: 'Hi' } });

      const submitButton = screen.getByRole('button', { name: /send message/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/subject must be at least 5 characters/i)).toBeInTheDocument();
      });
    });

    it('shows error for short message', async () => {
      renderWithRouter(<ContactPage />);

      const nameInput = screen.getByLabelText(/your name/i);
      const emailInput = screen.getByLabelText(/email address/i);
      const subjectInput = screen.getByLabelText(/subject/i);
      const messageInput = screen.getByLabelText(/message/i);
      
      fireEvent.change(nameInput, { target: { value: 'John Doe' } });
      fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
      fireEvent.change(subjectInput, { target: { value: 'Question about pricing' } });
      fireEvent.change(messageInput, { target: { value: 'Short' } });

      const submitButton = screen.getByRole('button', { name: /send message/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/message must be at least 20 characters/i)).toBeInTheDocument();
      });
    });

    it('clears error when user starts typing', async () => {
      renderWithRouter(<ContactPage />);

      const nameInput = screen.getByLabelText(/your name/i);
      const submitButton = screen.getByRole('button', { name: /send message/i });
      
      // Submit to show error
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument();
      });

      // Type to clear error
      fireEvent.change(nameInput, { target: { value: 'John' } });

      await waitFor(() => {
        expect(screen.queryByText(/name is required/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    const validFormData = {
      name: 'John Doe',
      email: 'john@example.com',
      subject: 'Question about pricing',
      message: 'I am interested in your Enterprise plan and would like to know more about the features.',
    };

    it('submits form successfully', async () => {
      // Set up MSW handler for successful submission
      server.use(
        http.post('/api/v1/contact', () => {
          return HttpResponse.json({ success: true, message: 'Message sent' });
        })
      );

      renderWithRouter(<ContactPage />);

      const nameInput = screen.getByLabelText(/your name/i);
      const emailInput = screen.getByLabelText(/email address/i);
      const subjectInput = screen.getByLabelText(/subject/i);
      const messageInput = screen.getByLabelText(/message/i);
      
      fireEvent.change(nameInput, { target: { value: validFormData.name } });
      fireEvent.change(emailInput, { target: { value: validFormData.email } });
      fireEvent.change(subjectInput, { target: { value: validFormData.subject } });
      fireEvent.change(messageInput, { target: { value: validFormData.message } });

      const submitButton = screen.getByRole('button', { name: /send message/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/message sent/i)).toBeInTheDocument();
      });
    });

    it('shows loading state during submission', async () => {
      // Set up MSW handler that never resolves to show loading state
      server.use(
        http.post('/api/v1/contact', () => {
          return new Promise(() => {}); // Never resolves
        })
      );

      renderWithRouter(<ContactPage />);

      const nameInput = screen.getByLabelText(/your name/i);
      const emailInput = screen.getByLabelText(/email address/i);
      const subjectInput = screen.getByLabelText(/subject/i);
      const messageInput = screen.getByLabelText(/message/i);
      
      fireEvent.change(nameInput, { target: { value: validFormData.name } });
      fireEvent.change(emailInput, { target: { value: validFormData.email } });
      fireEvent.change(subjectInput, { target: { value: validFormData.subject } });
      fireEvent.change(messageInput, { target: { value: validFormData.message } });

      const submitButton = screen.getByRole('button', { name: /send message/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/sending/i)).toBeInTheDocument();
      });
    });

    it('shows error on submission failure', async () => {
      // Set up MSW handler for failed submission
      server.use(
        http.post('/api/v1/contact', () => {
          return HttpResponse.json(
            { detail: 'Server error' },
            { status: 500 }
          );
        })
      );

      renderWithRouter(<ContactPage />);

      const nameInput = screen.getByLabelText(/your name/i);
      const emailInput = screen.getByLabelText(/email address/i);
      const subjectInput = screen.getByLabelText(/subject/i);
      const messageInput = screen.getByLabelText(/message/i);
      
      fireEvent.change(nameInput, { target: { value: validFormData.name } });
      fireEvent.change(emailInput, { target: { value: validFormData.email } });
      fireEvent.change(subjectInput, { target: { value: validFormData.subject } });
      fireEvent.change(messageInput, { target: { value: validFormData.message } });

      const submitButton = screen.getByRole('button', { name: /send message/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/failed to send/i)).toBeInTheDocument();
      });
    });

    it('allows sending another message after success', async () => {
      // Set up MSW handler for successful submission
      server.use(
        http.post('/api/v1/contact', () => {
          return HttpResponse.json({ success: true, message: 'Message sent' });
        })
      );

      renderWithRouter(<ContactPage />);

      const nameInput = screen.getByLabelText(/your name/i);
      const emailInput = screen.getByLabelText(/email address/i);
      const subjectInput = screen.getByLabelText(/subject/i);
      const messageInput = screen.getByLabelText(/message/i);
      
      fireEvent.change(nameInput, { target: { value: validFormData.name } });
      fireEvent.change(emailInput, { target: { value: validFormData.email } });
      fireEvent.change(subjectInput, { target: { value: validFormData.subject } });
      fireEvent.change(messageInput, { target: { value: validFormData.message } });

      const submitButton = screen.getByRole('button', { name: /send message/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/message sent/i)).toBeInTheDocument();
      });

      // Click "send another message"
      const sendAnotherButton = screen.getByText(/send another message/i);
      fireEvent.click(sendAnotherButton);

      // Form should be visible again
      await waitFor(() => {
        expect(screen.getByLabelText(/your name/i)).toBeInTheDocument();
      });
    });
  });

  describe('Footer', () => {
    it('renders footer with navigation links', () => {
      renderWithRouter(<ContactPage />);

      const footerLinks = screen.getAllByRole('link');
      const linkTexts = footerLinks.map(link => link.textContent);

      expect(linkTexts).toContain('Demo');
      expect(linkTexts).toContain('Pricing');
      expect(linkTexts).toContain('Terms');
      expect(linkTexts).toContain('Privacy');
      expect(linkTexts).toContain('Contact');
    });
  });

  describe('Accessibility', () => {
    it('has proper heading hierarchy', () => {
      renderWithRouter(<ContactPage />);

      const h1 = screen.getByRole('heading', { level: 1 });
      expect(h1).toHaveTextContent('Contact Us');

      const h2s = screen.getAllByRole('heading', { level: 2 });
      expect(h2s.length).toBeGreaterThan(0);
    });

    it('has labels for all form inputs', () => {
      renderWithRouter(<ContactPage />);

      expect(screen.getByLabelText(/your name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/subject/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/message/i)).toBeInTheDocument();
    });

    it('indicates required fields', () => {
      renderWithRouter(<ContactPage />);

      const requiredIndicators = screen.getAllByText('*');
      expect(requiredIndicators.length).toBeGreaterThan(0);
    });
  });
});
