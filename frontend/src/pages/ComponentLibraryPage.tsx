import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Search, 
  Grid3X3, 
  List, 
  Plus, 
  Upload,
  Cpu,
  Monitor,
  Zap,
  ToggleLeft,
  Plug,
  Thermometer,
  Volume2,
  HardDrive,
  Box,
  Star,
  Loader2,
  Eye
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { useDebounce } from '@/hooks/use-debounce';
import { componentsApi } from '@/lib/api/components';
import { ComponentSpecsViewer } from '@/components/components/ComponentSpecsViewer';

// Category icons
const CATEGORY_ICONS: Record<string, React.ElementType> = {
  sbc: Cpu,
  mcu: Cpu,
  display: Monitor,
  input: ToggleLeft,
  connector: Plug,
  sensor: Thermometer,
  power: Zap,
  audio: Volume2,
  storage: HardDrive,
  other: Box,
};

// Category labels
const CATEGORY_LABELS: Record<string, string> = {
  sbc: 'Single Board Computers',
  mcu: 'Microcontrollers',
  display: 'Displays',
  input: 'Input Devices',
  connector: 'Connectors',
  sensor: 'Sensors',
  power: 'Power Components',
  audio: 'Audio Components',
  storage: 'Storage',
  other: 'Other',
};

interface LibraryComponent {
  id: string;
  component_id: string;
  name: string;
  description?: string;
  category: string;
  subcategory?: string;
  manufacturer?: string;
  model_number?: string;
  thumbnail_url?: string;
  dimensions?: {
    length: number;
    width: number;
    height: number;
  };
  popularity_score: number;
  usage_count: number;
  is_featured: boolean;
  tags: string[];
}

interface LibrarySearchResponse {
  items: LibraryComponent[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export function ComponentLibraryPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedManufacturer, setSelectedManufacturer] = useState<string>('');
  const [sortBy, setSortBy] = useState<'popularity' | 'name' | 'newest'>('popularity');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [page, setPage] = useState(1);
  const [selectedComponent, setSelectedComponent] = useState<LibraryComponent | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const debouncedSearch = useDebounce(searchQuery, 300);

  // Fetch components
  const { data, isLoading, error } = useQuery<LibrarySearchResponse>({
    queryKey: ['library-components', debouncedSearch, selectedCategory, selectedManufacturer, sortBy, page],
    queryFn: () => componentsApi.browseLibrary({
      search: debouncedSearch || undefined,
      category: selectedCategory || undefined,
      manufacturer: selectedManufacturer || undefined,
      sort_by: sortBy,
      page,
      page_size: 20,
    }),
  });

  // Fetch categories
  const { data: categories } = useQuery({
    queryKey: ['library-categories'],
    queryFn: () => componentsApi.getCategories(),
  });

  // Fetch manufacturers
  const { data: manufacturers } = useQuery({
    queryKey: ['library-manufacturers'],
    queryFn: () => componentsApi.getManufacturers(),
  });

