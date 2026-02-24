/**
 * PrintOptimizationForm component.
 *
 * Provides controls for configuring 3D-print-optimized thread generation,
 * including process selection, tolerance, nozzle/layer settings (FDM),
 * and a live recommendation panel displaying feasibility analysis.
 */

import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { usePrintRecommendation } from '@/hooks/useThreads';
import type {
  PrintFeasibility,
  PrintProcess,
  PrintRecommendation,
  ToleranceClass,
} from '@/types/threads';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PROCESS_LABELS: Record<PrintProcess, string> = {
  fdm: 'FDM',
  sla: 'SLA',
  sls: 'SLS',
  mjf: 'MJF',
};

/** Subset of processes exposed in the selector as per requirements. */
const SELECTABLE_PROCESSES: PrintProcess[] = ['fdm', 'sla', 'sls'];

const TOLERANCE_LABELS: Record<ToleranceClass, string> = {
  tight: 'Tight',
  standard: 'Standard',
  loose: 'Loose',
};

const FEASIBILITY_COLORS: Record<PrintFeasibility, string> = {
  excellent: 'bg-green-500/15 text-green-700 border-green-500/30',
  good: 'bg-blue-500/15 text-blue-700 border-blue-500/30',
  marginal: 'bg-yellow-500/15 text-yellow-700 border-yellow-500/30',
  not_recommended: 'bg-red-500/15 text-red-700 border-red-500/30',
};

const FEASIBILITY_LABEL: Record<PrintFeasibility, string> = {
  excellent: 'Excellent',
  good: 'Good',
  marginal: 'Marginal',
  not_recommended: 'Not Recommended',
};

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

/** Clamp a numeric value within inclusive bounds. */
function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

/** Props for the {@link PrintOptimizationForm} component. */
export interface PrintOptimizationFormProps {
  /** Whether print optimization is active. */
  enabled: boolean;
  /** Callback when the enabled state changes. */
  onEnabledChange: (enabled: boolean) => void;

  /** Selected 3D printing process. */
  process: PrintProcess;
  /** Callback when the process selection changes. */
  onProcessChange: (process: PrintProcess) => void;

  /** Selected tolerance class. */
  toleranceClass: ToleranceClass;
  /** Callback when the tolerance class changes. */
  onToleranceClassChange: (tc: ToleranceClass) => void;

  /** Nozzle diameter in millimetres (FDM only). */
  nozzleDiameterMm: number;
  /** Callback when the nozzle diameter changes. */
  onNozzleDiameterChange: (val: number) => void;

  /** Layer height in millimetres (FDM only). */
  layerHeightMm: number;
  /** Callback when the layer height changes. */
  onLayerHeightChange: (val: number) => void;

  /** Whether to use a flat-bottom thread profile (FDM only). */
  useFlatBottom: boolean;
  /** Callback when the flat-bottom toggle changes. */
  onFlatBottomChange: (val: boolean) => void;

  /** Optional custom clearance override in millimetres (null = auto). */
  customClearanceMm: number | null;
  /** Callback when the custom clearance changes. */
  onCustomClearanceChange: (val: number | null) => void;

