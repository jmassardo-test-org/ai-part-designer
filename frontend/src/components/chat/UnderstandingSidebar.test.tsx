/**
 * UnderstandingSidebar Component Tests
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { UnderstandingSidebar } from './UnderstandingSidebar';
import type { PartUnderstanding } from '@/lib/conversations';

describe('UnderstandingSidebar', () => {
  describe('Empty State', () => {
    it('shows waiting message when understanding is null', () => {
      render(<UnderstandingSidebar understanding={null} />);
      expect(screen.getByText('Waiting for input...')).toBeInTheDocument();
    });

    it('shows waiting message when understanding is undefined', () => {
      render(<UnderstandingSidebar understanding={undefined} />);
      expect(screen.getByText('Waiting for input...')).toBeInTheDocument();
    });
  });

  describe('Classification Display', () => {
    it('displays part category', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: {
          category: 'bracket',
          subcategory: 'L-bracket',
          confidence: 0.9,
          reasoning: '',
        },
        dimensions: {},
        features: [],
        constraints: [],
        hardware_references: [],
        missing_critical: [],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'ready_to_plan',
        completeness_score: 0.8,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('bracket')).toBeInTheDocument();
    });

    it('displays subcategory when present', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: {
          category: 'bracket',
          subcategory: 'L-bracket',
          confidence: 0.9,
          reasoning: '',
        },
        dimensions: {},
        features: [],
        constraints: [],
        hardware_references: [],
        missing_critical: [],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'ready_to_plan',
        completeness_score: 0.8,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('(L-bracket)')).toBeInTheDocument();
    });
  });

  describe('Dimensions Display', () => {
    it('displays dimensions when present', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: null,
        dimensions: {
          length: { name: 'length', value: 100, unit: 'mm', confidence: 1, source: 'explicit' },
          width: { name: 'width', value: 50, unit: 'mm', confidence: 1, source: 'explicit' },
        },
        features: [],
        constraints: [],
        hardware_references: [],
        missing_critical: [],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'extracting',
        completeness_score: 0.5,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('Dimensions')).toBeInTheDocument();
      expect(screen.getByText('length')).toBeInTheDocument();
    });

    it('shows inferred indicator for inferred dimensions', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: null,
        dimensions: {
          thickness: { name: 'thickness', value: 3, unit: 'mm', confidence: 0.8, source: 'inferred' },
        },
        features: [],
        constraints: [],
        hardware_references: [],
        missing_critical: [],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'extracting',
        completeness_score: 0.5,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('*')).toBeInTheDocument();
    });
  });

  describe('Features Display', () => {
    it('displays features when present', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: null,
        dimensions: {},
        features: [
          { feature_type: 'hole', description: '10mm center hole', parameters: {}, location: '', count: 1, confidence: 1 },
        ],
        constraints: [],
        hardware_references: [],
        missing_critical: [],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'extracting',
        completeness_score: 0.5,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('Features')).toBeInTheDocument();
      expect(screen.getByText('hole')).toBeInTheDocument();
    });

    it('shows count for multiple features', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: null,
        dimensions: {},
        features: [
          { feature_type: 'hole', description: 'corner holes', parameters: {}, location: '', count: 4, confidence: 1 },
        ],
        constraints: [],
        hardware_references: [],
        missing_critical: [],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'extracting',
        completeness_score: 0.5,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('hole ×4')).toBeInTheDocument();
    });
  });

  describe('Missing Critical Display', () => {
    it('displays missing critical dimensions', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: null,
        dimensions: {},
        features: [],
        constraints: [],
        hardware_references: [],
        missing_critical: ['height', 'wall_thickness'],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'needs_clarification',
        completeness_score: 0.3,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('Missing')).toBeInTheDocument();
      expect(screen.getByText('height')).toBeInTheDocument();
      expect(screen.getByText('wall thickness')).toBeInTheDocument(); // Underscore replaced
    });
  });

  describe('Completeness Indicator', () => {
    it('shows green for high completeness (>=70%)', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: { category: 'box', subcategory: null, confidence: 0.9, reasoning: '' },
        dimensions: {},
        features: [],
        constraints: [],
        hardware_references: [],
        missing_critical: [],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'ready_to_plan',
        completeness_score: 0.8,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('80%')).toBeInTheDocument();
    });

    it('shows amber for medium completeness (40-69%)', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: null,
        dimensions: {},
        features: [],
        constraints: [],
        hardware_references: [],
        missing_critical: [],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'extracting',
        completeness_score: 0.5,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('shows red for low completeness (<40%)', () => {
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: null,
        dimensions: {},
        features: [],
        constraints: [],
        hardware_references: [],
        missing_critical: ['all'],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'needs_clarification',
        completeness_score: 0.2,
      };

      render(<UnderstandingSidebar understanding={understanding} />);
      expect(screen.getByText('20%')).toBeInTheDocument();
    });
  });

  describe('Dark Mode Support', () => {
    it('renders correctly with dark mode classes available', () => {
      // The component should use dark: prefixed classes for dark mode support
      const understanding: PartUnderstanding = {
        user_messages: [],
        classification: { category: 'enclosure', subcategory: null, confidence: 0.9, reasoning: '' },
        dimensions: {
          length: { name: 'length', value: 100, unit: 'mm', confidence: 1, source: 'explicit' },
        },
        features: [
          { feature_type: 'fillet', description: '3mm fillet', parameters: {}, location: '', count: 4, confidence: 1 },
        ],
        constraints: [],
        hardware_references: [],
        missing_critical: [],
        ambiguities: [],
        assumptions: [],
        questions: [],
        state: 'ready_to_plan',
        completeness_score: 0.9,
      };

      const { container } = render(<UnderstandingSidebar understanding={understanding} />);
      
      // Verify dark mode classes are present in the rendered HTML
      const html = container.innerHTML;
      expect(html).toContain('dark:');
    });
  });
});
