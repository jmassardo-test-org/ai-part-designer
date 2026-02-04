/**
 * Organization Switcher Component
 *
 * Dropdown in the header to switch between personal account
 * and organization contexts.
 */

import {
  Building2,
  User,
  ChevronDown,
  Check,
  Plus,
  Settings,
  Loader2,
} from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { organizationsApi, Organization } from '@/lib/api/organizations';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface OrgContext {
  type: 'personal' | 'organization';
  org?: Organization;
}

interface OrgSwitcherProps {
  currentContext: OrgContext;
  onContextChange: (context: OrgContext) => void;
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function OrgSwitcher({
  currentContext,
  onContextChange,
  className,
}: OrgSwitcherProps) {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load organizations
  useEffect(() => {
    async function loadOrgs() {
      try {
        const orgs = await organizationsApi.list();
        setOrganizations(orgs);
      } catch (err) {
        console.error('Failed to load organizations:', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadOrgs();
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (context: OrgContext) => {
    onContextChange(context);
    setIsOpen(false);
  };

  const displayName =
    currentContext.type === 'personal'
      ? 'Personal Account'
      : currentContext.org?.name || 'Organization';

  const displayIcon =
    currentContext.type === 'personal' ? (
      <User className="h-4 w-4" />
    ) : currentContext.org?.logo_url ? (
      <img
        src={currentContext.org.logo_url}
        alt=""
        className="h-5 w-5 rounded"
      />
    ) : (
      <Building2 className="h-4 w-4" />
    );

  return (
    <div ref={dropdownRef} className={cn('relative', className)}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
          'border-gray-200 bg-white text-gray-700 hover:bg-gray-50',
          'dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700',
          isOpen && 'ring-2 ring-blue-500'
        )}
      >
        <span className="flex h-6 w-6 items-center justify-center rounded bg-gray-100 dark:bg-gray-700">
          {displayIcon}
        </span>
        <span className="max-w-[150px] truncate">{displayName}</span>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-gray-400 transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className={cn(
            'absolute left-0 top-full z-50 mt-1 w-64 rounded-lg border bg-white py-1 shadow-lg',
            'dark:border-gray-700 dark:bg-gray-800'
          )}
        >
          {/* Personal Account Option */}
          <button
            onClick={() => handleSelect({ type: 'personal' })}
            className={cn(
              'flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition-colors',
              'hover:bg-gray-50 dark:hover:bg-gray-700',
              currentContext.type === 'personal' &&
                'bg-blue-50 dark:bg-blue-900/30'
            )}
          >
            <span className="flex h-8 w-8 items-center justify-center rounded bg-gray-100 dark:bg-gray-700">
              <User className="h-4 w-4 text-gray-600 dark:text-gray-400" />
            </span>
            <span className="flex-1">
              <span className="block font-medium text-gray-900 dark:text-white">
                Personal Account
              </span>
              <span className="block text-xs text-gray-500">
                Your personal projects
              </span>
            </span>
            {currentContext.type === 'personal' && (
              <Check className="h-4 w-4 text-blue-500" />
            )}
          </button>

          {/* Divider */}
          {organizations.length > 0 && (
            <div className="my-1 border-t dark:border-gray-700" />
          )}

          {/* Organizations */}
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
            </div>
          ) : (
            <>
              {organizations.length > 0 && (
                <div className="px-4 py-1">
                  <span className="text-xs font-medium uppercase text-gray-500">
                    Organizations
                  </span>
                </div>
              )}

              {organizations.map((org) => (
                <button
                  key={org.id}
                  onClick={() => handleSelect({ type: 'organization', org })}
                  className={cn(
                    'flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition-colors',
                    'hover:bg-gray-50 dark:hover:bg-gray-700',
                    currentContext.type === 'organization' &&
                      currentContext.org?.id === org.id &&
                      'bg-blue-50 dark:bg-blue-900/30'
                  )}
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded bg-blue-100 dark:bg-blue-900">
                    {org.logo_url ? (
                      <img
                        src={org.logo_url}
                        alt=""
                        className="h-6 w-6 rounded"
                      />
                    ) : (
                      <Building2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    )}
                  </span>
                  <span className="flex-1">
                    <span className="block font-medium text-gray-900 dark:text-white">
                      {org.name}
                    </span>
                    <span className="block text-xs text-gray-500">
                      {org.member_count} member{org.member_count !== 1 ? 's' : ''}
                    </span>
                  </span>
                  {currentContext.type === 'organization' &&
                    currentContext.org?.id === org.id && (
                      <Check className="h-4 w-4 text-blue-500" />
                    )}
                </button>
              ))}
            </>
          )}

          {/* Divider */}
          <div className="my-1 border-t dark:border-gray-700" />

          {/* Actions */}
          <button
            onClick={() => {
              setIsOpen(false);
              navigate('/organizations/new');
            }}
            className={cn(
              'flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition-colors',
              'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-700'
            )}
          >
            <Plus className="h-4 w-4" />
            Create Organization
          </button>

          {currentContext.type === 'organization' && currentContext.org && (
            <button
              onClick={() => {
                setIsOpen(false);
                navigate(`/organizations/${currentContext.org?.id}/settings`);
              }}
              className={cn(
                'flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition-colors',
                'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-700'
              )}
            >
              <Settings className="h-4 w-4" />
              Organization Settings
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default OrgSwitcher;
