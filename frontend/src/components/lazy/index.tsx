/**
 * Lazy loaded components for bundle optimization.
 *
 * Heavy components are lazy loaded to reduce initial bundle size.
 * React.lazy + Suspense enables code splitting by route/component.
 */

import React, { Suspense, ComponentType } from 'react';

// Loading fallback for lazy components
function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-600"></div>
    </div>
  );
}

// Skeleton loader for 3D viewer
function ViewerSkeleton() {
  return (
    <div className="bg-gray-100 rounded-lg min-h-[400px] flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600 mx-auto mb-4"></div>
        <p className="text-gray-500">Loading 3D Viewer...</p>
      </div>
    </div>
  );
}

// Page loading skeleton
function PageSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/4"></div>
      <div className="h-4 bg-gray-200 rounded w-3/4"></div>
      <div className="h-4 bg-gray-200 rounded w-1/2"></div>
      <div className="grid grid-cols-3 gap-4 mt-8">
        <div className="h-32 bg-gray-200 rounded"></div>
        <div className="h-32 bg-gray-200 rounded"></div>
        <div className="h-32 bg-gray-200 rounded"></div>
      </div>
    </div>
  );
}

/**
 * Create a lazy component with a fallback
 */
export function lazyWithFallback<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  fallback: React.ReactNode = <LoadingSpinner />
): React.LazyExoticComponent<T> & { Suspense: React.FC<React.ComponentProps<T>> } {
  const LazyComponent = React.lazy(importFn);
  
  const SuspenseWrapper: React.FC<React.ComponentProps<T>> = (props) => (
    <Suspense fallback={fallback}>
      <LazyComponent {...props} />
    </Suspense>
  );
  
  return Object.assign(LazyComponent, { Suspense: SuspenseWrapper });
}

/**
 * Preload a component before it's needed
 */
export function preloadComponent<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>
): void {
  importFn();
}

// ============================================================================
// Lazy loaded heavy components
// ============================================================================

/**
 * Lazy loaded 3D Viewer
 * Only loaded when user needs to view 3D models
 */
export const LazyCADViewer = lazyWithFallback(
  () => import('@/components/viewer/CADViewer'),
  <ViewerSkeleton />
);

/**
 * Lazy loaded Admin Dashboard
 * Only loaded for admin users
 */
export const LazyAdminDashboard = lazyWithFallback(
  () => import('@/pages/admin/AdminDashboard'),
  <PageSkeleton />
);

/**
 * Lazy loaded Settings Page
 * Heavy form with multiple sections
 */
export const LazySettingsPage = lazyWithFallback(
  () => import('@/pages/SettingsPage'),
  <PageSkeleton />
);

/**
 * Lazy loaded Projects Page
 * Complex page with grids and modals
 */
export const LazyProjectsPage = lazyWithFallback(
  () => import('@/pages/ProjectsPage'),
  <PageSkeleton />
);

/**
 * Lazy loaded Generate Page (v2)
 * Heavy component with parameter forms and preview
 */
export const LazyGeneratePage = lazyWithFallback(
  () => import('@/pages/GeneratePageV2'),
  <PageSkeleton />
);

/**
 * Lazy loaded Files Page
 * File manager with preview capabilities
 */
export const LazyFilesPage = lazyWithFallback(
  () => import('@/pages/FilesPage'),
  <PageSkeleton />
);

// ============================================================================
// Preload functions for anticipated navigation
// ============================================================================

/**
 * Preload dashboard related components
 * Called after login
 */
export function preloadDashboard(): void {
  preloadComponent(() => import('@/pages/DashboardPage'));
  preloadComponent(() => import('@/pages/ProjectsPage'));
}

/**
 * Preload 3D viewer components
 * Called when hovering over a design
 */
export function preload3DViewer(): void {
  preloadComponent(() => import('@/components/viewer/CADViewer'));
}

/**
 * Preload admin components
 * Called for admin users
 */
export function preloadAdmin(): void {
  preloadComponent(() => import('@/pages/admin/AdminDashboard'));
}

// ============================================================================
// Exports
// ============================================================================

export { LoadingSpinner, ViewerSkeleton, PageSkeleton };
