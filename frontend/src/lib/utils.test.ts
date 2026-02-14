import { describe, it, expect } from 'vitest';
import { cn } from './utils';

describe('utils', () => {
  describe('cn', () => {
    it('merges class names', () => {
      const result = cn('class1', 'class2');
      expect(result).toBe('class1 class2');
    });

    it('handles undefined and null values', () => {
      const result = cn('class1', undefined, null, 'class2');
      expect(result).toBe('class1 class2');
    });

    it('handles empty string', () => {
      const result = cn('class1', '', 'class2');
      expect(result).toBe('class1 class2');
    });

    it('handles boolean conditionals', () => {
      const isActive = true;
      const isDisabled = false;

      const result = cn('base', isActive && 'active', isDisabled && 'disabled');
      expect(result).toBe('base active');
    });

    it('handles object syntax from clsx', () => {
      const result = cn('base', {
        active: true,
        disabled: false,
        highlighted: true,
      });
      expect(result).toBe('base active highlighted');
    });

    it('handles array syntax', () => {
      const result = cn(['class1', 'class2'], 'class3');
      expect(result).toBe('class1 class2 class3');
    });

    it('merges tailwind classes correctly', () => {
      // twMerge should resolve conflicting classes
      const result = cn('px-2 py-1', 'px-4');
      expect(result).toBe('py-1 px-4');
    });

    it('handles conflicting text colors', () => {
      const result = cn('text-red-500', 'text-blue-500');
      expect(result).toBe('text-blue-500');
    });

    it('handles conflicting background colors', () => {
      const result = cn('bg-white', 'bg-gray-100');
      expect(result).toBe('bg-gray-100');
    });

    it('handles conflicting padding', () => {
      const result = cn('p-4', 'p-2');
      expect(result).toBe('p-2');
    });

    it('handles conflicting margin', () => {
      const result = cn('m-4', 'm-2');
      expect(result).toBe('m-2');
    });

    it('preserves non-conflicting classes', () => {
      const result = cn('flex', 'items-center', 'gap-2', 'p-4', 'bg-white');
      expect(result).toBe('flex items-center gap-2 p-4 bg-white');
    });

    it('handles responsive variants', () => {
      const result = cn('text-sm', 'md:text-lg', 'lg:text-xl');
      expect(result).toBe('text-sm md:text-lg lg:text-xl');
    });

    it('handles state variants', () => {
      const result = cn('bg-blue-500', 'hover:bg-blue-600', 'focus:bg-blue-700');
      expect(result).toBe('bg-blue-500 hover:bg-blue-600 focus:bg-blue-700');
    });

    it('handles complex combinations', () => {
      const trueCondition = true;
      const falseCondition = false;
      const result = cn(
        'base-class',
        trueCondition && 'conditional-true',
        falseCondition && 'conditional-false',
        { 'object-true': true, 'object-false': false },
        ['array-1', 'array-2'],
        undefined,
        null,
        ''
      );
      expect(result).toBe('base-class conditional-true object-true array-1 array-2');
    });

    it('returns empty string for no valid inputs', () => {
      const result = cn(undefined, null, false, '');
      expect(result).toBe('');
    });
  });
});
