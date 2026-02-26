/**
 * TapDrillReference component.
 *
 * Displays tap drill and clearance hole information for a given thread
 * family and size in a compact reference table.
 */

import { Loader2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useTapDrill } from '@/hooks/useThreads';

/** Props for the TapDrillReference component. */
export interface TapDrillReferenceProps {
  /** Thread family identifier (e.g. 'iso_metric'). */
  family: string;
  /** Thread size designation (e.g. 'M8'). */
  size: string;
}

/**
 * Read-only reference table showing tap drill and clearance hole data.
 *
 * Fetches data for the specified family/size and displays tap drill diameter
 * along with close, medium, and free clearance hole sizes.
 *
 * @param props - Component props.
 * @returns Rendered tap drill reference table.
 */
export function TapDrillReference({ family, size }: TapDrillReferenceProps) {
  const { data, isLoading, error } = useTapDrill(family, size);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4" data-testid="tap-drill-loading">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading tap drill data…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive" data-testid="tap-drill-error">
        Failed to load tap drill information.
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="rounded-md border" data-testid="tap-drill-table">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Measurement</TableHead>
            <TableHead className="text-right">Diameter (mm)</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell className="font-medium">Tap Drill</TableCell>
            <TableCell className="text-right" data-testid="tap-drill-value">
              {data.tap_drill_mm.toFixed(2)}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Clearance – Close</TableCell>
            <TableCell className="text-right" data-testid="clearance-close-value">
              {data.clearance_hole_close_mm.toFixed(2)}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Clearance – Medium</TableCell>
            <TableCell className="text-right" data-testid="clearance-medium-value">
              {data.clearance_hole_medium_mm.toFixed(2)}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Clearance – Free</TableCell>
            <TableCell className="text-right" data-testid="clearance-free-value">
              {data.clearance_hole_free_mm.toFixed(2)}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  );
}
