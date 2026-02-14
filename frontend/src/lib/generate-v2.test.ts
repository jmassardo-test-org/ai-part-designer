/**
 * Tests for CAD v2 generation API functions.
 */

import { describe, it, expect } from 'vitest';
import {
  createEnclosureSpec,
  addComponent,
  addVentilation,
  addLid,
  getDownloadUrl,
} from './generate-v2';

// Note: API functions that use fetch are tested via integration tests
// since mocking fetch conflicts with MSW interceptors.
// Here we test the schema helper functions which don't require network calls.

describe('getDownloadUrl', () => {
  it('should return correct URL', () => {
    const url = getDownloadUrl('job-123', 'body.step');
    expect(url).toContain('/api/v2/downloads/job-123/body.step');
  });
});

describe('Schema Helpers', () => {
  describe('createEnclosureSpec', () => {
    it('should create minimal spec with defaults', () => {
      const spec = createEnclosureSpec(100, 80, 40);

      expect(spec.exterior.width.value).toBe(100);
      expect(spec.exterior.depth.value).toBe(80);
      expect(spec.exterior.height.value).toBe(40);
      expect(spec.walls?.thickness?.value).toBe(2);
    });

    it('should merge options', () => {
      const spec = createEnclosureSpec(100, 80, 40, {
        name: 'My Box',
        corner_radius: { value: 3 },
      });

      expect(spec.name).toBe('My Box');
      expect(spec.corner_radius?.value).toBe(3);
    });
  });

  describe('addComponent', () => {
    it('should add component to spec', () => {
      const base = createEnclosureSpec(100, 80, 40);
      const spec = addComponent(base, 'raspberry-pi-4b', { x: 10, y: 10, z: 0 });

      expect(spec.components).toHaveLength(1);
      expect(spec.components![0].component.component_id).toBe('raspberry-pi-4b');
      expect(spec.components![0].position).toEqual({ x: 10, y: 10, z: 0 });
    });

    it('should add multiple components', () => {
      let spec = createEnclosureSpec(150, 100, 50);
      spec = addComponent(spec, 'raspberry-pi-4b', { x: 10, y: 10, z: 0 });
      spec = addComponent(spec, 'lcd-16x2', { x: 10, y: 60, z: 0 });

      expect(spec.components).toHaveLength(2);
    });
  });

  describe('addVentilation', () => {
    it('should add slot ventilation by default', () => {
      const base = createEnclosureSpec(100, 80, 40);
      const spec = addVentilation(base);

      expect(spec.ventilation?.enabled).toBe(true);
      expect(spec.ventilation?.pattern).toBe('slots');
      expect(spec.ventilation?.sides).toContain('left');
      expect(spec.ventilation?.sides).toContain('right');
    });

    it('should add honeycomb ventilation', () => {
      const base = createEnclosureSpec(100, 80, 40);
      const spec = addVentilation(base, {
        pattern: 'honeycomb',
        sides: ['front', 'back'],
      });

      expect(spec.ventilation?.pattern).toBe('honeycomb');
      expect(spec.ventilation?.sides).toContain('front');
    });
  });

  describe('addLid', () => {
    it('should add snap-fit lid by default', () => {
      const base = createEnclosureSpec(100, 80, 40);
      const spec = addLid(base);

      expect(spec.lid?.type).toBe('snap_fit');
      expect(spec.lid?.separate_part).toBe(true);
      expect(spec.lid?.snap_fit).toBeDefined();
    });

    it('should add screw-on lid', () => {
      const base = createEnclosureSpec(100, 80, 40);
      const spec = addLid(base, 'screw_on');

      expect(spec.lid?.type).toBe('screw_on');
      expect(spec.lid?.screws).toBeDefined();
      expect(spec.lid?.screws?.hole_diameter?.value).toBe(3);
    });
  });
});
