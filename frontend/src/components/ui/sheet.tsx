import * as React from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';

// Sheet is implemented as a variant of Dialog for simplicity
// In a full implementation, you'd use @radix-ui/react-dialog with side positioning

const Sheet = Dialog;

const SheetTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, ...props }, ref) => (
  <Button ref={ref} variant="ghost" className={className} {...props} />
));
SheetTrigger.displayName = 'SheetTrigger';

const SheetClose = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, ...props }, ref) => (
  <Button ref={ref} variant="ghost" className={className} {...props} />
));
SheetClose.displayName = 'SheetClose';

const SheetContent = React.forwardRef<
  React.ElementRef<typeof DialogContent>,
  React.ComponentPropsWithoutRef<typeof DialogContent> & {
    side?: 'top' | 'bottom' | 'left' | 'right';
  }
>(({ className, side = 'right', children, ...props }, ref) => {
  const sideStyles = {
    top: 'inset-x-0 top-0 border-b translate-y-0',
    bottom: 'inset-x-0 bottom-0 border-t translate-y-0',
    left: 'inset-y-0 left-0 h-full w-3/4 border-r sm:max-w-sm translate-x-0',
    right: 'inset-y-0 right-0 h-full w-3/4 border-l sm:max-w-sm translate-x-0',
  };

  return (
    <DialogContent
      ref={ref}
      className={cn(
        'fixed z-50 gap-4 bg-background p-6 shadow-lg',
        sideStyles[side],
        className
      )}
      {...props}
    >
      {children}
    </DialogContent>
  );
});
SheetContent.displayName = 'SheetContent';

const SheetHeader = DialogHeader;
const SheetFooter = DialogFooter;
const SheetTitle = DialogTitle;
const SheetDescription = DialogDescription;

export {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
};