  // Add to project mutation
  const addToProjectMutation = useMutation({
    mutationFn: (libraryId: string) => componentsApi.addToProject(libraryId),
    onSuccess: () => {
      toast({
        title: 'Component Added',
        description: 'Component has been added to your project.',
      });
      setDetailsOpen(false);
      queryClient.invalidateQueries({ queryKey: ['project-components'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to Add',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Active category filter items
  const categoryList = useMemo(() => {
    return Object.entries(CATEGORY_LABELS).map(([value, label]) => ({
      value,
      label,
      icon: CATEGORY_ICONS[value],
      count: categories?.find((c: any) => c.name === value)?.total || 0,
    }));
  }, [categories]);

  const handleViewDetails = (component: LibraryComponent) => {
    setSelectedComponent(component);
    setDetailsOpen(true);
  };

  const handleAddToProject = (component: LibraryComponent) => {
    addToProjectMutation.mutate(component.id);
  };

  const getCategoryIcon = (category: string) => {
    const Icon = CATEGORY_ICONS[category] || Box;
    return <Icon className="h-4 w-4" />;
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 border-r bg-muted/30 p-4 space-y-6">
        <div>
          <h3 className="font-semibold mb-3">Categories</h3>
          <div className="space-y-1">
            <Button
              variant={selectedCategory === '' ? 'secondary' : 'ghost'}
              className="w-full justify-start"
              onClick={() => setSelectedCategory('')}
            >
              <Grid3X3 className="h-4 w-4 mr-2" />
              All Components
              {data && (
                <Badge variant="outline" className="ml-auto">
                  {data.total}
                </Badge>
              )}
            </Button>
            {categoryList.map(({ value, label, icon: Icon, count }) => (
              <Button
                key={value}
                variant={selectedCategory === value ? 'secondary' : 'ghost'}
                className="w-full justify-start"
                onClick={() => setSelectedCategory(value)}
              >
                <Icon className="h-4 w-4 mr-2" />
                <span className="truncate">{label}</span>
                {count > 0 && (
                  <Badge variant="outline" className="ml-auto">
                    {count}
                  </Badge>
                )}
              </Button>
            ))}
          </div>
        </div>

        {manufacturers && manufacturers.length > 0 && (
          <div>
            <h3 className="font-semibold mb-3">Manufacturers</h3>
            <Select value={selectedManufacturer} onValueChange={setSelectedManufacturer}>
              <SelectTrigger>
                <SelectValue placeholder="All manufacturers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All manufacturers</SelectItem>
                {manufacturers.map((m: { name: string; count: number }) => (
                  <SelectItem key={m.name} value={m.name}>
                    {m.name} ({m.count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="pt-4 border-t">
          <Button className="w-full" asChild>
            <a href="/components/upload">
              <Upload className="h-4 w-4 mr-2" />
              Upload Component
            </a>
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Component Library</h1>
            <p className="text-muted-foreground">
              Browse pre-configured components for your enclosure designs
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('grid')}
            >
              <Grid3X3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="flex items-center space-x-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search components..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as any)}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="popularity">Most Popular</SelectItem>
              <SelectItem value="name">Name A-Z</SelectItem>
              <SelectItem value="newest">Newest First</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className={viewMode === 'grid' ? 'grid grid-cols-3 gap-4' : 'space-y-4'}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <Skeleton className="h-32 w-full mb-4" />
                  <Skeleton className="h-5 w-3/4 mb-2" />
                  <Skeleton className="h-4 w-1/2" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-12">
            <p className="text-destructive">Failed to load components</p>
            <Button variant="outline" className="mt-4" onClick={() => queryClient.invalidateQueries({ queryKey: ['library-components'] })}>
              Retry
            </Button>
          </div>
        )}

        {/* Component Grid */}
        {data && !isLoading && (
          <>
            {data.items.length === 0 ? (
              <div className="text-center py-12">
                <Box className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="font-semibold">No components found</h3>
                <p className="text-muted-foreground">
                  Try adjusting your search or filters
                </p>
              </div>
            ) : (
              <div className={
                viewMode === 'grid'
                  ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
                  : 'space-y-3'
              }>
                {data.items.map((component) => (
                  viewMode === 'grid' ? (
                    <Card key={component.id} className="group hover:border-primary transition-colors">
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2">
                            {getCategoryIcon(component.category)}
                            <Badge variant="outline" className="text-xs">
                              {CATEGORY_LABELS[component.category] || component.category}
                            </Badge>
                          </div>
                          {component.is_featured && (
                            <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                          )}
                        </div>
                      </CardHeader>
                      <CardContent>
                        {/* Thumbnail */}
                        <div className="aspect-video bg-muted rounded-md mb-3 flex items-center justify-center">
                          {component.thumbnail_url ? (
                            <img
                              src={component.thumbnail_url}
                              alt={component.name}
                              className="w-full h-full object-contain rounded-md"
                            />
                          ) : (
                            <Box className="h-12 w-12 text-muted-foreground" />
                          )}
                        </div>
                        <CardTitle className="text-base line-clamp-1">
                          {component.name}
                        </CardTitle>
                        {component.manufacturer && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {component.manufacturer}
                          </p>
                        )}
                        {component.dimensions && (
                          <p className="text-xs text-muted-foreground mt-2">
                            {component.dimensions.length} × {component.dimensions.width} × {component.dimensions.height} mm
                          </p>
                        )}
                      </CardContent>
                      <CardFooter className="pt-0 gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => handleViewDetails(component)}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          Details
                        </Button>
                        <Button
                          size="sm"
                          className="flex-1"
                          onClick={() => handleAddToProject(component)}
                          disabled={addToProjectMutation.isPending}
                        >
                          <Plus className="h-4 w-4 mr-1" />
                          Add
                        </Button>
                      </CardFooter>
                    </Card>
                  ) : (
                    <Card key={component.id} className="hover:border-primary transition-colors">
                      <CardContent className="flex items-center p-4">
                        {/* Thumbnail */}
                        <div className="w-20 h-20 bg-muted rounded-md flex items-center justify-center mr-4 flex-shrink-0">
                          {component.thumbnail_url ? (
                            <img
                              src={component.thumbnail_url}
                              alt={component.name}
                              className="w-full h-full object-contain rounded-md"
                            />
                          ) : (
                            <Box className="h-8 w-8 text-muted-foreground" />
                          )}
                        </div>
                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <h3 className="font-semibold truncate">{component.name}</h3>
                            {component.is_featured && (
                              <Star className="h-4 w-4 text-yellow-500 fill-yellow-500 flex-shrink-0" />
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {component.manufacturer} • {component.model_number}
                          </p>
                          {component.dimensions && (
                            <p className="text-xs text-muted-foreground mt-1">
                              {component.dimensions.length} × {component.dimensions.width} × {component.dimensions.height} mm
                            </p>
                          )}
                          <div className="flex items-center space-x-2 mt-2">
                            <Badge variant="outline" className="text-xs">
                              {CATEGORY_LABELS[component.category] || component.category}
                            </Badge>
                          </div>
                        </div>
                        {/* Actions */}
                        <div className="flex items-center space-x-2 ml-4">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleViewDetails(component)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleAddToProject(component)}
                            disabled={addToProjectMutation.isPending}
                          >
                            <Plus className="h-4 w-4 mr-1" />
                            Add
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )
                ))}
              </div>
            )}

            {/* Pagination */}
            {data.total_pages > 1 && (
              <div className="flex items-center justify-center space-x-2 mt-8">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground">
                  Page {page} of {data.total_pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                  disabled={page === data.total_pages}
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Component Details Dialog */}
      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedComponent && (
            <>
              <DialogHeader>
                <div className="flex items-center space-x-2">
                  {getCategoryIcon(selectedComponent.category)}
                  <Badge variant="outline">
                    {CATEGORY_LABELS[selectedComponent.category]}
                  </Badge>
                  {selectedComponent.is_featured && (
                    <Badge className="bg-yellow-500">Featured</Badge>
                  )}
                </div>
                <DialogTitle className="text-2xl">{selectedComponent.name}</DialogTitle>
                <DialogDescription>
                  {selectedComponent.manufacturer} • {selectedComponent.model_number}
                </DialogDescription>
              </DialogHeader>
              
              <div className="py-4">
                <ComponentSpecsViewer componentId={selectedComponent.component_id} />
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setDetailsOpen(false)}>
                  Close
                </Button>
                <Button
                  onClick={() => handleAddToProject(selectedComponent)}
                  disabled={addToProjectMutation.isPending}
                >
                  {addToProjectMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4 mr-2" />
                  )}
                  Add to Project
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default ComponentLibraryPage;
