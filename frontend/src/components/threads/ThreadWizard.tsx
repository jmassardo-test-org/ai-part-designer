/**
 * ThreadWizard component.
 *
 * Multi-step wizard dialog for selecting a thread family, size,
 * configuring generation options, and generating a thread CAD model.
 */

import { ChevronLeft, ChevronRight, Loader2, Wrench } from 'lucide-react';
import { useCallback, useState } from 'react';
import { PrintOptimizationForm } from '@/components/threads/PrintOptimizationForm';
import { TapDrillReference } from '@/components/threads/TapDrillReference';
import { ThreadPreview3D } from '@/components/threads/ThreadPreview3D';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useThreadFamilies,
  useThreadSizes,
  useThreadSpec,
  useGenerateThread,
  useGeneratePrintOptimized,
} from '@/hooks/useThreads';
import type {
  ThreadType,
  ThreadHand,
  ThreadGenerateResponse,
  PrintProcess,
  ToleranceClass,
  PitchSeries,
} from '@/types/threads';

// =============================================================================
// Types
// =============================================================================

/** Props for the ThreadWizard component. */
export interface ThreadWizardProps {
  /** Whether the wizard dialog is open. */
  isOpen: boolean;
  /** Callback when the dialog is closed. */
  onClose: () => void;
  /** Optional callback when generation completes successfully. */
  onGenerate?: (result: ThreadGenerateResponse) => void;
}

/** Wizard step identifiers. */
type WizardStep = 'family' | 'size' | 'configure' | 'generate';

/** Labels for each wizard step. */
const STEP_LABELS: Record<WizardStep, string> = {
  family: 'Select Family',
  size: 'Select Size',
  configure: 'Configure Options',
  generate: 'Generate',
};

/** Ordered list of steps. */
const STEPS: WizardStep[] = ['family', 'size', 'configure', 'generate'];

// =============================================================================
// Component
// =============================================================================

/**
 * Multi-step wizard for thread selection and CAD generation.
 *
 * Steps:
 * 1. Select thread family (ISO Metric, UNC, etc.)
 * 2. Select size within that family
 * 3. Configure generation options (type, hand, length, chamfer)
 * 4. Generate and preview result
 *
 * @param props - Component props.
 * @returns Rendered wizard dialog.
 */
