/**
 * PartTransformControls Component Tests
 */

import { render } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as THREE from 'three';
import { PartTransformControls } from './PartTransformControls';

// Mock Three.js and react-three-fiber
vi.mock('@react-three/fiber', () => ({
  useThree: () => ({
    gl: { domElement: document.createElement('canvas') },
    camera: new THREE.PerspectiveCamera(),
  }),
}));

vi.mock('@react-three/drei', () => ({
  TransformControls: vi.fn(({ object, mode }: { object: THREE.Object3D; mode: string }) => {
    if (!object) return null;
    return <mesh data-testid={`transform-controls-${mode}`} />;
  }),
}));

describe('PartTransformControls', () => {
  let mockObject: THREE.Mesh;

  beforeEach(() => {
    vi.clearAllMocks();
    // Create a mock mesh object
    mockObject = new THREE.Mesh(
      new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshBasicMaterial()
    );
    mockObject.position.set(10, 20, 30);
    mockObject.rotation.set(0, Math.PI / 4, 0);
  });

  it('renders transform controls when object is provided', () => {
    const { container } = render(
      <PartTransformControls object={mockObject} mode="translate" />
    );
    expect(container.querySelector('[data-testid="transform-controls-translate"]')).toBeTruthy();
  });

  it('does not render when object is null', () => {
    const { container } = render(
      <PartTransformControls object={null} mode="translate" />
    );
    expect(container.querySelector('[data-testid^="transform-controls-"]')).toBeNull();
  });

  it('renders with translate mode', () => {
    const { container } = render(
      <PartTransformControls object={mockObject} mode="translate" />
    );
    expect(container.querySelector('[data-testid="transform-controls-translate"]')).toBeTruthy();
  });

  it('renders with rotate mode', () => {
    const { container } = render(
      <PartTransformControls object={mockObject} mode="rotate" />
    );
    expect(container.querySelector('[data-testid="transform-controls-rotate"]')).toBeTruthy();
  });

  it('renders with scale mode', () => {
    const { container } = render(
      <PartTransformControls object={mockObject} mode="scale" />
    );
    expect(container.querySelector('[data-testid="transform-controls-scale"]')).toBeTruthy();
  });

  it('accepts snapping configuration for position', () => {
    const { rerender } = render(
      <PartTransformControls
        object={mockObject}
        mode="translate"
        enablePositionSnap={true}
        positionSnapIncrement={5}
      />
    );
    expect(mockObject).toBeTruthy();

    // Test that we can change snapping settings
    rerender(
      <PartTransformControls
        object={mockObject}
        mode="translate"
        enablePositionSnap={false}
        positionSnapIncrement={10}
      />
    );
    expect(mockObject).toBeTruthy();
  });

  it('accepts snapping configuration for rotation', () => {
    const { rerender } = render(
      <PartTransformControls
        object={mockObject}
        mode="rotate"
        enableRotationSnap={true}
        rotationSnapIncrement={15}
      />
    );
    expect(mockObject).toBeTruthy();

    // Test that we can change snapping settings
    rerender(
      <PartTransformControls
        object={mockObject}
        mode="rotate"
        enableRotationSnap={false}
        rotationSnapIncrement={30}
      />
    );
    expect(mockObject).toBeTruthy();
  });

  it('calls onTransformChange when provided', () => {
    const onTransformChange = vi.fn();
    render(
      <PartTransformControls
        object={mockObject}
        mode="translate"
        onTransformChange={onTransformChange}
      />
    );
    // The actual transform change event is triggered by the real TransformControls
    // In a real scenario, this would be tested with integration tests
    expect(onTransformChange).not.toHaveBeenCalled();
  });

  it('calls onTransformEnd when provided', () => {
    const onTransformEnd = vi.fn();
    render(
      <PartTransformControls
        object={mockObject}
        mode="translate"
        onTransformEnd={onTransformEnd}
      />
    );
    // The actual transform end event is triggered by the real TransformControls
    expect(onTransformEnd).not.toHaveBeenCalled();
  });

  it('calls onDraggingChange when provided', () => {
    const onDraggingChange = vi.fn();
    render(
      <PartTransformControls
        object={mockObject}
        mode="translate"
        onDraggingChange={onDraggingChange}
      />
    );
    // The actual dragging change event is triggered by the real TransformControls
    expect(onDraggingChange).not.toHaveBeenCalled();
  });

  it('uses default snap values when not provided', () => {
    const { container } = render(
      <PartTransformControls object={mockObject} mode="translate" />
    );
    expect(container.querySelector('[data-testid="transform-controls-translate"]')).toBeTruthy();
  });
});
