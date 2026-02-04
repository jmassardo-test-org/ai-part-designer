/**
 * SaveButton component for saving/unsaving marketplace designs.
 * 
 * Shows a heart icon that toggles saved state when clicked.
 */

import { Heart, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import * as api from '@/lib/marketplace';

interface SaveButtonProps {
  designId: string;
  initialSaved?: boolean;
  variant?: 'icon' | 'button';
  size?: 'sm' | 'md' | 'lg';
  onSaveChange?: (designId: string, saved: boolean) => void;
}

export function SaveButton({
  designId,
  initialSaved = false,
  variant = 'button',
  size = 'md',
  onSaveChange,
}: SaveButtonProps) {
  const { token, user } = useAuth();
  const [saved, setSaved] = useState(initialSaved);
  const [loading, setLoading] = useState(false);
  const [checked, setChecked] = useState(false);

  // Check initial save status
  useEffect(() => {
    if (!token || !user || checked) return;

    async function checkStatus() {
      try {
        const status = await api.checkSaveStatus(designId, token!);
        setSaved(status.is_saved);
        setChecked(true);
      } catch {
        // Ignore errors - assume not saved
        setChecked(true);
      }
    }

    checkStatus();
  }, [designId, token, user, checked]);

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!token || !user) {
      // Redirect to login or show message
      return;
    }

    if (loading) return;

    setLoading(true);
    try {
      if (saved) {
        await api.unsaveDesign(designId, token);
        setSaved(false);
        onSaveChange?.(designId, false);
      } else {
        await api.saveDesign(designId, undefined, token);
        setSaved(true);
        onSaveChange?.(designId, true);
      }
    } catch (err) {
      console.error('Failed to save/unsave:', err);
    } finally {
      setLoading(false);
    }
  };

  // Size classes
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  const buttonSizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  if (variant === 'icon') {
    return (
      <button
        onClick={handleClick}
        disabled={loading || !user}
        className={`p-2 rounded-full transition-colors ${
          saved
            ? 'bg-red-500 text-white hover:bg-red-600'
            : 'bg-white/80 dark:bg-gray-800/80 text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-800'
        } shadow-sm backdrop-blur-sm disabled:opacity-50 disabled:cursor-not-allowed`}
        title={saved ? 'Unsave' : 'Save'}
      >
        {loading ? (
          <Loader2 className={`${sizeClasses[size]} animate-spin`} />
        ) : (
          <Heart
            className={`${sizeClasses[size]} ${saved ? 'fill-current' : ''}`}
          />
        )}
      </button>
    );
  }

  return (
    <button
      onClick={handleClick}
      disabled={loading || !user}
      className={`inline-flex items-center gap-1.5 ${buttonSizeClasses[size]} rounded-lg border transition-colors ${
        saved
          ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30'
          : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {loading ? (
        <Loader2 className={`${sizeClasses[size]} animate-spin`} />
      ) : (
        <Heart
          className={`${sizeClasses[size]} ${saved ? 'fill-current' : ''}`}
        />
      )}
      <span>{saved ? 'Saved' : 'Save'}</span>
    </button>
  );
}

export default SaveButton;
