import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Plus,
  Upload,
  Trash2,
  GripVertical,
  Box,
  Settings,
  ChevronRight,
  Minus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { componentsApi } from '@/lib/api/components';
import { ComponentSpecsViewer } from './ComponentSpecsViewer';

interface ProjectComponent {
  id: string;
  component_id: string;
  name: string;
  manufacturer?: string;
  model_number?: string;
  category: string;
  thumbnail_url?: string;
  quantity: number;
  position?: { x: number; y: number; z: number };
  dimensions?: {
    length: number;
    width: number;
    height: number;
  };
}

interface ProjectComponentsListProps {
  projectId: string;
  onComponentSelect?: (componentId: string) => void;
  selectedComponentId?: string;
}

// Sortable item component
function SortableComponentItem({
  component,
  isSelected,
  onSelect,
  onQuantityChange,
  onRemove,
}: {
  component: ProjectComponent;
  isSelected: boolean;
  onSelect: () => void;
  onQuantityChange: (quantity: number) => void;
  onRemove: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: component.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`
        group flex items-center gap-3 p-3 rounded-lg border transition-all
        ${isSelected ? 'border-primary bg-primary/5' : 'border-transparent hover:bg-muted/50'}
        ${isDragging ? 'opacity-50 shadow-lg' : ''}
      `}
    >
      {/* Drag Handle */}
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing p-1 text-muted-foreground hover:text-foreground"
      >
        <GripVertical className="h-4 w-4" />
      </button>

      {/* Thumbnail */}
      <div
        className="w-12 h-12 rounded bg-muted flex items-center justify-center flex-shrink-0 cursor-pointer"
        onClick={onSelect}
      >
        {component.thumbnail_url ? (
          <img
            src={component.thumbnail_url}
            alt={component.name}
            className="w-full h-full object-contain rounded"
          />
        ) : (
          <Box className="h-6 w-6 text-muted-foreground" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 cursor-pointer" onClick={onSelect}>
        <p className="font-medium text-sm truncate">{component.name}</p>
        {component.dimensions && (
          <p className="text-xs text-muted-foreground">
            {component.dimensions.length}×{component.dimensions.width}×{component.dimensions.height} mm
          </p>
        )}
      </div>

      {/* Quantity */}
      <div className="flex items-center space-x-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => onQuantityChange(Math.max(1, component.quantity - 1))}
          disabled={component.quantity <= 1}
        >
          <Minus className="h-3 w-3" />
        </Button>
        <Input
          type="number"
          value={component.quantity}
          onChange={(e) => onQuantityChange(parseInt(e.target.value) || 1)}
          className="w-10 h-6 text-center text-xs p-0"
          min={1}
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => onQuantityChange(component.quantity + 1)}
        >
          <Plus className="h-3 w-3" />
        </Button>
      </div>

      {/* Remove */}
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 group-hover:opacity-100 text-destructive"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Component?</AlertDialogTitle>
            <AlertDialogDescription>
              Remove "{component.name}" from this project? This won't delete the component from your library.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onRemove}>Remove</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

export function ProjectComponentsList({
  projectId,
  onComponentSelect,
  selectedComponentId,
}: ProjectComponentsListProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedForDetails, setSelectedForDetails] = useState<ProjectComponent | null>(null);

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Fetch project components
  const { data: components, isLoading } = useQuery<ProjectComponent[]>({
    queryKey: ['project-components', projectId],
    queryFn: () => componentsApi.getProjectComponents(projectId),
  });

  // Update quantity mutation
  const updateQuantityMutation = useMutation({
    mutationFn: ({ componentId, quantity }: { componentId: string; quantity: number }) =>
      componentsApi.updateProjectComponent(projectId, componentId, { quantity }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-components', projectId] });
    },
  });

  // Remove component mutation
  const removeMutation = useMutation({
    mutationFn: (componentId: string) =>
      componentsApi.removeFromProject(projectId, componentId),
    onSuccess: () => {
      toast({
        title: 'Component Removed',
        description: 'Component has been removed from the project.',
      });
      queryClient.invalidateQueries({ queryKey: ['project-components', projectId] });
    },
  });

  // Reorder mutation
  const reorderMutation = useMutation({
    mutationFn: (newOrder: string[]) =>
      componentsApi.reorderProjectComponents(projectId, newOrder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-components', projectId] });
    },
  });

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id && components) {
      const oldIndex = components.findIndex((c) => c.id === active.id);
      const newIndex = components.findIndex((c) => c.id === over.id);
      const newOrder = arrayMove(components, oldIndex, newIndex).map((c) => c.id);
      
      // Optimistically update
      queryClient.setQueryData(['project-components', projectId], (old: ProjectComponent[] | undefined) =>
        old ? arrayMove(old, oldIndex, newIndex) : old
      );
      
      reorderMutation.mutate(newOrder);
    }
  };

  const handleQuantityChange = (componentId: string, quantity: number) => {
    updateQuantityMutation.mutate({ componentId, quantity });
  };

  const handleRemove = (componentId: string) => {
    removeMutation.mutate(componentId);
  };

  const handleViewDetails = (component: ProjectComponent) => {
    setSelectedForDetails(component);
    setDetailsOpen(true);
  };

  const totalComponents = components?.reduce((sum, c) => sum + c.quantity, 0) || 0;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Project Components</CardTitle>
          <Badge variant="secondary">{totalComponents}</Badge>
        </div>
        <CardDescription className="text-xs">
          Components to include in enclosure generation
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden flex flex-col">
        {/* Add buttons */}
        <div className="flex gap-2 mb-4">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <a href="/components">
              <Plus className="h-4 w-4 mr-1" />
              Library
            </a>
          </Button>
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <a href="/components/upload">
              <Upload className="h-4 w-4 mr-1" />
              Upload
            </a>
          </Button>
        </div>

        {/* Component list */}
        <div className="flex-1 overflow-y-auto -mx-2 px-2">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 p-3">
                  <Skeleton className="h-4 w-4" />
                  <Skeleton className="h-12 w-12 rounded" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-3/4 mb-1" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : components && components.length > 0 ? (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={components.map((c) => c.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-1">
                  {components.map((component) => (
                    <SortableComponentItem
                      key={component.id}
                      component={component}
                      isSelected={selectedComponentId === component.id}
                      onSelect={() => {
                        onComponentSelect?.(component.id);
                        handleViewDetails(component);
                      }}
                      onQuantityChange={(qty) => handleQuantityChange(component.id, qty)}
                      onRemove={() => handleRemove(component.id)}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Box className="h-12 w-12 text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">No components added yet</p>
              <p className="text-xs text-muted-foreground mt-1">
                Add components from the library or upload new ones
              </p>
            </div>
          )}
        </div>

        {/* Generate button */}
        {components && components.length > 0 && (
          <div className="pt-4 border-t mt-4">
            <Button className="w-full">
              <Settings className="h-4 w-4 mr-2" />
              Generate Enclosure
              <ChevronRight className="h-4 w-4 ml-auto" />
            </Button>
          </div>
        )}
      </CardContent>

      {/* Component Details Sheet */}
      <Sheet open={detailsOpen} onOpenChange={setDetailsOpen}>
        <SheetContent className="w-[400px] sm:w-[540px]">
          <SheetHeader>
            <SheetTitle>{selectedForDetails?.name}</SheetTitle>
            <SheetDescription>
              {selectedForDetails?.manufacturer} • {selectedForDetails?.model_number}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            {selectedForDetails && (
              <ComponentSpecsViewer
                componentId={selectedForDetails.component_id}
                compact
              />
            )}
          </div>
        </SheetContent>
      </Sheet>
    </Card>
  );
}

export default ProjectComponentsList;
