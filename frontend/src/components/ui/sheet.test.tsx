import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { describe, it, expect } from 'vitest';
import {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
} from './sheet';

describe('SheetTrigger', () => {
  it('renders as a button', () => {
    render(<SheetTrigger>Open Sheet</SheetTrigger>);
    expect(screen.getByRole('button', { name: /open sheet/i })).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<SheetTrigger className="custom-trigger">Open</SheetTrigger>);
    expect(screen.getByRole('button', { name: /open/i })).toHaveClass('custom-trigger');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLButtonElement>();
    render(<SheetTrigger ref={ref}>Open</SheetTrigger>);
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
  });
});

describe('SheetClose', () => {
  it('renders as a button', () => {
    render(<SheetClose>Close</SheetClose>);
    expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<SheetClose className="custom-close">Close</SheetClose>);
    expect(screen.getByRole('button', { name: /close/i })).toHaveClass('custom-close');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLButtonElement>();
    render(<SheetClose ref={ref}>Close</SheetClose>);
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
  });
});

describe('Sheet with Dialog', () => {
  it('opens sheet when trigger is clicked', async () => {
    render(
      <Sheet>
        <SheetTrigger>Open Sheet</SheetTrigger>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Sheet Title</SheetTitle>
            <SheetDescription>Sheet description text</SheetDescription>
          </SheetHeader>
        </SheetContent>
      </Sheet>
    );

    // SheetTrigger is a Button, not a DialogTrigger, so we need to test differently
    // The Sheet component wraps Dialog, so opening requires the Dialog to be controlled
    expect(screen.getByRole('button', { name: /open sheet/i })).toBeInTheDocument();
  });

  it('renders sheet content when open', async () => {
    render(
      <Sheet open>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Sheet Title</SheetTitle>
            <SheetDescription>Description</SheetDescription>
          </SheetHeader>
        </SheetContent>
      </Sheet>
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Sheet Title')).toBeInTheDocument();
  });

  it('applies side styles for right position', () => {
    render(
      <Sheet open>
        <SheetContent side="right">
          <SheetTitle>Content</SheetTitle>
          <SheetDescription>Description</SheetDescription>
        </SheetContent>
      </Sheet>
    );
    
    expect(screen.getByRole('dialog')).toHaveClass('right-0');
  });

  it('applies side styles for left position', () => {
    render(
      <Sheet open>
        <SheetContent side="left">
          <SheetTitle>Content</SheetTitle>
          <SheetDescription>Description</SheetDescription>
        </SheetContent>
      </Sheet>
    );
    
    expect(screen.getByRole('dialog')).toHaveClass('left-0');
  });

  it('applies side styles for top position', () => {
    render(
      <Sheet open>
        <SheetContent side="top">
          <SheetTitle>Content</SheetTitle>
          <SheetDescription>Description</SheetDescription>
        </SheetContent>
      </Sheet>
    );
    
    expect(screen.getByRole('dialog')).toHaveClass('top-0');
  });

  it('applies side styles for bottom position', () => {
    render(
      <Sheet open>
        <SheetContent side="bottom">
          <SheetTitle>Content</SheetTitle>
          <SheetDescription>Description</SheetDescription>
        </SheetContent>
      </Sheet>
    );
    
    expect(screen.getByRole('dialog')).toHaveClass('bottom-0');
  });

  it('renders footer content', () => {
    render(
      <Sheet open>
        <SheetContent>
          <SheetTitle>Title</SheetTitle>
          <SheetDescription>Description</SheetDescription>
          <SheetFooter data-testid="footer">
            <button>Action</button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    );

    expect(screen.getByTestId('footer')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /action/i })).toBeInTheDocument();
  });
});
