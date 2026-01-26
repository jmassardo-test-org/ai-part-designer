import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
} from './table';

describe('Table', () => {
  it('renders without crashing', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <Table className="custom-table">
        <TableBody>
          <TableRow>
            <TableCell>Content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByRole('table')).toHaveClass('custom-table');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLTableElement>();
    render(
      <Table ref={ref}>
        <TableBody>
          <TableRow>
            <TableCell>Content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(ref.current).toBeInstanceOf(HTMLTableElement);
  });
});

describe('TableHeader', () => {
  it('renders without crashing', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Header</TableHead>
          </TableRow>
        </TableHeader>
      </Table>
    );
    expect(screen.getByRole('rowgroup')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <Table>
        <TableHeader className="custom-header" data-testid="header">
          <TableRow>
            <TableHead>Header</TableHead>
          </TableRow>
        </TableHeader>
      </Table>
    );
    expect(screen.getByTestId('header')).toHaveClass('custom-header');
  });
});

describe('TableBody', () => {
  it('renders without crashing', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByRole('rowgroup')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <Table>
        <TableBody className="custom-body" data-testid="body">
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByTestId('body')).toHaveClass('custom-body');
  });
});

describe('TableFooter', () => {
  it('renders without crashing', () => {
    render(
      <Table>
        <TableFooter>
          <TableRow>
            <TableCell>Footer</TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    );
    expect(screen.getByRole('rowgroup')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <Table>
        <TableFooter className="custom-footer" data-testid="footer">
          <TableRow>
            <TableCell>Footer</TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    );
    expect(screen.getByTestId('footer')).toHaveClass('custom-footer');
  });
});

describe('TableRow', () => {
  it('renders without crashing', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByRole('row')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <Table>
        <TableBody>
          <TableRow className="custom-row">
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByRole('row')).toHaveClass('custom-row');
  });
});

describe('TableHead', () => {
  it('renders without crashing', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Header</TableHead>
          </TableRow>
        </TableHeader>
      </Table>
    );
    expect(screen.getByRole('columnheader')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="custom-head">Header</TableHead>
          </TableRow>
        </TableHeader>
      </Table>
    );
    expect(screen.getByRole('columnheader')).toHaveClass('custom-head');
  });
});

describe('TableCell', () => {
  it('renders without crashing', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Cell Content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByRole('cell')).toBeInTheDocument();
    expect(screen.getByText('Cell Content')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell className="custom-cell">Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByRole('cell')).toHaveClass('custom-cell');
  });
});

describe('TableCaption', () => {
  it('renders without crashing', () => {
    render(
      <Table>
        <TableCaption>Table Caption</TableCaption>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByText('Table Caption')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <Table>
        <TableCaption className="custom-caption">Caption</TableCaption>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByText('Caption')).toHaveClass('custom-caption');
  });
});
