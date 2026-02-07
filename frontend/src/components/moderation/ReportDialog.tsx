/**
 * Report content dialog component.
 */

import { Flag } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Textarea } from '@/components/ui/textarea';

type ReportReason = 'spam' | 'inappropriate' | 'copyright' | 'misleading' | 'offensive' | 'other';
type ReportTargetType = 'template' | 'comment' | 'design' | 'user';

interface ReportDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog closes */
  onOpenChange: (open: boolean) => void;
  /** Type of content being reported */
  targetType: ReportTargetType;
  /** ID of content being reported */
  targetId: string;
  /** Callback when report is submitted */
  onSubmit: (data: {
    target_type: ReportTargetType;
    target_id: string;
    reason: ReportReason;
    description?: string;
  }) => Promise<void>;
}

const reasonLabels: Record<ReportReason, { label: string; description: string }> = {
  spam: {
    label: 'Spam',
    description: 'Unsolicited advertising or repetitive content',
  },
  inappropriate: {
    label: 'Inappropriate',
    description: 'Content not suitable for this platform',
  },
  copyright: {
    label: 'Copyright Violation',
    description: 'Content that infringes on intellectual property rights',
  },
  misleading: {
    label: 'Misleading',
    description: 'False or deceptive information',
  },
  offensive: {
    label: 'Offensive',
    description: 'Hateful, harassing, or discriminatory content',
  },
  other: {
    label: 'Other',
    description: 'Another issue not listed above',
  },
};

/**
 * Dialog for reporting content (templates, comments, etc.)
 */
export function ReportDialog({
  open,
  onOpenChange,
  targetType,
  targetId,
  onSubmit,
}: ReportDialogProps) {
  const [reason, setReason] = useState<ReportReason | null>(null);
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleSubmit = async () => {
    if (!reason) {
      setError('Please select a reason');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      await onSubmit({
        target_type: targetType,
        target_id: targetId,
        reason,
        description: description.trim() || undefined,
      });
      
      // Reset and close
      setReason(null);
      setDescription('');
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit report');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleClose = () => {
    if (!isSubmitting) {
      setReason(null);
      setDescription('');
      setError(null);
      onOpenChange(false);
    }
  };
  
  const targetLabel = {
    template: 'template',
    comment: 'comment',
    design: 'design',
    user: 'user',
  }[targetType];
  
  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Flag className="h-5 w-5 text-red-500" />
            Report {targetLabel}
          </DialogTitle>
          <DialogDescription>
            Help us understand what's wrong with this {targetLabel}. Your report
            will be reviewed by our moderation team.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-3">
            <Label>Reason for reporting</Label>
            <RadioGroup
              value={reason || ''}
              onValueChange={(value) => setReason(value as ReportReason)}
            >
              {(Object.keys(reasonLabels) as ReportReason[]).map((key) => (
                <div key={key} className="flex items-start space-x-3">
                  <RadioGroupItem value={key} id={`reason-${key}`} className="mt-1" />
                  <div className="space-y-0.5">
                    <Label htmlFor={`reason-${key}`} className="cursor-pointer">
                      {reasonLabels[key].label}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      {reasonLabels[key].description}
                    </p>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="description">
              Additional details <span className="text-muted-foreground">(optional)</span>
            </Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide any additional context that might help us understand the issue..."
              className="min-h-[80px] resize-none"
              maxLength={1000}
            />
            <p className="text-xs text-muted-foreground text-right">
              {description.length}/1000
            </p>
          </div>
          
          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!reason || isSubmitting}
            className="bg-red-600 hover:bg-red-700"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Report'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