export function ThreadWizard({ isOpen, onClose, onGenerate }: ThreadWizardProps) {
  // Step state
  const [currentStep, setCurrentStep] = useState<WizardStep>('family');
  const stepIndex = STEPS.indexOf(currentStep);

  // Selection state
  const [selectedFamily, setSelectedFamily] = useState<string | null>(null);
  const [selectedSize, setSelectedSize] = useState<string | null>(null);

  // Configuration state
  const [threadType, setThreadType] = useState<ThreadType>('external');
  const [threadHand, setThreadHand] = useState<ThreadHand>('right');
  const [lengthMm, setLengthMm] = useState<number>(20);
  const [addChamfer, setAddChamfer] = useState<boolean>(true);

  // Print optimization state
  const [printOptEnabled, setPrintOptEnabled] = useState<boolean>(false);
  const [printProcess, setPrintProcess] = useState<PrintProcess>('fdm');
  const [printTolerance, setPrintTolerance] = useState<ToleranceClass>('standard');
  const [nozzleDiameterMm, setNozzleDiameterMm] = useState<number>(0.4);
  const [layerHeightMm, setLayerHeightMm] = useState<number>(0.2);
  const [useFlatBottom, setUseFlatBottom] = useState<boolean>(false);
  const [customClearanceMm, setCustomClearanceMm] = useState<number | null>(null);

  // Pitch series (for metric families)
  const [pitchSeries, setPitchSeries] = useState<PitchSeries | null>(null);

  // Data hooks
  const familiesQuery = useThreadFamilies();
  const sizesQuery = useThreadSizes(selectedFamily, pitchSeries ?? undefined);
  const specQuery = useThreadSpec(selectedFamily, selectedSize);
  const generateMutation = useGenerateThread();
  const printOptMutation = useGeneratePrintOptimized();

  /** Reset wizard to initial state. */
  const resetWizard = useCallback(() => {
    setCurrentStep('family');
    setSelectedFamily(null);
    setSelectedSize(null);
    setThreadType('external');
    setThreadHand('right');
    setLengthMm(20);
    setAddChamfer(true);
    setPrintOptEnabled(false);
    setPrintProcess('fdm');
    setPrintTolerance('standard');
    setNozzleDiameterMm(0.4);
    setLayerHeightMm(0.2);
    setUseFlatBottom(false);
    setCustomClearanceMm(null);
    setPitchSeries(null);
    generateMutation.reset();
    printOptMutation.reset();
  }, [generateMutation, printOptMutation]);

  /** Handle dialog close with reset. */
  const handleClose = useCallback(() => {
    resetWizard();
    onClose();
  }, [resetWizard, onClose]);

  /** Navigate to next step. */
  const goNext = useCallback(() => {
    const idx = STEPS.indexOf(currentStep);
    if (idx < STEPS.length - 1) {
      setCurrentStep(STEPS[idx + 1]);
    }
  }, [currentStep]);

  /** Navigate to previous step. */
  const goBack = useCallback(() => {
    const idx = STEPS.indexOf(currentStep);
    if (idx > 0) {
      setCurrentStep(STEPS[idx - 1]);
    }
  }, [currentStep]);

  /** Handle family selection. */
  const handleFamilySelect = useCallback((family: string) => {
    setSelectedFamily(family);
    setSelectedSize(null);
    setPitchSeries(null);
  }, []);

  /** Handle size selection. */
  const handleSizeSelect = useCallback((size: string) => {
    setSelectedSize(size);
  }, []);

  /** Trigger thread generation. */
  const handleGenerate = useCallback(() => {
    if (!selectedFamily || !selectedSize) return;

    if (printOptEnabled) {
      printOptMutation.mutate(
        {
          family: selectedFamily,
          size: selectedSize,
          thread_type: threadType,
          hand: threadHand,
          length_mm: lengthMm,
          add_chamfer: addChamfer,
          process: printProcess,
          tolerance_class: printTolerance,
          nozzle_diameter_mm: nozzleDiameterMm,
          layer_height_mm: layerHeightMm,
          use_flat_bottom: useFlatBottom,
          custom_clearance_mm: customClearanceMm,
        },
        {
          onSuccess: (result) => {
            onGenerate?.(result.generation_result ?? {
              success: result.success,
              message: result.message,
              generation_time_ms: 0,
              estimated_face_count: 0,
            } as ThreadGenerateResponse);
          },
        },
      );
    } else {
      generateMutation.mutate(
        {
          family: selectedFamily,
          size: selectedSize,
          thread_type: threadType,
          hand: threadHand,
          length_mm: lengthMm,
          add_chamfer: addChamfer,
        },
        {
          onSuccess: (result) => {
            onGenerate?.(result);
          },
        },
      );
    }
  }, [
    selectedFamily, selectedSize, threadType, threadHand, lengthMm, addChamfer,
    printOptEnabled, printProcess, printTolerance, nozzleDiameterMm, layerHeightMm,
    useFlatBottom, customClearanceMm, generateMutation, printOptMutation, onGenerate,
  ]);

  /** Determine if the Next button should be enabled. */
  const canProceed = (): boolean => {
    switch (currentStep) {
      case 'family':
        return !!selectedFamily;
      case 'size':
        return !!selectedSize;
      case 'configure':
        return lengthMm > 0;
      case 'generate':
        return false;
      default:
        return false;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) handleClose(); }}>
      <DialogContent className="max-w-2xl" data-testid="thread-wizard">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wrench className="h-5 w-5" />
            Thread Wizard
          </DialogTitle>
          <DialogDescription>
            Step {stepIndex + 1} of {STEPS.length}: {STEP_LABELS[currentStep]}
          </DialogDescription>
        </DialogHeader>

        {/* Step progress indicator */}
        <div className="flex gap-1 mb-2" data-testid="step-indicator">
          {STEPS.map((step, idx) => (
            <div
              key={step}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                idx <= stepIndex ? 'bg-primary' : 'bg-muted'
              }`}
            />
          ))}
        </div>

        {/* Step content */}
        <div className="min-h-[300px]">
          {currentStep === 'family' && (
            <StepFamily
              families={familiesQuery.data?.families ?? []}
              isLoading={familiesQuery.isLoading}
              selected={selectedFamily}
              onSelect={handleFamilySelect}
            />
          )}

          {currentStep === 'size' && (
            <StepSize
              sizes={sizesQuery.data?.sizes ?? []}
              isLoading={sizesQuery.isLoading}
              selected={selectedSize}
              family={selectedFamily!}
              onSelect={handleSizeSelect}
              pitchSeries={pitchSeries}
              onPitchSeriesChange={setPitchSeries}
            />
          )}

          {currentStep === 'configure' && (
            <StepConfigure
              threadType={threadType}
              onThreadTypeChange={setThreadType}
              threadHand={threadHand}
              onThreadHandChange={setThreadHand}
              lengthMm={lengthMm}
              onLengthChange={setLengthMm}
              addChamfer={addChamfer}
              onChamferChange={setAddChamfer}
              family={selectedFamily}
              size={selectedSize}
              spec={specQuery.data ?? null}
              specLoading={specQuery.isLoading}
              printOptEnabled={printOptEnabled}
              onPrintOptEnabledChange={setPrintOptEnabled}
              printProcess={printProcess}
              onPrintProcessChange={setPrintProcess}
              printTolerance={printTolerance}
              onPrintToleranceChange={setPrintTolerance}
              nozzleDiameterMm={nozzleDiameterMm}
              onNozzleDiameterChange={setNozzleDiameterMm}
              layerHeightMm={layerHeightMm}
              onLayerHeightChange={setLayerHeightMm}
              useFlatBottom={useFlatBottom}
              onFlatBottomChange={setUseFlatBottom}
              customClearanceMm={customClearanceMm}
              onCustomClearanceChange={setCustomClearanceMm}
            />
          )}

          {currentStep === 'generate' && (
            <StepGenerate
              family={selectedFamily!}
              size={selectedSize!}
              threadType={threadType}
              threadHand={threadHand}
              lengthMm={lengthMm}
              addChamfer={addChamfer}
              isPending={generateMutation.isPending || printOptMutation.isPending}
              isSuccess={generateMutation.isSuccess || printOptMutation.isSuccess}
              isError={generateMutation.isError || printOptMutation.isError}
              result={generateMutation.data ?? printOptMutation.data?.generation_result ?? null}
              error={generateMutation.error ?? printOptMutation.error}
              onGenerate={handleGenerate}
              spec={specQuery.data ?? null}
            />
          )}
        </div>

        {/* Footer navigation */}
        <DialogFooter className="flex justify-between sm:justify-between">
          <Button
            variant="outline"
            onClick={goBack}
            disabled={stepIndex === 0}
            data-testid="wizard-back"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back
          </Button>

          <div className="flex gap-2">
            <Button variant="ghost" onClick={handleClose} data-testid="wizard-close">
              Cancel
            </Button>
            {currentStep !== 'generate' && (
              <Button
                onClick={goNext}
                disabled={!canProceed()}
                data-testid="wizard-next"
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// =============================================================================
// Step Sub-Components
// =============================================================================

interface StepFamilyProps {
  families: Array<{ family: string; name: string; description: string; size_count: number }>;
  isLoading: boolean;
  selected: string | null;
  onSelect: (family: string) => void;
}

/** Step 1: Select thread family. */
function StepFamily({ families, isLoading, selected, onSelect }: StepFamilyProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3" data-testid="families-loading">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3" data-testid="family-list">
      {families.map((f) => (
        <button
          key={f.family}
          onClick={() => onSelect(f.family)}
          className={`rounded-lg border p-4 text-left transition-colors hover:bg-accent ${
            selected === f.family
              ? 'border-primary bg-primary/5 ring-1 ring-primary'
              : 'border-border'
          }`}
          data-testid={`family-${f.family}`}
        >
          <div className="font-medium">{f.name}</div>
          <div className="mt-1 text-xs text-muted-foreground line-clamp-2">
            {f.description}
          </div>
          <Badge variant="secondary" className="mt-2">
            {f.size_count} sizes
          </Badge>
        </button>
      ))}
    </div>
  );
}

interface StepSizeProps {
  sizes: string[];
  isLoading: boolean;
  selected: string | null;
  family: string;
  onSelect: (size: string) => void;
  pitchSeries: PitchSeries | null;
  onPitchSeriesChange: (series: PitchSeries | null) => void;
}

/** Step 2: Select thread size. */
function StepSize({ sizes, isLoading, selected, family, onSelect, pitchSeries, onPitchSeriesChange }: StepSizeProps) {
  if (isLoading) {
    return (
      <div className="space-y-2" data-testid="sizes-loading">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 rounded" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {family === 'iso_metric' && (
        <div className="flex gap-2 mb-3">
          <Button variant={pitchSeries !== 'fine' ? 'default' : 'outline'} size="sm" onClick={() => onPitchSeriesChange(null)}>Coarse</Button>
          <Button variant={pitchSeries === 'fine' ? 'default' : 'outline'} size="sm" onClick={() => onPitchSeriesChange('fine')}>Fine</Button>
        </div>
      )}
      <div className="grid grid-cols-3 gap-2 max-h-[250px] overflow-y-auto" data-testid="size-list">
        {sizes.map((size) => (
          <button
            key={size}
            onClick={() => onSelect(size)}
            className={`rounded-md border px-3 py-2 text-sm transition-colors hover:bg-accent ${
              selected === size
                ? 'border-primary bg-primary/5 ring-1 ring-primary font-medium'
                : 'border-border'
            }`}
            data-testid={`size-${size}`}
          >
            {size}
          </button>
        ))}
      </div>

      {selected && (
        <div className="mt-4">
          <h4 className="text-sm font-medium mb-2">Tap Drill Reference</h4>
          <TapDrillReference family={family} size={selected} />
        </div>
      )}
    </div>
  );
}

interface StepConfigureProps {
  threadType: ThreadType;
  onThreadTypeChange: (value: ThreadType) => void;
  threadHand: ThreadHand;
  onThreadHandChange: (value: ThreadHand) => void;
  lengthMm: number;
  onLengthChange: (value: number) => void;
  addChamfer: boolean;
  onChamferChange: (value: boolean) => void;
  family: string | null;
  size: string | null;
  spec: import('@/types/threads').ThreadSpec | null;
  specLoading: boolean;
  printOptEnabled: boolean;
  onPrintOptEnabledChange: (enabled: boolean) => void;
  printProcess: PrintProcess;
  onPrintProcessChange: (process: PrintProcess) => void;
  printTolerance: ToleranceClass;
  onPrintToleranceChange: (tc: ToleranceClass) => void;
  nozzleDiameterMm: number;
  onNozzleDiameterChange: (val: number) => void;
  layerHeightMm: number;
  onLayerHeightChange: (val: number) => void;
  useFlatBottom: boolean;
  onFlatBottomChange: (val: boolean) => void;
  customClearanceMm: number | null;
  onCustomClearanceChange: (val: number | null) => void;
}

/** Step 3: Configure generation options. */
function StepConfigure({
  threadType,
  onThreadTypeChange,
  threadHand,
  onThreadHandChange,
  lengthMm,
  onLengthChange,
  addChamfer,
  onChamferChange,
  family,
  size,
  spec,
  specLoading,
  printOptEnabled,
  onPrintOptEnabledChange,
  printProcess,
  onPrintProcessChange,
  printTolerance,
  onPrintToleranceChange,
  nozzleDiameterMm,
  onNozzleDiameterChange,
  layerHeightMm,
  onLayerHeightChange,
  useFlatBottom,
  onFlatBottomChange,
  customClearanceMm,
  onCustomClearanceChange,
}: StepConfigureProps) {
  return (
    <div className="space-y-4" data-testid="configure-step">
      {/* Thread spec summary */}
      {specLoading && <Skeleton className="h-16 rounded" />}
      {spec && (
        <div className="rounded-md border bg-muted/30 p-3 text-sm space-y-1">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Major Diameter</span>
            <span className="font-mono">{spec.major_diameter.toFixed(3)} mm</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Pitch</span>
            <span className="font-mono">{spec.pitch_mm.toFixed(3)} mm</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Profile Angle</span>
            <span className="font-mono">{spec.profile_angle_deg}°</span>
          </div>
        </div>
      )}

      {/* Thread type */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium" htmlFor="thread-type">Thread Type</label>
        <Select value={threadType} onValueChange={(v) => onThreadTypeChange(v as ThreadType)}>
          <SelectTrigger id="thread-type" data-testid="thread-type-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="external">External (bolt)</SelectItem>
            <SelectItem value="internal">Internal (nut)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Thread hand */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium" htmlFor="thread-hand">Helix Direction</label>
        <Select value={threadHand} onValueChange={(v) => onThreadHandChange(v as ThreadHand)}>
          <SelectTrigger id="thread-hand" data-testid="thread-hand-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="right">Right-hand</SelectItem>
            <SelectItem value="left">Left-hand</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Length */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium" htmlFor="thread-length">Length (mm)</label>
        <Input
          id="thread-length"
          type="number"
          min={1}
          max={500}
          value={lengthMm}
          onChange={(e) => onLengthChange(Number(e.target.value))}
          data-testid="thread-length-input"
        />
      </div>

      {/* Chamfer */}
      <div className="flex items-center gap-2">
        <input
          id="add-chamfer"
          type="checkbox"
          checked={addChamfer}
          onChange={(e) => onChamferChange(e.target.checked)}
          className="h-4 w-4 rounded border-border"
          data-testid="chamfer-checkbox"
        />
        <label className="text-sm" htmlFor="add-chamfer">Add entry chamfer</label>
      </div>

      {/* Print optimization */}
      <PrintOptimizationForm
        enabled={printOptEnabled}
        onEnabledChange={onPrintOptEnabledChange}
        process={printProcess}
        onProcessChange={onPrintProcessChange}
        toleranceClass={printTolerance}
        onToleranceClassChange={onPrintToleranceChange}
        nozzleDiameterMm={nozzleDiameterMm}
        onNozzleDiameterChange={onNozzleDiameterChange}
        layerHeightMm={layerHeightMm}
        onLayerHeightChange={onLayerHeightChange}
        useFlatBottom={useFlatBottom}
        onFlatBottomChange={onFlatBottomChange}
        customClearanceMm={customClearanceMm}
        onCustomClearanceChange={onCustomClearanceChange}
        family={family}
        size={size}
      />
    </div>
  );
}

interface StepGenerateProps {
  family: string;
  size: string;
  threadType: ThreadType;
  threadHand: ThreadHand;
  lengthMm: number;
  addChamfer: boolean;
  isPending: boolean;
  isSuccess: boolean;
  isError: boolean;
  result: ThreadGenerateResponse | null;
  error: Error | null;
  onGenerate: () => void;
  spec: import('@/types/threads').ThreadSpec | null;
}

/** Step 4: Generate thread and show result. */
function StepGenerate({
  family,
  size,
  threadType,
  threadHand,
  lengthMm,
  addChamfer,
  isPending,
  isSuccess,
  isError,
  result,
  error,
  onGenerate,
  spec,
}: StepGenerateProps) {
  return (
    <div className="space-y-4" data-testid="generate-step">
      {/* Thread preview */}
      <ThreadPreview3D
        spec={spec}
        threadType={threadType}
        lengthMm={lengthMm}
        className="h-48 mb-4"
      />

      {/* Summary */}
      <div className="rounded-md border p-4 space-y-2">
        <h4 className="font-medium">Generation Summary</h4>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-muted-foreground">Family</div>
          <div className="font-mono">{family}</div>
          <div className="text-muted-foreground">Size</div>
          <div className="font-mono">{size}</div>
          <div className="text-muted-foreground">Type</div>
          <div>{threadType}</div>
          <div className="text-muted-foreground">Hand</div>
          <div>{threadHand}</div>
          <div className="text-muted-foreground">Length</div>
          <div className="font-mono">{lengthMm} mm</div>
          <div className="text-muted-foreground">Chamfer</div>
          <div>{addChamfer ? 'Yes' : 'No'}</div>
        </div>
      </div>

      {/* Generate button */}
      {!isSuccess && (
        <Button
          onClick={onGenerate}
          disabled={isPending}
          className="w-full"
          data-testid="generate-button"
        >
          {isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Generating…
            </>
          ) : (
            'Generate Thread'
          )}
        </Button>
      )}

      {/* Error state */}
      {isError && error && (
        <div
          className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
          data-testid="generate-error"
        >
          {error.message}
        </div>
      )}

      {/* Success state */}
      {isSuccess && result && (
        <div className="rounded-md border border-green-500/50 bg-green-50 dark:bg-green-950/20 p-4 space-y-2" data-testid="generate-result">
          <div className="flex items-center gap-2">
            <Badge variant="default" className="bg-green-600">Success</Badge>
            <span className="text-sm font-medium">{result.message}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-muted-foreground">Generation Time</div>
            <div className="font-mono">{result.generation_time_ms.toFixed(0)} ms</div>
            <div className="text-muted-foreground">Estimated Faces</div>
            <div className="font-mono">{result.estimated_face_count.toLocaleString()}</div>
          </div>
        </div>
      )}
    </div>
  );
}
