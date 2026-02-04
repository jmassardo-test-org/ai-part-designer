import { useQuery } from '@tanstack/react-query';
import { 
  Ruler, 
  Circle, 
  Plug, 
  Box, 
  Thermometer,
  AlertCircle,
  CheckCircle2,
  Info
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { componentsApi } from '@/lib/api/components';

interface ComponentSpecsViewerProps {
  componentId: string;
  showTitle?: boolean;
  compact?: boolean;
}

interface ComponentSpecs {
  id: string;
  name: string;
  dimensions?: {
    length: number;
    width: number;
    height: number;
    pcb_thickness?: number;
  };
  mounting_holes?: Array<{
    x: number;
    y: number;
    diameter: number;
    type?: string;
    label?: string;
  }>;
  connectors?: Array<{
    name: string;
    type: string;
    x: number;
    y: number;
    width: number;
    height: number;
    side: string;
  }>;
  clearance_zones?: Array<{
    name: string;
    x: number;
    y: number;
    width: number;
    height: number;
    z_height: number;
    side: string;
  }>;
  thermal_properties?: {
    max_temp_c?: number;
    recommended_ventilation?: boolean;
    heat_zones?: Array<{ x: number; y: number; radius: number }>;
  };
  weight_grams?: number;
  datasheet_url?: string;
  is_verified?: boolean;
  confidence?: number;
}

export function ComponentSpecsViewer({
  componentId,
  showTitle = false,
  compact = false,
}: ComponentSpecsViewerProps) {
  const { data: specs, isLoading, error } = useQuery<ComponentSpecs>({
    queryKey: ['component-specs', componentId],
    queryFn: () => componentsApi.getComponent(componentId),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (error || !specs) {
    return (
      <div className="flex items-center justify-center py-8 text-muted-foreground">
        <AlertCircle className="h-5 w-5 mr-2" />
        <span>Failed to load specifications</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {showTitle && (
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">{specs.name}</h3>
          {specs.is_verified && (
            <Badge variant="outline" className="text-green-600 border-green-600">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Verified
            </Badge>
          )}
        </div>
      )}

      {specs.confidence && (
        <div className="flex items-center space-x-3 p-3 bg-muted/50 rounded-lg">
          <Info className="h-4 w-4 text-muted-foreground" />
          <div className="flex-1">
            <div className="flex items-center justify-between text-sm mb-1">
              <span>Extraction Confidence</span>
              <span className="font-medium">{Math.round(specs.confidence * 100)}%</span>
            </div>
            <Progress value={specs.confidence * 100} className="h-1.5" />
          </div>
        </div>
      )}

      <Tabs defaultValue="dimensions">
        <TabsList className={compact ? 'grid w-full grid-cols-4' : 'grid w-full grid-cols-5'}>
          <TabsTrigger value="dimensions" className="text-xs sm:text-sm">
            <Ruler className="h-4 w-4 mr-1 hidden sm:inline" />
            Dimensions
          </TabsTrigger>
          <TabsTrigger value="mounting" className="text-xs sm:text-sm">
            <Circle className="h-4 w-4 mr-1 hidden sm:inline" />
            Mounting
          </TabsTrigger>
          <TabsTrigger value="connectors" className="text-xs sm:text-sm">
            <Plug className="h-4 w-4 mr-1 hidden sm:inline" />
            Connectors
          </TabsTrigger>
          <TabsTrigger value="clearance" className="text-xs sm:text-sm">
            <Box className="h-4 w-4 mr-1 hidden sm:inline" />
            Clearance
          </TabsTrigger>
          {!compact && (
            <TabsTrigger value="thermal" className="text-xs sm:text-sm">
              <Thermometer className="h-4 w-4 mr-1 hidden sm:inline" />
              Thermal
            </TabsTrigger>
          )}
        </TabsList>

        {/* Dimensions Tab */}
        <TabsContent value="dimensions" className="mt-4">
          {specs.dimensions ? (
            <div className="space-y-4">
              {/* Visual Diagram */}
              <div className="relative bg-muted/30 rounded-lg p-6 flex items-center justify-center">
                <svg
                  viewBox="0 0 200 150"
                  className="w-full max-w-sm"
                  style={{ maxHeight: '200px' }}
                >
                  {/* 3D Box representation */}
                  <g transform="translate(50, 30)">
                    {/* Top face */}
                    <polygon
                      points="0,40 50,20 100,40 50,60"
                      fill="hsl(var(--primary) / 0.2)"
                      stroke="hsl(var(--primary))"
                      strokeWidth="2"
                    />
                    {/* Left face */}
                    <polygon
                      points="0,40 0,90 50,110 50,60"
                      fill="hsl(var(--primary) / 0.3)"
                      stroke="hsl(var(--primary))"
                      strokeWidth="2"
                    />
                    {/* Right face */}
                    <polygon
                      points="50,60 50,110 100,90 100,40"
                      fill="hsl(var(--primary) / 0.1)"
                      stroke="hsl(var(--primary))"
                      strokeWidth="2"
                    />
                  </g>
                  
                  {/* Dimension labels */}
                  <text x="100" y="130" textAnchor="middle" className="text-xs fill-current">
                    {specs.dimensions.length} mm
                  </text>
                  <text x="155" y="70" textAnchor="start" className="text-xs fill-current">
                    {specs.dimensions.width} mm
                  </text>
                  <text x="40" y="80" textAnchor="end" className="text-xs fill-current">
                    {specs.dimensions.height} mm
                  </text>
                </svg>
              </div>

              {/* Dimension Values */}
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardContent className="pt-4 text-center">
                    <p className="text-2xl font-bold">{specs.dimensions.length}</p>
                    <p className="text-sm text-muted-foreground">Length (mm)</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4 text-center">
                    <p className="text-2xl font-bold">{specs.dimensions.width}</p>
                    <p className="text-sm text-muted-foreground">Width (mm)</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4 text-center">
                    <p className="text-2xl font-bold">{specs.dimensions.height}</p>
                    <p className="text-sm text-muted-foreground">Height (mm)</p>
                  </CardContent>
                </Card>
              </div>

              {specs.dimensions.pcb_thickness && (
                <p className="text-sm text-muted-foreground text-center">
                  PCB Thickness: {specs.dimensions.pcb_thickness} mm
                </p>
              )}

              {specs.weight_grams && (
                <p className="text-sm text-muted-foreground text-center">
                  Weight: {specs.weight_grams}g
                </p>
              )}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No dimension data available
            </p>
          )}
        </TabsContent>

        {/* Mounting Holes Tab */}
        <TabsContent value="mounting" className="mt-4">
          {specs.mounting_holes && specs.mounting_holes.length > 0 ? (
            <div className="space-y-4">
              {/* Visual Diagram */}
              <div className="relative bg-muted/30 rounded-lg p-4">
                <svg
                  viewBox={`0 0 ${specs.dimensions?.length || 100} ${specs.dimensions?.width || 60}`}
                  className="w-full"
                  style={{ maxHeight: '200px' }}
                >
                  {/* PCB outline */}
                  <rect
                    x="0"
                    y="0"
                    width={specs.dimensions?.length || 100}
                    height={specs.dimensions?.width || 60}
                    fill="hsl(var(--muted))"
                    stroke="hsl(var(--border))"
                    strokeWidth="1"
                    rx="2"
                  />
                  
                  {/* Mounting holes */}
                  {specs.mounting_holes.map((hole, i) => (
                    <g key={i}>
                      <circle
                        cx={hole.x}
                        cy={hole.y}
                        r={hole.diameter / 2}
                        fill="none"
                        stroke="hsl(var(--primary))"
                        strokeWidth="1"
                      />
                      <circle
                        cx={hole.x}
                        cy={hole.y}
                        r="1"
                        fill="hsl(var(--primary))"
                      />
                    </g>
                  ))}
                </svg>
              </div>

              {/* Hole List */}
              <div className="space-y-2">
                {specs.mounting_holes.map((hole, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-mono">
                        #{index + 1}
                      </div>
                      <div>
                        <p className="font-medium text-sm">
                          Position: ({hole.x}, {hole.y})
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Diameter: {hole.diameter} mm
                        </p>
                      </div>
                    </div>
                    {hole.type && (
                      <Badge variant="outline">{hole.type}</Badge>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No mounting hole data available
            </p>
          )}
        </TabsContent>

        {/* Connectors Tab */}
        <TabsContent value="connectors" className="mt-4">
          {specs.connectors && specs.connectors.length > 0 ? (
            <div className="space-y-3">
              {specs.connectors.map((conn, index) => (
                <Card key={index}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium">{conn.name}</h4>
                        <p className="text-sm text-muted-foreground mt-1">
                          Type: {conn.type}
                        </p>
                      </div>
                      <Badge variant="secondary">{conn.side}</Badge>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                      <div className="bg-muted/50 rounded p-2">
                        <span className="text-muted-foreground">Position:</span>
                        <span className="ml-1 font-mono">({conn.x}, {conn.y})</span>
                      </div>
                      <div className="bg-muted/50 rounded p-2">
                        <span className="text-muted-foreground">Cutout:</span>
                        <span className="ml-1 font-mono">{conn.width}×{conn.height} mm</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No connector data available
            </p>
          )}
        </TabsContent>

        {/* Clearance Zones Tab */}
        <TabsContent value="clearance" className="mt-4">
          {specs.clearance_zones && specs.clearance_zones.length > 0 ? (
            <div className="space-y-3">
              {specs.clearance_zones.map((zone, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 border rounded-lg bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-900"
                >
                  <div>
                    <h4 className="font-medium text-orange-900 dark:text-orange-100">
                      {zone.name}
                    </h4>
                    <p className="text-sm text-orange-700 dark:text-orange-300 mt-1">
                      {zone.width} × {zone.height} × {zone.z_height} mm
                    </p>
                  </div>
                  <Badge variant="outline" className="border-orange-500 text-orange-700 dark:text-orange-300">
                    {zone.side} side
                  </Badge>
                </div>
              ))}
              <p className="text-xs text-muted-foreground mt-2">
                Keep these areas clear of obstructions for proper component function.
              </p>
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No clearance zone data available
            </p>
          )}
        </TabsContent>

        {/* Thermal Tab */}
        {!compact && (
          <TabsContent value="thermal" className="mt-4">
            {specs.thermal_properties ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  {specs.thermal_properties.max_temp_c && (
                    <Card>
                      <CardContent className="pt-4 text-center">
                        <Thermometer className="h-8 w-8 mx-auto mb-2 text-orange-500" />
                        <p className="text-2xl font-bold">
                          {specs.thermal_properties.max_temp_c}°C
                        </p>
                        <p className="text-sm text-muted-foreground">Max Operating Temp</p>
                      </CardContent>
                    </Card>
                  )}
                  <Card>
                    <CardContent className="pt-4 text-center">
                      <Box className="h-8 w-8 mx-auto mb-2 text-blue-500" />
                      <p className="text-2xl font-bold">
                        {specs.thermal_properties.recommended_ventilation ? 'Yes' : 'No'}
                      </p>
                      <p className="text-sm text-muted-foreground">Ventilation Required</p>
                    </CardContent>
                  </Card>
                </div>

                {specs.thermal_properties.heat_zones && specs.thermal_properties.heat_zones.length > 0 && (
                  <div className="p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 rounded-lg">
                    <h4 className="font-medium text-red-900 dark:text-red-100 mb-2">
                      Heat Zones
                    </h4>
                    <p className="text-sm text-red-700 dark:text-red-300">
                      This component has {specs.thermal_properties.heat_zones.length} heat-generating zone(s).
                      Consider adding ventilation or heat sinks in your enclosure design.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-center text-muted-foreground py-8">
                No thermal data available
              </p>
            )}
          </TabsContent>
        )}
      </Tabs>

      {specs.datasheet_url && (
        <div className="pt-4 border-t">
          <a
            href={specs.datasheet_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-primary hover:underline"
          >
            View Original Datasheet →
          </a>
        </div>
      )}
    </div>
  );
}

export default ComponentSpecsViewer;
