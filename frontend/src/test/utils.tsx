/**
 * Test utilities and custom render function.
 */

import { render, RenderOptions } from '@testing-library/react';
import { ReactElement } from 'react';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';

// All providers wrapper
function AllProviders({ children }: { children: React.ReactNode }) {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          {children}
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

// Custom render that wraps components with providers
function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Options for renderWithRouter
interface RouterRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: Array<string | { pathname: string; state?: unknown }>;
  route?: string;
}

// Render with MemoryRouter for tests needing location state or specific routes
function renderWithRouter(
  ui: ReactElement,
  { initialEntries = ['/'], route = '*', ...options }: RouterRenderOptions = {},
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={initialEntries}>
        <ThemeProvider>
          <AuthProvider>
            <Routes>
              <Route path={route} element={children} />
            </Routes>
          </AuthProvider>
        </ThemeProvider>
      </MemoryRouter>
    );
  }
  return render(ui, { wrapper: Wrapper, ...options });
}

// Re-export everything from testing-library except render (which we override)
export { 
  screen, 
  fireEvent, 
  waitFor, 
  within,
  act,
  cleanup,
  renderHook,
} from '@testing-library/react';
export { userEvent } from '@testing-library/user-event';

// Override render with custom render
export { customRender as render, renderWithRouter };
