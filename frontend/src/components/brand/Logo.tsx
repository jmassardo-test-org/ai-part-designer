/**
 * AssemblematicAI Logo Component
 * 
 * SVG logo with the isometric gear and blocks design.
 */

import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showText?: boolean;
  variant?: 'full' | 'icon';
}

const sizes = {
  sm: { icon: 24, text: 'text-lg' },
  md: { icon: 32, text: 'text-xl' },
  lg: { icon: 40, text: 'text-2xl' },
  xl: { icon: 48, text: 'text-3xl' },
};

export function Logo({ 
  className, 
  size = 'md', 
  showText = true,
  variant = 'full',
}: LogoProps) {
  const { icon: iconSize, text: textSize } = sizes[size];

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Icon */}
      <LogoIcon size={iconSize} />

      {/* Text */}
      {showText && variant === 'full' && (
        <span className={cn('font-bold', textSize)}>
          <span className="text-white">Assemblematic</span>
          <span className="text-brand-cyan">AI</span>
        </span>
      )}
    </div>
  );
}

interface LogoIconProps {
  size?: number;
  className?: string;
}

export function LogoIcon({ size = 32, className }: LogoIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Gear (back left) */}
      <g transform="translate(4, 8)">
        {/* Gear body */}
        <path
          d="M16 4L20 6V10L24 12V18L20 20V24L16 26L12 24V20L8 18V12L12 10V6L16 4Z"
          fill="#94a3b8"
          stroke="#64748b"
          strokeWidth="1"
        />
        {/* Gear teeth */}
        <path
          d="M14 2L18 2L18 5L14 5ZM14 25L18 25L18 28L14 28Z"
          fill="#94a3b8"
        />
        <path
          d="M6 8L9 6.5L10.5 9.5L7.5 11ZM22 19L25 17.5L26.5 20.5L23.5 22Z"
          fill="#94a3b8"
        />
        <path
          d="M6 22L9 23.5L10.5 20.5L7.5 19ZM22 11L25 12.5L26.5 9.5L23.5 8Z"
          fill="#94a3b8"
        />
        {/* Gear center hole */}
        <circle cx="16" cy="15" r="4" fill="#0d1526" />
      </g>

      {/* Blue blocks (isometric cube stack) */}
      {/* Bottom layer - darker blue */}
      <g transform="translate(24, 28)">
        {/* Front face */}
        <path
          d="M0 12L16 4L16 20L0 28Z"
          fill="#2563eb"
        />
        {/* Top face */}
        <path
          d="M0 12L16 4L32 12L16 20Z"
          fill="#3b82f6"
        />
        {/* Right face */}
        <path
          d="M16 20L32 12L32 28L16 36Z"
          fill="#1d4ed8"
        />
      </g>

      {/* Top block - cyan accent */}
      <g transform="translate(28, 16)">
        {/* Front face */}
        <path
          d="M0 8L10 3L10 13L0 18Z"
          fill="#0891b2"
        />
        {/* Top face */}
        <path
          d="M0 8L10 3L20 8L10 13Z"
          fill="#22d3ee"
        />
        {/* Right face */}
        <path
          d="M10 13L20 8L20 18L10 23Z"
          fill="#0e7490"
        />
      </g>

      {/* Connection pins (top right) */}
      <g fill="#64748b">
        <circle cx="48" cy="8" r="2" />
        <circle cx="54" cy="4" r="2" />
        <path d="M48 10L48 16" stroke="#64748b" strokeWidth="1.5" />
        <path d="M54 6L54 10" stroke="#64748b" strokeWidth="1.5" />
        <path d="M48 16L44 20" stroke="#64748b" strokeWidth="1.5" />
        <path d="M54 10L50 14" stroke="#64748b" strokeWidth="1.5" />
      </g>
    </svg>
  );
}

// Logo for dark backgrounds (default)
export function LogoDark(props: LogoProps) {
  return <Logo {...props} />;
}

// Logo for light backgrounds - now theme-aware
export function LogoLight({ className, ...props }: LogoProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <LogoIcon size={sizes[props.size || 'md'].icon} />
      {props.showText !== false && props.variant !== 'icon' && (
        <span className={cn('font-bold', sizes[props.size || 'md'].text)}>
          <span className="text-slate-900 dark:text-white">Assemblematic</span>
          <span className="text-brand-cyan">AI</span>
        </span>
      )}
    </div>
  );
}
