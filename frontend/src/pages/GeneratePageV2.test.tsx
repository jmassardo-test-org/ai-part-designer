/**
 * Tests for GeneratePageV2 component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render, renderWithRouter } from '@/test/utils';
import { GeneratePageV2 } from './GeneratePageV2';

// Mock the hooks
vi.mock('@/hooks/useGenerateV2', () => ({
  useGenerateV2: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ job_id: 'test-job', success: true }),
    isPending: false,
    error: null,
    reset: vi.fn(),
  }),
  usePreviewSchema: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ job_id: 'test-job', success: true }),
    isPending: false,
    error: null,
    reset: vi.fn(),
  }),
  useCompileEnclosure: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ 
      job_id: 'test-job', 
      success: true, 
      parts: ['base', 'lid'],
      files: [],
      downloads: {},
      errors: [],
      warnings: [],
    }),
    isPending: false,
    error: null,
    reset: vi.fn(),
  }),
  useSaveDesignV2: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ id: 'saved-design-id' }),
    isPending: false,
    error: null,
    reset: vi.fn(),
  }),
}));

// Mock the lib functions
vi.mock('@/lib/generate-v2', () => ({
  createEnclosureSpec: vi.fn(() => ({
    exterior: { width: { value: 100 }, depth: { value: 80 }, height: { value: 50 } },
  })),
  addVentilation: vi.fn((spec) => spec),
  addLid: vi.fn((spec) => spec),
  getDownloadUrl: vi.fn((jobId, filename) => `/api/v2/downloads/${jobId}/${filename}`),
}));

// Mock the ModelViewer
vi.mock('@/components/viewer', () => ({
  ModelViewer: ({ stlUrl }: { stlUrl?: string }) => (
    <div data-testid="model-viewer" data-stl-url={stlUrl}>
      Model Viewer
    </div>
  ),
}));

describe('GeneratePageV2', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render the page header', () => {
    render(<GeneratePageV2 />);
    
    expect(screen.getByText('Generate Enclosure')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();
  });

  it('should render mode toggle buttons', () => {
    render(<GeneratePageV2 />);
    
    expect(screen.getByText('AI Description')).toBeInTheDocument();
    expect(screen.getByText('Manual Config')).toBeInTheDocument();
  });

  it('should show AI mode by default', () => {
    render(<GeneratePageV2 />);
    
    // Check for the label text and example prompts section
    expect(screen.getByText('Describe your enclosure')).toBeInTheDocument();
    expect(screen.getByText('Example Prompts')).toBeInTheDocument();
  });

  it('should switch to manual mode when clicked', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    await user.click(screen.getByText('Manual Config'));
    
    expect(screen.getByText('Dimensions')).toBeInTheDocument();
    expect(screen.getByText('Features')).toBeInTheDocument();
  });

  it('should render dimension presets in manual mode', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    await user.click(screen.getByText('Manual Config'));
    
    expect(screen.getByText('Small')).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText('Large')).toBeInTheDocument();
    expect(screen.getByText('Pi Case')).toBeInTheDocument();
  });

  it('should render example prompts in AI mode', () => {
    render(<GeneratePageV2 />);
    
    expect(
      screen.getByText(/Create an enclosure for a Raspberry Pi 4/i)
    ).toBeInTheDocument();
  });

  it('should fill description when example prompt is clicked', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    const prompt = screen.getByText(/Create an enclosure for a Raspberry Pi 4/i);
    await user.click(prompt);
    
    const textarea = screen.getByRole('textbox');
    // Value should contain the Raspberry Pi text
    expect((textarea as HTMLTextAreaElement).value).toContain('Raspberry Pi 4');
  });

  it('should disable generate button when description is empty', () => {
    render(<GeneratePageV2 />);
    
    const generateButton = screen.getByRole('button', { name: /generate/i });
    expect(generateButton).toBeDisabled();
  });

  it('should enable generate button when description has content', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Test enclosure');
    
    const generateButton = screen.getByRole('button', { name: /generate/i });
    expect(generateButton).not.toBeDisabled();
  });

  it('should render lid type options in manual mode', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    await user.click(screen.getByText('Manual Config'));
    
    expect(screen.getByText('snap fit')).toBeInTheDocument();
    expect(screen.getByText('screw on')).toBeInTheDocument();
    expect(screen.getByText('hinged')).toBeInTheDocument();
  });

  it('should render ventilation toggle in manual mode', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    await user.click(screen.getByText('Manual Config'));
    
    expect(screen.getByText('Add ventilation')).toBeInTheDocument();
  });

  it('should show ventilation patterns when ventilation is enabled', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    await user.click(screen.getByText('Manual Config'));
    
    expect(screen.getByText('slots')).toBeInTheDocument();
    expect(screen.getByText('honeycomb')).toBeInTheDocument();
    expect(screen.getByText('circular')).toBeInTheDocument();
  });

  it('should show placeholder in viewer area before generation', () => {
    render(<GeneratePageV2 />);
    
    expect(screen.getByText('Preview will appear here')).toBeInTheDocument();
  });

  it('should render the character counter', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    // Initially should show 0/2000
    expect(screen.getByText('0/2000')).toBeInTheDocument();
    
    // Type something
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Test');
    
    expect(screen.getByText('4/2000')).toBeInTheDocument();
  });

  it('should render ports and cutouts section in manual mode', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    await user.click(screen.getByText('Manual Config'));
    
    expect(screen.getByText('Ports & Cutouts')).toBeInTheDocument();
    expect(screen.getByText('USB-C')).toBeInTheDocument();
    expect(screen.getByText('HDMI')).toBeInTheDocument();
    expect(screen.getByText('Ethernet')).toBeInTheDocument();
  });

  it('should add and remove port features', async () => {
    const user = userEvent.setup();
    render(<GeneratePageV2 />);
    
    await user.click(screen.getByText('Manual Config'));
    
    // Initially no features
    expect(screen.getByText('0 added')).toBeInTheDocument();
    
    // Add a USB-C port
    await user.click(screen.getByRole('button', { name: /USB-C/i }));
    
    // Should show 1 added
    expect(screen.getByText('1 added')).toBeInTheDocument();
    
    // Should show the feature in the list with side selector
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  describe('Remix Mode', () => {
    const mockRemixState = {
      remixMode: true,
      enclosureSpec: {
        exterior: {
          width: { value: 150, unit: 'mm' },
          depth: { value: 100, unit: 'mm' },
          height: { value: 60, unit: 'mm' },
        },
        walls: { thickness: { value: 3, unit: 'mm' } },
        corner_radius: { value: 5, unit: 'mm' },
        lid: { type: 'screw_on' },
        ventilation: { enabled: true, pattern: 'honeycomb' },
      },
      remixedFrom: {
        id: 'starter-123',
        name: 'Pi Zero Case',
      },
      designId: 'remix-456',
      designName: 'My Remix of Pi Zero Case',
    };

    it('should show remix banner when in remix mode', async () => {
      renderWithRouter(
        <GeneratePageV2 />,
        { initialEntries: [{ pathname: '/generate', state: mockRemixState }] }
      );

      await waitFor(() => {
        expect(screen.getByText(/Remixing: Pi Zero Case/)).toBeInTheDocument();
      });
    });

    it('should pre-fill description with remix prompt', async () => {
      renderWithRouter(
        <GeneratePageV2 />,
        { initialEntries: [{ pathname: '/generate', state: mockRemixState }] }
      );

      await waitFor(() => {
        const textarea = screen.getByRole('textbox');
        expect((textarea as HTMLTextAreaElement).value).toContain('remix');
        expect((textarea as HTMLTextAreaElement).value).toContain('Pi Zero Case');
      });
    });

    it('should auto-compile the remixed enclosure spec', async () => {
      renderWithRouter(
        <GeneratePageV2 />,
        { initialEntries: [{ pathname: '/generate', state: mockRemixState }] }
      );

      // Wait for the remix banner to appear, indicating the remix was processed
      await waitFor(() => {
        expect(screen.getByText(/Remixing: Pi Zero Case/)).toBeInTheDocument();
      });
    });

    it('should show helpful guidance text in remix banner', async () => {
      renderWithRouter(
        <GeneratePageV2 />,
        { initialEntries: [{ pathname: '/generate', state: mockRemixState }] }
      );

      await waitFor(() => {
        expect(screen.getByText(/Use the AI chat to describe your changes/)).toBeInTheDocument();
      });
    });
  });});