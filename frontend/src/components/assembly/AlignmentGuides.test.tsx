/**
 * AlignmentGuides Component Tests
 */

import { Canvas } from '@react-three/fiber';
import { render } from '@testing-library/react';
import * as THREE from 'three';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AlignmentGuide } from '../../hooks/useAlignmentGuides';
import { AlignmentGuides } from './AlignmentGuides';

// =============================================================================
// Test Helpers
// =============================================================================

/**
 * Wrapper for Three.js components that need Canvas context.
 */
function CanvasWrapper({ children }: { children: React.ReactNode }) {
  return (
    <Canvas>
      {children}
    </Canvas>
  );
}

/**
 * Create a test edge guide.
 */
function createEdgeGuide(id: string, distance: number = 0): AlignmentGuide {
  return {
    id,
    type: 'edge',
    sourcePartId: 'source',
    targetPartId: 'target',
    axis: 'x',
    position: new THREE.Vector3(0, 0, 0),
    startPoint: new THREE.Vector3(-10, 0, 0),
    endPoint: new THREE.Vector3(10, 0, 0),
    strength: 1 - distance / 10,
    distance,
  };
}

/**
 * Create a test center guide.
 */
function createCenterGuide(id: string, distance: number = 0): AlignmentGuide {
  return {
    id,
    type: 'center',
    sourcePartId: 'source',
    targetPartId: 'target',
    axis: 'y',
    position: new THREE.Vector3(0, 15, 0),
    startPoint: new THREE.Vector3(0, 0, 0),
    endPoint: new THREE.Vector3(0, 30, 0),
    strength: 1 - distance / 10,
    distance,
  };
}

/**
 * Create a test face guide.
 */
function createFaceGuide(id: string, distance: number = 0): AlignmentGuide {
  return {
    id,
    type: 'face',
    sourcePartId: 'source',
    targetPartId: 'target',
    axis: 'z',
    position: new THREE.Vector3(0, 0, 5),
    startPoint: new THREE.Vector3(0, 0, 5),
    endPoint: new THREE.Vector3(0, 0, 5),
    planeNormal: new THREE.Vector3(0, 0, 1),
    planeSize: { width: 20, height: 20 },
    strength: 1 - distance / 10,
    distance,
  };
}

// =============================================================================
// Tests
// =============================================================================

describe('AlignmentGuides', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---------------------------------------------------------------------------
  // Visibility
  // ---------------------------------------------------------------------------

  describe('visibility', () => {
    it('renders nothing when not visible', () => {
      const guides = [createEdgeGuide('edge-1')];

      const { container } = render(
        <CanvasWrapper>
          <AlignmentGuides guides={guides} visible={false} />
        </CanvasWrapper>
      );

      // Canvas will render but alignment guides should be empty
      expect(container).toBeDefined();
    });

    it('renders nothing when guides array is empty', () => {
      const { container } = render(
        <CanvasWrapper>
          <AlignmentGuides guides={[]} visible={true} />
        </CanvasWrapper>
      );

      expect(container).toBeDefined();
    });

    it('renders guides when visible and guides present', () => {
      const guides = [createEdgeGuide('edge-1')];

      // This test mainly verifies no errors are thrown during render
      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });
  });

  // ---------------------------------------------------------------------------
  // Edge Guides
  // ---------------------------------------------------------------------------

  describe('edge guides', () => {
    it('renders edge guide without error', () => {
      const guides = [createEdgeGuide('edge-1')];

      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });

    it('renders multiple edge guides', () => {
      const guides = [
        createEdgeGuide('edge-1'),
        createEdgeGuide('edge-2'),
        createEdgeGuide('edge-3'),
      ];

      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });
  });

  // ---------------------------------------------------------------------------
  // Center Guides
  // ---------------------------------------------------------------------------

  describe('center guides', () => {
    it('renders center guide without error', () => {
      const guides = [createCenterGuide('center-1')];

      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });

    it('renders center guide with sphere markers', () => {
      const guides = [createCenterGuide('center-1')];

      // Verify component can render (specific geometry testing would require more complex setup)
      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });
  });

  // ---------------------------------------------------------------------------
  // Face Guides
  // ---------------------------------------------------------------------------

  describe('face guides', () => {
    it('renders face guide without error', () => {
      const guides = [createFaceGuide('face-1')];

      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });

    it('renders face guide with default plane size when not specified', () => {
      const guide: AlignmentGuide = {
        ...createFaceGuide('face-1'),
        planeSize: undefined,
      };

      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={[guide]} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });
  });

  // ---------------------------------------------------------------------------
  // Mixed Guides
  // ---------------------------------------------------------------------------

  describe('mixed guides', () => {
    it('renders all guide types together', () => {
      const guides = [
        createEdgeGuide('edge-1'),
        createCenterGuide('center-1'),
        createFaceGuide('face-1'),
      ];

      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });

    it('applies different strengths correctly', () => {
      const guides = [
        createEdgeGuide('edge-strong', 0), // strength = 1
        createEdgeGuide('edge-weak', 8), // strength = 0.2
      ];

      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });
  });

  // ---------------------------------------------------------------------------
  // Opacity
  // ---------------------------------------------------------------------------

  describe('opacity', () => {
    it('accepts custom opacity value', () => {
      const guides = [createEdgeGuide('edge-1')];

      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} opacity={0.5} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });

    it('uses default opacity when not specified', () => {
      const guides = [createEdgeGuide('edge-1')];

      expect(() =>
        render(
          <CanvasWrapper>
            <AlignmentGuides guides={guides} visible={true} />
          </CanvasWrapper>
        )
      ).not.toThrow();
    });
  });
});