  /** Current thread family identifier used for recommendations. */
  family: string | null;
  /** Current thread size designation used for recommendations. */
  size: string | null;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/**
 * Renders the live recommendation panel when a print recommendation is
 * available or loading.
 */
function RecommendationPanel({
  recommendation,
  isLoading,
  error,
}: {
  recommendation: PrintRecommendation | undefined;
  isLoading: boolean;
  error: Error | null;
}) {
  if (isLoading) {
    return (
      <div
        className="space-y-3 rounded-md border p-4"
        data-testid="print-recommendation"
      >
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
        data-testid="print-recommendation"
      >
        Failed to load print recommendation.
      </div>
    );
  }

  if (!recommendation) {
    return null;
  }

  const colorClass =
    FEASIBILITY_COLORS[recommendation.feasibility] ?? FEASIBILITY_COLORS.good;
  const feasibilityLabel =
    FEASIBILITY_LABEL[recommendation.feasibility] ?? recommendation.feasibility;

  return (
    <div
      className="space-y-3 rounded-md border p-4"
      data-testid="print-recommendation"
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">Feasibility</span>
        <Badge className={colorClass} variant="outline">
          {feasibilityLabel}
        </Badge>
        {recommendation.estimated_strength_pct > 0 && (
          <span className="ml-auto text-xs text-muted-foreground">
            ~{recommendation.estimated_strength_pct}% strength
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <span className="text-muted-foreground">Recommended clearance</span>
        <span className="font-mono">{recommendation.clearance_mm.toFixed(2)} mm</span>

        <span className="text-muted-foreground">Recommended tolerance</span>
        <span>{recommendation.recommended_tolerance}</span>

        <span className="text-muted-foreground">Min recommended size</span>
        <span>{recommendation.min_recommended_size}</span>
      </div>

      {recommendation.orientation_advice && (
        <div className="text-sm">
          <span className="font-medium">Orientation: </span>
          <span className="text-muted-foreground">
            {recommendation.orientation_advice}
          </span>
        </div>
      )}

      {recommendation.notes.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {recommendation.notes.map((note, idx) => (
            <li key={idx}>{note}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * Form section for configuring 3D-print-optimized thread parameters.
 *
 * Includes a master toggle, process/tolerance selectors, FDM-specific
 * inputs (nozzle, layer height, flat-bottom), an optional custom clearance
 * override, and a live recommendation panel.
 *
 * @param props - Component props.
 * @returns Rendered print optimization form.
 */
export function PrintOptimizationForm({
  enabled,
  onEnabledChange,
  process,
  onProcessChange,
  toleranceClass,
  onToleranceClassChange,
  nozzleDiameterMm,
  onNozzleDiameterChange,
  layerHeightMm,
  onLayerHeightChange,
  useFlatBottom,
  onFlatBottomChange,
  customClearanceMm,
  onCustomClearanceChange,
  family,
  size,
}: PrintOptimizationFormProps) {
  const isFdm = process === 'fdm';

  // Fetch recommendation when enabled and a family + size are selected.
  const {
    data: recommendation,
    isLoading: recLoading,
    error: recError,
  } = usePrintRecommendation(
    enabled ? family : null,
    enabled ? size : null,
    process,
  );

  // ------- Event handlers -------

  /** Handle nozzle diameter input change with validation. */
  const handleNozzleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = parseFloat(e.target.value);
    if (Number.isNaN(raw)) return;
    onNozzleDiameterChange(clamp(raw, 0.1, 1.0));
  };

  /** Handle layer height input change with validation. */
  const handleLayerHeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = parseFloat(e.target.value);
    if (Number.isNaN(raw)) return;
    onLayerHeightChange(clamp(raw, 0.05, 0.5));
  };

  /** Handle custom clearance input change with validation. */
  const handleClearanceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.trim();
    if (value === '') {
      onCustomClearanceChange(null);
      return;
    }
    const raw = parseFloat(value);
    if (Number.isNaN(raw)) return;
    onCustomClearanceChange(clamp(raw, 0.05, 2.0));
  };

  return (
    <div className="space-y-4">
      {/* Master toggle */}
      <div className="flex items-center justify-between">
        <Label htmlFor="print-opt-toggle" className="cursor-pointer">
          Enable Print Optimization
        </Label>
        <Switch
          id="print-opt-toggle"
          checked={enabled}
          onCheckedChange={onEnabledChange}
          data-testid="print-opt-toggle"
        />
      </div>

      {!enabled && (
        <p className="text-sm text-muted-foreground">
          Standard thread geometry will be generated.
        </p>
      )}

      {enabled && (
        <div className="space-y-4">
          {/* Process selector */}
          <div className="space-y-1.5">
            <Label htmlFor="process-select">Printing Process</Label>
            <Select
              value={process}
              onValueChange={(val) => onProcessChange(val as PrintProcess)}
            >
              <SelectTrigger id="process-select" data-testid="process-select">
                <SelectValue placeholder="Select process" />
              </SelectTrigger>
              <SelectContent>
                {SELECTABLE_PROCESSES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {PROCESS_LABELS[p]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Tolerance selector */}
          <div className="space-y-1.5">
            <Label htmlFor="tolerance-select">Tolerance Class</Label>
            <Select
              value={toleranceClass}
              onValueChange={(val) =>
                onToleranceClassChange(val as ToleranceClass)
              }
            >
              <SelectTrigger
                id="tolerance-select"
                data-testid="tolerance-select"
              >
                <SelectValue placeholder="Select tolerance" />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(TOLERANCE_LABELS) as ToleranceClass[]).map(
                  (tc) => (
                    <SelectItem key={tc} value={tc}>
                      {TOLERANCE_LABELS[tc]}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>

          {/* FDM-specific controls */}
          {isFdm && (
            <>
              {/* Nozzle diameter */}
              <div className="space-y-1.5">
                <Label htmlFor="nozzle-input">Nozzle Diameter (mm)</Label>
                <Input
                  id="nozzle-input"
                  type="number"
                  min={0.1}
                  max={1.0}
                  step={0.1}
                  value={nozzleDiameterMm}
                  onChange={handleNozzleChange}
                  data-testid="nozzle-input"
                />
              </div>

              {/* Layer height */}
              <div className="space-y-1.5">
                <Label htmlFor="layer-height-input">Layer Height (mm)</Label>
                <Input
                  id="layer-height-input"
                  type="number"
                  min={0.05}
                  max={0.5}
                  step={0.05}
                  value={layerHeightMm}
                  onChange={handleLayerHeightChange}
                  data-testid="layer-height-input"
                />
              </div>

              {/* Flat bottom toggle */}
              <div className="flex items-center justify-between">
                <Label
                  htmlFor="flat-bottom-checkbox"
                  className="cursor-pointer"
                >
                  Flat-Bottom Thread Profile
                </Label>
                <Switch
                  id="flat-bottom-checkbox"
                  checked={useFlatBottom}
                  onCheckedChange={onFlatBottomChange}
                  data-testid="flat-bottom-checkbox"
                />
              </div>
            </>
          )}

          {/* Custom clearance override */}
          <div className="space-y-1.5">
            <Label htmlFor="clearance-input">
              Custom Clearance (mm){' '}
              <span className="text-muted-foreground font-normal">
                — leave empty for auto
              </span>
            </Label>
            <Input
              id="clearance-input"
              type="number"
              min={0.05}
              max={2.0}
              step={0.05}
              value={customClearanceMm ?? ''}
              onChange={handleClearanceChange}
              placeholder="Auto"
              data-testid="clearance-input"
            />
          </div>

          {/* Live recommendation panel */}
          {family && size && (
            <RecommendationPanel
              recommendation={recommendation}
              isLoading={recLoading}
              error={recError}
            />
          )}
        </div>
      )}
    </div>
  );
}
