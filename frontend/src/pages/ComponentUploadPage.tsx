import { useMutation } from '@tanstack/react-query';
import { 
  Upload, 
  FileText, 
  Cpu, 
  Box, 
  CheckCircle, 
  Loader2,
  Edit2,
  Save,
  X
} from 'lucide-react';
import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { componentsApi } from '@/lib/api/components';

// Component categories
const CATEGORIES = [
  { value: 'sbc', label: 'Single Board Computers' },
  { value: 'mcu', label: 'Microcontrollers' },
  { value: 'display', label: 'Displays' },
  { value: 'input', label: 'Input Devices' },
  { value: 'connector', label: 'Connectors' },
  { value: 'sensor', label: 'Sensors' },
  { value: 'power', label: 'Power Components' },
  { value: 'audio', label: 'Audio Components' },
  { value: 'storage', label: 'Storage' },
  { value: 'other', label: 'Other' },
];

type UploadStep = 'upload' | 'extracting' | 'review' | 'complete';

interface ExtractedSpecs {
  dimensions?: {
    length: number;
    width: number;
    height: number;
    unit: string;
  };
  mounting_holes?: Array<{
    x: number;
    y: number;
    diameter: number;
    type?: string;
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
  confidence?: number;
}

export function ComponentUploadPage() {
  const { toast } = useToast();
  const [step, setStep] = useState<UploadStep>('upload');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [extractionProgress, setExtractionProgress] = useState(0);
  const [extractedSpecs, setExtractedSpecs] = useState<ExtractedSpecs | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: '',
    manufacturer: '',
    model_number: '',
    tags: '',
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return componentsApi.uploadComponent(formData, (progress: number) => {
        setExtractionProgress(progress);
      });
    },
    onSuccess: (data) => {
      setExtractedSpecs(data.specifications);
      setFormData(prev => ({
        ...prev,
        name: data.name || prev.name,
        manufacturer: data.manufacturer || prev.manufacturer,
        model_number: data.model_number || prev.model_number,
      }));
      setStep('review');
    },
    onError: (error: Error) => {
      toast({
        title: 'Upload Failed',
        description: error.message,
        variant: 'destructive',
      });
      setStep('upload');
    },
  });

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      return componentsApi.createComponent({
        ...formData,
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
        specifications: extractedSpecs as Record<string, unknown> | undefined,
      });
    },
    onSuccess: () => {
      toast({
        title: 'Component Saved',
        description: 'Your component has been added to your library.',
      });
      setStep('complete');
    },
    onError: (error: Error) => {
      toast({
        title: 'Save Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // File dropzone
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setUploadedFile(file);
      // Auto-extract name from filename
      const nameFromFile = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      setFormData(prev => ({ ...prev, name: nameFromFile }));
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'model/step': ['.step', '.stp'],
      'model/stl': ['.stl'],
      'image/vnd.dxf': ['.dxf'],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const handleStartExtraction = () => {
    if (!uploadedFile) return;
    setStep('extracting');
    setExtractionProgress(0);
    uploadMutation.mutate(uploadedFile);
  };

  const handleSave = () => {
    if (!formData.name || !formData.category) {
      toast({
        title: 'Missing Information',
        description: 'Please provide a name and category.',
        variant: 'destructive',
      });
      return;
    }
    saveMutation.mutate();
  };

  const handleReset = () => {
    setStep('upload');
    setUploadedFile(null);
    setExtractedSpecs(null);
    setExtractionProgress(0);
    setFormData({
      name: '',
      description: '',
      category: '',
      manufacturer: '',
      model_number: '',
      tags: '',
    });
  };

  const getFileIcon = () => {
    if (!uploadedFile) return <Upload className="h-12 w-12 text-muted-foreground" />;
    const ext = uploadedFile.name.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return <FileText className="h-12 w-12 text-red-500" />;
    if (ext === 'step' || ext === 'stp') return <Box className="h-12 w-12 text-blue-500" />;
    if (ext === 'stl') return <Cpu className="h-12 w-12 text-green-500" />;
    return <FileText className="h-12 w-12 text-muted-foreground" />;
  };

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Upload Reference Component</h1>
        <p className="text-muted-foreground mt-2">
          Upload a datasheet, CAD file, or 3D model to extract component specifications.
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between mb-8">
        {['Upload', 'Extract', 'Review', 'Complete'].map((label, index) => {
          const stepNames: UploadStep[] = ['upload', 'extracting', 'review', 'complete'];
          const currentIndex = stepNames.indexOf(step);
          const isActive = index === currentIndex;
          const isComplete = index < currentIndex;

          return (
            <div key={label} className="flex items-center">
              <div
                className={`
                  flex items-center justify-center w-10 h-10 rounded-full
                  ${isComplete ? 'bg-primary text-primary-foreground' : ''}
                  ${isActive ? 'bg-primary text-primary-foreground' : ''}
                  ${!isActive && !isComplete ? 'bg-muted text-muted-foreground' : ''}
                `}
              >
                {isComplete ? (
                  <CheckCircle className="h-5 w-5" />
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>
              <span className={`ml-2 ${isActive ? 'font-semibold' : ''}`}>
                {label}
              </span>
              {index < 3 && (
                <div className={`w-16 h-0.5 mx-4 ${isComplete ? 'bg-primary' : 'bg-muted'}`} />
              )}
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      {step === 'upload' && (
        <div className="space-y-6">
          {/* File Upload */}
          <Card>
            <CardHeader>
              <CardTitle>Upload File</CardTitle>
              <CardDescription>
                Supported formats: PDF datasheets, STEP, STL, DXF
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                {...getRootProps()}
                className={`
                  border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
                  transition-colors
                  ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
                  ${uploadedFile ? 'bg-muted/50' : ''}
                `}
              >
                <input {...getInputProps()} />
                <div className="flex flex-col items-center space-y-4">
                  {getFileIcon()}
                  {uploadedFile ? (
                    <>
                      <p className="font-medium">{uploadedFile.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                      <Button variant="outline" size="sm">
                        Choose Different File
                      </Button>
                    </>
                  ) : (
                    <>
                      <p className="font-medium">
                        {isDragActive ? 'Drop file here' : 'Drag & drop or click to upload'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Max file size: 50MB
                      </p>
                    </>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Component Info */}
          <Card>
            <CardHeader>
              <CardTitle>Component Information</CardTitle>
              <CardDescription>
                Basic details about your component (can be auto-filled from file)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Component Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Raspberry Pi 5"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category">Category *</Label>
                  <Select
                    value={formData.category}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, category: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((cat) => (
                        <SelectItem key={cat.value} value={cat.value}>
                          {cat.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="manufacturer">Manufacturer</Label>
                  <Input
                    id="manufacturer"
                    value={formData.manufacturer}
                    onChange={(e) => setFormData(prev => ({ ...prev, manufacturer: e.target.value }))}
                    placeholder="e.g., Raspberry Pi Foundation"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="model_number">Model Number</Label>
                  <Input
                    id="model_number"
                    value={formData.model_number}
                    onChange={(e) => setFormData(prev => ({ ...prev, model_number: e.target.value }))}
                    placeholder="e.g., RPI5-8GB"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Brief description of the component"
                  rows={3}
                />
              </div>
            </CardContent>
            <CardFooter className="flex justify-end">
              <Button
                onClick={handleStartExtraction}
                disabled={!uploadedFile}
              >
                Extract Specifications
              </Button>
            </CardFooter>
          </Card>
        </div>
      )}

      {step === 'extracting' && (
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center space-y-6">
              <Loader2 className="h-16 w-16 animate-spin text-primary" />
              <div className="text-center">
                <h3 className="text-lg font-semibold">Extracting Specifications</h3>
                <p className="text-muted-foreground mt-1">
                  AI is analyzing your file to extract dimensions and features...
                </p>
              </div>
              <div className="w-full max-w-md">
                <Progress value={extractionProgress} className="h-2" />
                <p className="text-center text-sm text-muted-foreground mt-2">
                  {extractionProgress}% complete
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 'review' && extractedSpecs && (
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Extracted Specifications</CardTitle>
                <CardDescription>
                  Review and edit the extracted specifications
                </CardDescription>
              </div>
              {extractedSpecs.confidence && (
                <Badge variant={extractedSpecs.confidence > 0.8 ? 'default' : 'secondary'}>
                  {Math.round(extractedSpecs.confidence * 100)}% Confidence
                </Badge>
              )}
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="dimensions">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="dimensions">Dimensions</TabsTrigger>
                  <TabsTrigger value="mounting">Mounting Holes</TabsTrigger>
                  <TabsTrigger value="connectors">Connectors</TabsTrigger>
                  <TabsTrigger value="clearance">Clearance</TabsTrigger>
                </TabsList>

                <TabsContent value="dimensions" className="mt-4">
                  {extractedSpecs.dimensions ? (
                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label>Length</Label>
                        <div className="flex items-center space-x-2">
                          <Input
                            type="number"
                            value={extractedSpecs.dimensions.length}
                            onChange={(e) => setExtractedSpecs(prev => ({
                              ...prev!,
                              dimensions: { ...prev!.dimensions!, length: parseFloat(e.target.value) }
                            }))}
                            disabled={!isEditing}
                          />
                          <span className="text-muted-foreground">mm</span>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Width</Label>
                        <div className="flex items-center space-x-2">
                          <Input
                            type="number"
                            value={extractedSpecs.dimensions.width}
                            onChange={(e) => setExtractedSpecs(prev => ({
                              ...prev!,
                              dimensions: { ...prev!.dimensions!, width: parseFloat(e.target.value) }
                            }))}
                            disabled={!isEditing}
                          />
                          <span className="text-muted-foreground">mm</span>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Height</Label>
                        <div className="flex items-center space-x-2">
                          <Input
                            type="number"
                            value={extractedSpecs.dimensions.height}
                            onChange={(e) => setExtractedSpecs(prev => ({
                              ...prev!,
                              dimensions: { ...prev!.dimensions!, height: parseFloat(e.target.value) }
                            }))}
                            disabled={!isEditing}
                          />
                          <span className="text-muted-foreground">mm</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No dimensions extracted</p>
                  )}
                </TabsContent>

                <TabsContent value="mounting" className="mt-4">
                  {extractedSpecs.mounting_holes && extractedSpecs.mounting_holes.length > 0 ? (
                    <div className="space-y-4">
                      {extractedSpecs.mounting_holes.map((hole, index) => (
                        <div key={index} className="flex items-center space-x-4 p-3 bg-muted rounded-lg">
                          <span className="font-mono text-sm">#{index + 1}</span>
                          <div className="flex items-center space-x-2">
                            <span className="text-muted-foreground">X:</span>
                            <Input
                              type="number"
                              value={hole.x}
                              className="w-20"
                              disabled={!isEditing}
                            />
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-muted-foreground">Y:</span>
                            <Input
                              type="number"
                              value={hole.y}
                              className="w-20"
                              disabled={!isEditing}
                            />
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-muted-foreground">Ø:</span>
                            <Input
                              type="number"
                              value={hole.diameter}
                              className="w-20"
                              disabled={!isEditing}
                            />
                          </div>
                          {hole.type && <Badge variant="outline">{hole.type}</Badge>}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No mounting holes extracted</p>
                  )}
                </TabsContent>

                <TabsContent value="connectors" className="mt-4">
                  {extractedSpecs.connectors && extractedSpecs.connectors.length > 0 ? (
                    <div className="space-y-3">
                      {extractedSpecs.connectors.map((conn, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                          <div className="flex items-center space-x-3">
                            <span className="font-medium">{conn.name}</span>
                            <Badge variant="secondary">{conn.type}</Badge>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {conn.width}×{conn.height}mm @ ({conn.x}, {conn.y}) - {conn.side}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No connectors extracted</p>
                  )}
                </TabsContent>

                <TabsContent value="clearance" className="mt-4">
                  {extractedSpecs.clearance_zones && extractedSpecs.clearance_zones.length > 0 ? (
                    <div className="space-y-3">
                      {extractedSpecs.clearance_zones.map((zone, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                          <span className="font-medium">{zone.name}</span>
                          <div className="text-sm text-muted-foreground">
                            {zone.width}×{zone.height}×{zone.z_height}mm - {zone.side}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No clearance zones extracted</p>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
            <CardFooter className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setIsEditing(!isEditing)}
              >
                {isEditing ? (
                  <>
                    <X className="h-4 w-4 mr-2" />
                    Cancel Edit
                  </>
                ) : (
                  <>
                    <Edit2 className="h-4 w-4 mr-2" />
                    Edit Specifications
                  </>
                )}
              </Button>
              <div className="flex space-x-2">
                <Button variant="outline" onClick={handleReset}>
                  Start Over
                </Button>
                <Button onClick={handleSave} disabled={saveMutation.isPending}>
                  {saveMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4 mr-2" />
                  )}
                  Save Component
                </Button>
              </div>
            </CardFooter>
          </Card>
        </div>
      )}

      {step === 'complete' && (
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center space-y-6">
              <div className="rounded-full bg-green-100 p-4">
                <CheckCircle className="h-16 w-16 text-green-600" />
              </div>
              <div className="text-center">
                <h3 className="text-xl font-semibold">Component Added!</h3>
                <p className="text-muted-foreground mt-1">
                  Your component has been saved to your library.
                </p>
              </div>
              <div className="flex space-x-4">
                <Button variant="outline" onClick={handleReset}>
                  Upload Another
                </Button>
                <Button onClick={() => window.location.href = '/components'}>
                  View Library
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default ComponentUploadPage;
