/**
 * Tests for Virtual Table Component
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { VirtualTable } from './virtual-table';

// Mock the ThemeContext
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    resolvedTheme: 'dark',
    setTheme: vi.fn(),
    toggleTheme: vi.fn(),
    isLoading: false,
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

interface TestItem {
  id: string;
  name: string;
  email: string;
}

const mockData: TestItem[] = Array.from({ length: 100 }, (_, i) => ({
  id: `id-${i}`,
  name: `User ${i}`,
  email: `user${i}@example.com`,
}));

const columns = [
  { key: 'name', header: 'Name', render: (item: TestItem) => item.name },
  { key: 'email', header: 'Email', render: (item: TestItem) => item.email },
];

describe('VirtualTable', () => {
  it('renders column headers', () => {
    render(<VirtualTable data={mockData} columns={columns} />);
    
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
  });

  it('renders empty message when no data', () => {
    render(<VirtualTable data={[]} columns={columns} />);
    
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('renders custom empty message', () => {
    render(
      <VirtualTable 
        data={[]} 
        columns={columns} 
        emptyMessage="No users found" 
      />
    );
    
    expect(screen.getByText('No users found')).toBeInTheDocument();
  });

  it('renders visible rows', () => {
    render(<VirtualTable data={mockData} columns={columns} maxHeight={200} />);
    
    // Should render at least the first visible row
    expect(screen.getByText('User 0')).toBeInTheDocument();
  });

  it('does not render all rows (virtualizes)', () => {
    const { container } = render(
      <VirtualTable data={mockData} columns={columns} maxHeight={200} />
    );
    
    // With 100 items and maxHeight 200, should not render all 100 rows
    const rows = container.querySelectorAll('tbody tr');
    expect(rows.length).toBeLessThan(100);
  });

  it('calls onRowClick when row is clicked', () => {
    const handleClick = vi.fn();
    render(
      <VirtualTable 
        data={mockData} 
        columns={columns} 
        onRowClick={handleClick}
      />
    );
    
    fireEvent.click(screen.getByText('User 0').closest('tr')!);
    
    expect(handleClick).toHaveBeenCalledWith(mockData[0], 0);
  });

  it('applies custom row className', () => {
    const { container } = render(
      <VirtualTable 
        data={mockData.slice(0, 5)} 
        columns={columns}
        rowClassName={(item, index) => index === 0 ? 'first-row' : ''}
      />
    );
    
    const firstRow = container.querySelector('tbody tr');
    expect(firstRow).toHaveClass('first-row');
  });

  it('applies custom className to container', () => {
    const { container } = render(
      <VirtualTable 
        data={mockData} 
        columns={columns} 
        className="custom-table" 
      />
    );
    
    expect(container.querySelector('.custom-table')).toBeInTheDocument();
  });
});
