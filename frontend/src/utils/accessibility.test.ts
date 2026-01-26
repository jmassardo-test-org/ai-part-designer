import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  hexToRgb,
  getLuminance,
  getContrastRatio,
  meetsContrastRequirements,
  getContrastLevel,
  accessibleColors,
  focusRingStyles,
  generateId,
  announceToScreenReader,
  trapFocus,
  prefersReducedMotion,
  getAnimationDuration,
} from './accessibility';

describe('accessibility utilities', () => {
  describe('hexToRgb', () => {
    it('converts hex to RGB', () => {
      expect(hexToRgb('#FFFFFF')).toEqual({ r: 255, g: 255, b: 255 });
      expect(hexToRgb('#000000')).toEqual({ r: 0, g: 0, b: 0 });
      expect(hexToRgb('#FF0000')).toEqual({ r: 255, g: 0, b: 0 });
      expect(hexToRgb('#00FF00')).toEqual({ r: 0, g: 255, b: 0 });
      expect(hexToRgb('#0000FF')).toEqual({ r: 0, g: 0, b: 255 });
    });

    it('handles hex without # prefix', () => {
      expect(hexToRgb('FFFFFF')).toEqual({ r: 255, g: 255, b: 255 });
    });

    it('handles lowercase hex', () => {
      expect(hexToRgb('#ffffff')).toEqual({ r: 255, g: 255, b: 255 });
    });

    it('returns null for invalid hex', () => {
      expect(hexToRgb('#GGG')).toBeNull();
      expect(hexToRgb('invalid')).toBeNull();
      expect(hexToRgb('')).toBeNull();
    });
  });

  describe('getLuminance', () => {
    it('calculates luminance for white', () => {
      const luminance = getLuminance(255, 255, 255);
      expect(luminance).toBeCloseTo(1, 2);
    });

    it('calculates luminance for black', () => {
      const luminance = getLuminance(0, 0, 0);
      expect(luminance).toBeCloseTo(0, 2);
    });

    it('calculates luminance for gray', () => {
      const luminance = getLuminance(128, 128, 128);
      expect(luminance).toBeGreaterThan(0);
      expect(luminance).toBeLessThan(1);
    });

    it('applies correct coefficients (green has highest weight)', () => {
      const redLum = getLuminance(255, 0, 0);
      const greenLum = getLuminance(0, 255, 0);
      const blueLum = getLuminance(0, 0, 255);

      expect(greenLum).toBeGreaterThan(redLum);
      expect(redLum).toBeGreaterThan(blueLum);
    });
  });

  describe('getContrastRatio', () => {
    it('calculates maximum contrast (black/white)', () => {
      const ratio = getContrastRatio('#000000', '#FFFFFF');
      expect(ratio).toBeCloseTo(21, 0);
    });

    it('calculates minimum contrast (same color)', () => {
      const ratio = getContrastRatio('#808080', '#808080');
      expect(ratio).toBeCloseTo(1, 1);
    });

    it('handles order independence', () => {
      const ratio1 = getContrastRatio('#000000', '#FFFFFF');
      const ratio2 = getContrastRatio('#FFFFFF', '#000000');
      expect(ratio1).toBeCloseTo(ratio2, 2);
    });

    it('returns 0 for invalid colors', () => {
      expect(getContrastRatio('invalid', '#FFFFFF')).toBe(0);
      expect(getContrastRatio('#FFFFFF', 'invalid')).toBe(0);
    });
  });

  describe('meetsContrastRequirements', () => {
    describe('AA level', () => {
      it('requires 4.5:1 for normal text', () => {
        expect(meetsContrastRequirements(4.5, 'AA', false)).toBe(true);
        expect(meetsContrastRequirements(4.4, 'AA', false)).toBe(false);
      });

      it('requires 3:1 for large text', () => {
        expect(meetsContrastRequirements(3.0, 'AA', true)).toBe(true);
        expect(meetsContrastRequirements(2.9, 'AA', true)).toBe(false);
      });
    });

    describe('AAA level', () => {
      it('requires 7:1 for normal text', () => {
        expect(meetsContrastRequirements(7.0, 'AAA', false)).toBe(true);
        expect(meetsContrastRequirements(6.9, 'AAA', false)).toBe(false);
      });

      it('requires 4.5:1 for large text', () => {
        expect(meetsContrastRequirements(4.5, 'AAA', true)).toBe(true);
        expect(meetsContrastRequirements(4.4, 'AAA', true)).toBe(false);
      });
    });

    it('defaults to AA level and normal text', () => {
      expect(meetsContrastRequirements(4.5)).toBe(true);
      expect(meetsContrastRequirements(4.4)).toBe(false);
    });
  });

  describe('getContrastLevel', () => {
    it('returns AAA for ratio >= 7', () => {
      expect(getContrastLevel(7)).toBe('AAA (Excellent)');
      expect(getContrastLevel(21)).toBe('AAA (Excellent)');
    });

    it('returns AA for ratio >= 4.5', () => {
      expect(getContrastLevel(4.5)).toBe('AA (Good)');
      expect(getContrastLevel(6.9)).toBe('AA (Good)');
    });

    it('returns AA Large Text Only for ratio >= 3', () => {
      expect(getContrastLevel(3)).toBe('AA Large Text Only');
      expect(getContrastLevel(4.4)).toBe('AA Large Text Only');
    });

    it('returns Insufficient for ratio < 3', () => {
      expect(getContrastLevel(2.9)).toBe('Insufficient');
      expect(getContrastLevel(1)).toBe('Insufficient');
    });
  });

  describe('accessibleColors', () => {
    it('provides primary colors', () => {
      expect(accessibleColors.primary).toBeDefined();
      expect(accessibleColors.primary['500']).toBeDefined();
      expect(accessibleColors.primary['700']).toBeDefined();
    });

    it('provides status colors', () => {
      expect(accessibleColors.success).toBeDefined();
      expect(accessibleColors.warning).toBeDefined();
      expect(accessibleColors.error).toBeDefined();
      expect(accessibleColors.info).toBeDefined();
    });

    it('provides text colors', () => {
      expect(accessibleColors.text).toBeDefined();
      expect(accessibleColors.text.primary).toBeDefined();
      expect(accessibleColors.text.secondary).toBeDefined();
    });
  });

  describe('focusRingStyles', () => {
    it('provides focus ring style options', () => {
      expect(focusRingStyles.default).toContain('focus:ring');
      expect(focusRingStyles.inset).toContain('focus:ring-inset');
      expect(focusRingStyles.error).toContain('focus:ring-red');
    });
  });

  describe('generateId', () => {
    it('generates unique IDs with prefix', () => {
      const id1 = generateId('input');
      const id2 = generateId('input');

      expect(id1).toMatch(/^input-[a-z0-9]+$/);
      expect(id2).toMatch(/^input-[a-z0-9]+$/);
      expect(id1).not.toBe(id2);
    });

    it('uses provided prefix', () => {
      expect(generateId('button')).toMatch(/^button-/);
      expect(generateId('field')).toMatch(/^field-/);
    });
  });

  describe('announceToScreenReader', () => {
    let appendChildSpy: ReturnType<typeof vi.spyOn>;
    let removeChildSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      vi.useFakeTimers();
      appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => document.createElement('div'));
      removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation(() => document.createElement('div'));
    });

    afterEach(() => {
      vi.useRealTimers();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    });

    it('creates announcement element with polite priority by default', () => {
      announceToScreenReader('Test message');

      expect(appendChildSpy).toHaveBeenCalled();
      const element = appendChildSpy.mock.calls[0][0] as HTMLElement;
      expect(element.getAttribute('aria-live')).toBe('polite');
      expect(element.textContent).toBe('Test message');
    });

    it('supports assertive priority', () => {
      announceToScreenReader('Urgent message', 'assertive');

      const element = appendChildSpy.mock.calls[0][0] as HTMLElement;
      expect(element.getAttribute('aria-live')).toBe('assertive');
    });

    it('removes element after delay', () => {
      announceToScreenReader('Test');

      expect(removeChildSpy).not.toHaveBeenCalled();

      vi.advanceTimersByTime(1000);

      expect(removeChildSpy).toHaveBeenCalled();
    });
  });

  describe('trapFocus', () => {
    it('returns cleanup function', () => {
      const container = document.createElement('div');
      container.innerHTML = `
        <button id="first">First</button>
        <input id="input" />
        <button id="last">Last</button>
      `;

      const cleanup = trapFocus(container);
      expect(typeof cleanup).toBe('function');

      // Should not throw
      cleanup();
    });

    it('focuses first element on trap', () => {
      const container = document.createElement('div');
      const button = document.createElement('button');
      button.focus = vi.fn();
      container.appendChild(button);

      trapFocus(container);

      expect(button.focus).toHaveBeenCalled();
    });
  });

  describe('prefersReducedMotion', () => {
    it('returns boolean based on media query', () => {
      const result = prefersReducedMotion();
      expect(typeof result).toBe('boolean');
    });
  });

  describe('getAnimationDuration', () => {
    beforeEach(() => {
      vi.stubGlobal('matchMedia', vi.fn());
    });

    afterEach(() => {
      vi.unstubAllGlobals();
    });

    it('returns 0 when reduced motion is preferred', () => {
      (window.matchMedia as ReturnType<typeof vi.fn>).mockReturnValue({ matches: true });

      const duration = getAnimationDuration(300);
      expect(duration).toBe(0);
    });

    it('returns normal duration when motion is allowed', () => {
      (window.matchMedia as ReturnType<typeof vi.fn>).mockReturnValue({ matches: false });

      const duration = getAnimationDuration(300);
      expect(duration).toBe(300);
    });
  });
});
