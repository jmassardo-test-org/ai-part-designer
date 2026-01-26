import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import {
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
  ToastAction,
} from './toast';

const renderWithProvider = (ui: React.ReactNode) => {
  return render(
    <ToastProvider>
      {ui}
      <ToastViewport />
    </ToastProvider>
  );
};

describe('Toast', () => {
  it('renders without crashing', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle>Toast Title</ToastTitle>
      </Toast>
    );
    expect(screen.getByText('Toast Title')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    renderWithProvider(
      <Toast open className="custom-toast" data-testid="toast">
        <ToastTitle>Title</ToastTitle>
      </Toast>
    );
    expect(screen.getByTestId('toast')).toHaveClass('custom-toast');
  });

  it('applies default variant styles', () => {
    renderWithProvider(
      <Toast open data-testid="toast">
        <ToastTitle>Title</ToastTitle>
      </Toast>
    );
    expect(screen.getByTestId('toast')).toHaveClass('bg-background');
  });

  it('applies destructive variant styles', () => {
    renderWithProvider(
      <Toast open variant="destructive" data-testid="toast">
        <ToastTitle>Error</ToastTitle>
      </Toast>
    );
    expect(screen.getByTestId('toast')).toHaveClass('destructive');
  });
});

describe('ToastTitle', () => {
  it('renders without crashing', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle>Toast Title</ToastTitle>
      </Toast>
    );
    expect(screen.getByText('Toast Title')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle className="custom-title">Title</ToastTitle>
      </Toast>
    );
    expect(screen.getByText('Title')).toHaveClass('custom-title');
  });

  it('applies default styles', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle>Title</ToastTitle>
      </Toast>
    );
    expect(screen.getByText('Title')).toHaveClass('font-semibold');
  });
});

describe('ToastDescription', () => {
  it('renders without crashing', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle>Title</ToastTitle>
        <ToastDescription>Description text</ToastDescription>
      </Toast>
    );
    expect(screen.getByText('Description text')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle>Title</ToastTitle>
        <ToastDescription className="custom-desc">Description</ToastDescription>
      </Toast>
    );
    expect(screen.getByText('Description')).toHaveClass('custom-desc');
  });
});

describe('ToastClose', () => {
  it('renders without crashing', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle>Title</ToastTitle>
        <ToastClose data-testid="close" />
      </Toast>
    );
    expect(screen.getByTestId('close')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle>Title</ToastTitle>
        <ToastClose className="custom-close" data-testid="close" />
      </Toast>
    );
    expect(screen.getByTestId('close')).toHaveClass('custom-close');
  });
});

describe('ToastAction', () => {
  it('renders without crashing', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle>Title</ToastTitle>
        <ToastAction altText="Undo action">Undo</ToastAction>
      </Toast>
    );
    expect(screen.getByText('Undo')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    renderWithProvider(
      <Toast open>
        <ToastTitle>Title</ToastTitle>
        <ToastAction altText="Action" className="custom-action">
          Action
        </ToastAction>
      </Toast>
    );
    expect(screen.getByText('Action')).toHaveClass('custom-action');
  });
});

describe('ToastViewport', () => {
  it('renders without crashing', () => {
    render(
      <ToastProvider>
        <ToastViewport data-testid="viewport" />
      </ToastProvider>
    );
    expect(screen.getByTestId('viewport')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <ToastProvider>
        <ToastViewport className="custom-viewport" data-testid="viewport" />
      </ToastProvider>
    );
    expect(screen.getByTestId('viewport')).toHaveClass('custom-viewport');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLOListElement>();
    render(
      <ToastProvider>
        <ToastViewport ref={ref} />
      </ToastProvider>
    );
    expect(ref.current).toBeInstanceOf(HTMLOListElement);
  });
});
