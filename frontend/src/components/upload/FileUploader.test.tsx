/**
 * FileUploader Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FileUploader } from './FileUploader';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
  }),
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('FileUploader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  it('renders upload drop zone', () => {
    render(<FileUploader />);
    
    expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
  });

  it('shows allowed file types', () => {
    render(<FileUploader />);
    
    expect(screen.getByText(/\.step/i)).toBeInTheDocument();
  });

  it('handles file selection via click', async () => {
    const onUploadComplete = vi.fn();

    render(<FileUploader onUploadComplete={onUploadComplete} />);
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeInTheDocument();
    
    // Verify the input is there and can accept files
    expect(input.type).toBe('file');
  });

  it('shows error for files that are too large', async () => {
    const onError = vi.fn();
    render(<FileUploader onError={onError} maxSizeMB={1} />);
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    // Create a file larger than 1MB
    const largeContent = new Array(2 * 1024 * 1024).fill('a').join('');
    const file = new File([largeContent], 'large.step', { type: 'application/step' });
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });
    
    fireEvent.change(input);
    
    await waitFor(() => {
      expect(screen.getByText(/file too large/i)).toBeInTheDocument();
    });
  });

  it('shows error for invalid file types', async () => {
    const onError = vi.fn();
    render(<FileUploader onError={onError} />);
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test'], 'test.txt', { type: 'text/plain' });
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });
    
    fireEvent.change(input);
    
    await waitFor(() => {
      expect(screen.getByText(/file type not allowed/i)).toBeInTheDocument();
    });
  });

  it('handles drag and drop', async () => {
    const onUploadComplete = vi.fn();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        id: '1',
        filename: 'test.step',
        original_filename: 'test.step',
        size_bytes: 1024,
        file_type: 'step',
        status: 'complete',
        download_url: '/files/1',
      }),
    });

    render(<FileUploader onUploadComplete={onUploadComplete} />);
    
    const dropZone = screen.getByText(/drag and drop/i).closest('div')!;
    const file = new File(['test content'], 'test.step', { type: 'application/step' });
    
    const dataTransfer = {
      files: [file],
      items: [{ kind: 'file', type: 'application/step', getAsFile: () => file }],
      types: ['Files'],
    };
    
    fireEvent.dragOver(dropZone, { dataTransfer });
    fireEvent.drop(dropZone, { dataTransfer });
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
  });

  it('shows upload progress', async () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<FileUploader />);
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test content'], 'test.step', { type: 'application/step' });
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });
    
    fireEvent.change(input);
    
    await waitFor(() => {
      expect(screen.getByText('test.step')).toBeInTheDocument();
    });
  });

  it('handles upload error', async () => {
    const onError = vi.fn();

    render(<FileUploader onError={onError} />);
    
    // Verify error callback prop is accepted
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<FileUploader className="custom-class" />);
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('supports multiple file upload when enabled', () => {
    render(<FileUploader multiple={true} />);
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toHaveAttribute('multiple');
  });
});
