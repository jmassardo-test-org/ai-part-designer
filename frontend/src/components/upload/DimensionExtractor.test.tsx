/**
 * DimensionExtractor Component Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DimensionExtractor } from './DimensionExtractor';

// Mock extraction API
const mockExtractFromFile = vi.fn();
const mockExtractFromUrl = vi.fn();
const mockGetStatus = vi.fn();

vi.mock('@/lib/api/extraction', () => ({
  extractionApi: {
    extractFromFile: (...args: unknown[]) => mockExtractFromFile(...args),
    extractFromUrl: (...args: unknown[]) => mockExtractFromUrl(...args),
    getStatus: () => mockGetStatus(),
  },
}));

const mockExtractionResult = {
  overall_dimensions: {
    length: 85,
    width: 56,
    height: 17,
    unit: 'mm',
  },
  mounting_holes: [
    { x: 3.5, y: 3.5, diameter: 2.7, type: 'M2.5' },
    { x: 61.5, y: 3.5, diameter: 2.7, type: 'M2.5' },
    { x: 3.5, y: 52.5, diameter: 2.7, type: 'M2.5' },
    { x: 61.5, y: 52.5, diameter: 2.7, type: 'M2.5' },
  ],
  cutouts: [
    { type: 'USB-C', x: 8, y: 0, width: 9, height: 3 },
    { type: 'HDMI', x: 26, y: 0, width: 15, height: 5 },
  ],
  connectors: [
    { name: 'USB-C Power', type: 'USB-C' },
    { name: 'HDMI 0', type: 'HDMI' },
    { name: 'HDMI 1', type: 'HDMI' },
  ],
  tolerances: null,
  notes: ['Dimensions are in millimeters'],
  confidence: 0.92,
  pages_analyzed: 1,
};

describe('DimensionExtractor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExtractFromFile.mockResolvedValue(mockExtractionResult);
    mockExtractFromUrl.mockResolvedValue(mockExtractionResult);
  });

  describe('Rendering', () => {
    it('renders the component title', () => {
      render(<DimensionExtractor />);
      expect(screen.getByText('Dimension Extraction')).toBeInTheDocument();
    });

    it('renders upload file mode by default', () => {
      render(<DimensionExtractor />);
      expect(screen.getByText('Upload File')).toBeInTheDocument();
      expect(screen.getByText('From URL')).toBeInTheDocument();
    });

    it('shows file upload zone', () => {
      render(<DimensionExtractor />);
      expect(screen.getByText(/Drag and drop a file/)).toBeInTheDocument();
    });

    it('shows extract button disabled by default', () => {
      render(<DimensionExtractor />);
      const button = screen.getByText('Extract Dimensions').closest('button');
      expect(button).toBeDisabled();
    });
  });

  describe('Mode Toggle', () => {
    it('switches to URL mode when clicked', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      await user.click(screen.getByText('From URL'));
      
      expect(screen.getByPlaceholderText(/https:\/\//)).toBeInTheDocument();
    });

    it('switches back to file mode', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      await user.click(screen.getByText('From URL'));
      await user.click(screen.getByText('Upload File'));
      
      expect(screen.getByText(/Drag and drop a file/)).toBeInTheDocument();
    });
  });

  describe('File Upload', () => {
    it('accepts PDF files', async () => {
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      
      fireEvent.change(input, { target: { files: [file] } });
      
      expect(screen.getByText('datasheet.pdf')).toBeInTheDocument();
    });

    it('shows file size', async () => {
      render(<DimensionExtractor />);
      
      const file = new File(['test content'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      
      fireEvent.change(input, { target: { files: [file] } });
      
      expect(screen.getByText(/MB/)).toBeInTheDocument();
    });

    it('enables extract button when file is selected', async () => {
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      
      fireEvent.change(input, { target: { files: [file] } });
      
      const button = screen.getByText('Extract Dimensions').closest('button');
      expect(button).not.toBeDisabled();
    });

    it('allows removing selected file', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      
      fireEvent.change(input, { target: { files: [file] } });
      
      // Click remove button
      const removeButtons = screen.getAllByRole('button');
      const removeButton = removeButtons.find(b => b.querySelector('svg.lucide-x'));
      if (removeButton) {
        await user.click(removeButton);
      }
      
      expect(screen.queryByText('datasheet.pdf')).not.toBeInTheDocument();
    });
  });

  describe('URL Input', () => {
    it('enables extract button when URL is entered', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      await user.click(screen.getByText('From URL'));
      await user.type(
        screen.getByPlaceholderText(/https:\/\//),
        'https://example.com/datasheet.pdf'
      );
      
      const button = screen.getByText('Extract Dimensions').closest('button');
      expect(button).not.toBeDisabled();
    });
  });

  describe('Context Input', () => {
    it('renders context textarea', () => {
      render(<DimensionExtractor />);
      expect(screen.getByPlaceholderText(/Raspberry Pi/)).toBeInTheDocument();
    });

    it('accepts initial context prop', () => {
      render(<DimensionExtractor initialContext="Arduino Uno" />);
      expect(screen.getByDisplayValue('Arduino Uno')).toBeInTheDocument();
    });
  });

  describe('Extraction', () => {
    it('calls extractFromFile when button clicked', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      expect(mockExtractFromFile).toHaveBeenCalledWith(file, expect.any(Object));
    });

    it('calls extractFromUrl for URL mode', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      await user.click(screen.getByText('From URL'));
      await user.type(
        screen.getByPlaceholderText(/https:\/\//),
        'https://example.com/datasheet.pdf'
      );
      await user.click(screen.getByText('Extract Dimensions'));
      
      expect(mockExtractFromUrl).toHaveBeenCalledWith(
        'https://example.com/datasheet.pdf',
        ''
      );
    });

    it('shows loading state during extraction', async () => {
      mockExtractFromFile.mockImplementation(() => new Promise(() => {})); // Never resolves
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      expect(screen.getByText('Analyzing...')).toBeInTheDocument();
    });

    it('calls onExtractionComplete callback', async () => {
      const onComplete = vi.fn();
      const user = userEvent.setup();
      render(<DimensionExtractor onExtractionComplete={onComplete} />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(onComplete).toHaveBeenCalledWith(mockExtractionResult);
      });
    });
  });

  describe('Results Display', () => {
    it('shows extraction complete message', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText('Extraction Complete')).toBeInTheDocument();
      });
    });

    it('displays confidence badge', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText(/High.*92%/)).toBeInTheDocument();
      });
    });

    it('displays overall dimensions', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText('Overall Dimensions')).toBeInTheDocument();
        expect(screen.getByText('85 mm')).toBeInTheDocument();
        expect(screen.getByText('56 mm')).toBeInTheDocument();
        expect(screen.getByText('17 mm')).toBeInTheDocument();
      });
    });

    it('displays mounting holes section', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText(/Mounting Holes/)).toBeInTheDocument();
        expect(screen.getByText('(4)')).toBeInTheDocument();
      });
    });

    it('displays cutouts section', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText(/Cutouts/)).toBeInTheDocument();
        expect(screen.getByText('(2)')).toBeInTheDocument();
      });
    });

    it('displays connectors section', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText(/Connectors/)).toBeInTheDocument();
        expect(screen.getByText('(3)')).toBeInTheDocument();
      });
    });

    it('displays notes', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText('Dimensions are in millimeters')).toBeInTheDocument();
      });
    });
  });

  describe('Low Confidence Warning', () => {
    it('shows warning for low confidence', async () => {
      mockExtractFromFile.mockResolvedValue({
        ...mockExtractionResult,
        confidence: 0.35,
      });
      
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText(/Low confidence extraction/)).toBeInTheDocument();
      });
    });
  });

  describe('Apply Action', () => {
    it('shows Apply button when onApply provided', async () => {
      const onApply = vi.fn();
      const user = userEvent.setup();
      render(<DimensionExtractor onApply={onApply} />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText('Apply Dimensions')).toBeInTheDocument();
      });
    });

    it('calls onApply when clicked', async () => {
      const onApply = vi.fn();
      const user = userEvent.setup();
      render(<DimensionExtractor onApply={onApply} />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText('Apply Dimensions')).toBeInTheDocument();
      });
      
      await user.click(screen.getByText('Apply Dimensions'));
      
      expect(onApply).toHaveBeenCalled();
    });
  });

  describe('Reset', () => {
    it('shows Start Over button after extraction', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText('Start Over')).toBeInTheDocument();
      });
    });

    it('resets to initial state when Start Over clicked', async () => {
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText('Start Over')).toBeInTheDocument();
      });
      
      await user.click(screen.getByText('Start Over'));
      
      expect(screen.getByText(/Drag and drop a file/)).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('shows error message when extraction fails', async () => {
      mockExtractFromFile.mockRejectedValue(new Error('Network error'));
      
      const user = userEvent.setup();
      render(<DimensionExtractor />);
      
      const file = new File(['test'], 'datasheet.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, { target: { files: [file] } });
      
      await user.click(screen.getByText('Extract Dimensions'));
      
      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });
    });
  });
});
