/**
 * Demo Page.
 * 
 * Interactive demonstration of platform capabilities with
 * sample part generation walkthrough and 3D viewer.
 */

import {
  Play,
  Pause,
  RotateCcw,
  Sparkles,
  Layers,
  Download,
  ArrowRight,
  Check,
  ChevronRight,
  Cpu,
  Box,
  Settings2,
  Zap,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { LogoLight, LogoIcon } from '@/components/brand';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { cn } from '@/lib/utils';

// =============================
// Types
// =============================

interface DemoStep {
  id: number;
  title: string;
  description: string;
  prompt?: string;
  code?: string;
  visual: 'input' | 'processing' | 'preview' | 'export';
}

// =============================
// Demo Steps Data
// =============================

const DEMO_STEPS: DemoStep[] = [
  {
    id: 1,
    title: 'Describe Your Part',
    description: 'Use natural language to describe what you need. No CAD experience required.',
    prompt: 'Create a mounting bracket with:\n- Base plate 100x60x5mm\n- Two 8mm mounting holes\n- 45° support flange\n- M6 threaded insert hole',
    visual: 'input',
  },
  {
    id: 2,
    title: 'AI Processing',
    description: 'Our AI analyzes your requirements and generates precise CadQuery code.',
    code: `import cadquery as cq

# Create base plate
base = cq.Workplane("XY").box(100, 60, 5)

# Add mounting holes
base = base.faces(">Z").workplane()
base = base.pushPoints([(-35, 20), (35, 20)])
base = base.hole(8, depth=5)

# Add support flange at 45°
flange = cq.Workplane("XZ").transformed(
    rotate=(45, 0, 0)
).box(100, 30, 3)

# Add M6 threaded insert
result = base.union(flange)
result = result.faces(">Y").workplane()
result = result.hole(6, depth=10)`,
    visual: 'processing',
  },
  {
    id: 3,
    title: 'Preview in 3D',
    description: 'View your part from any angle. Rotate, zoom, and inspect every detail.',
    visual: 'preview',
  },
  {
    id: 4,
    title: 'Export & Manufacture',
    description: 'Download production-ready STEP or STL files for CNC machining or 3D printing.',
    visual: 'export',
  },
];

// =============================
// Demo Viewer Component
// =============================

interface DemoViewerProps {
  step: DemoStep;
  isAnimating: boolean;
}

function DemoViewer({ step, isAnimating }: DemoViewerProps) {
  const [typedText, setTypedText] = useState('');
  const [rotation, setRotation] = useState(0);

  // Typing animation for input step
  useEffect(() => {
    if (step.visual === 'input' && step.prompt && isAnimating) {
      setTypedText('');
      let index = 0;
      const interval = setInterval(() => {
        if (index < step.prompt!.length) {
          setTypedText(step.prompt!.slice(0, index + 1));
          index++;
        } else {
          clearInterval(interval);
        }
      }, 30);
      return () => clearInterval(interval);
    }
    if (step.visual === 'input' && step.prompt && !isAnimating) {
      setTypedText(step.prompt);
    }
  }, [step, isAnimating]);

  // Rotation animation for preview
  useEffect(() => {
    if (step.visual === 'preview' && isAnimating) {
      const interval = setInterval(() => {
        setRotation((r) => (r + 2) % 360);
      }, 50);
      return () => clearInterval(interval);
    }
  }, [step.visual, isAnimating]);

  return (
    <div className="relative w-full h-[400px] bg-gray-900 rounded-xl overflow-hidden border border-gray-700">
      {/* Input Visual */}
      {step.visual === 'input' && (
        <div className="absolute inset-0 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="h-5 w-5 text-cyan-400" />
            <span className="text-sm font-medium text-gray-400">AI Prompt</span>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 min-h-[200px]">
            <pre className="text-cyan-300 font-mono text-sm whitespace-pre-wrap">
              {typedText}
              {isAnimating && <span className="animate-pulse">|</span>}
            </pre>
          </div>
          <div className="absolute bottom-6 right-6">
            <button className="btn-primary btn-md opacity-80">
              Generate Part
              <ArrowRight className="ml-2 h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Processing Visual */}
      {step.visual === 'processing' && (
        <div className="absolute inset-0 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="h-5 w-5 text-purple-400" />
            <span className="text-sm font-medium text-gray-400">Generated CadQuery Code</span>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 overflow-auto max-h-[320px]">
            <pre className="text-green-300 font-mono text-xs">
              {step.code}
            </pre>
          </div>
          {isAnimating && (
            <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center">
              <div className="flex items-center gap-3 bg-gray-800 px-6 py-3 rounded-full border border-cyan-500/30">
                <div className="h-4 w-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                <span className="text-cyan-400 font-medium">Generating CAD model...</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Preview Visual - 3D Mockup */}
      {step.visual === 'preview' && (
        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800">
          <div
            className="relative"
            style={{ transform: `perspective(1000px) rotateY(${rotation}deg) rotateX(15deg)` }}
          >
            {/* Simple 3D bracket representation */}
            <div className="relative">
              {/* Base plate */}
              <div className="w-32 h-20 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-sm shadow-lg shadow-cyan-500/20 transform -skew-x-2">
                {/* Mounting holes */}
                <div className="absolute top-3 left-4 w-3 h-3 bg-gray-900 rounded-full" />
                <div className="absolute top-3 right-4 w-3 h-3 bg-gray-900 rounded-full" />
              </div>
              {/* Flange */}
              <div 
                className="absolute -top-8 left-0 w-32 h-8 bg-gradient-to-br from-cyan-400 to-cyan-500 rounded-sm shadow-lg origin-bottom"
                style={{ transform: 'rotateX(-45deg)' }}
              />
            </div>
          </div>
          {/* Controls overlay */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-4 bg-gray-800/80 px-4 py-2 rounded-full">
            <button className="p-1.5 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-white">
              <RotateCcw className="h-4 w-4" />
            </button>
            <span className="text-xs text-gray-500">Drag to rotate</span>
          </div>
        </div>
      )}

      {/* Export Visual */}
      {step.visual === 'export' && (
        <div className="absolute inset-0 p-6 flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Download className="h-5 w-5 text-green-400" />
            <span className="text-sm font-medium text-gray-400">Export Options</span>
          </div>
          <div className="flex-1 flex items-center justify-center">
            <div className="grid grid-cols-2 gap-4 max-w-sm w-full">
              <button className="bg-gray-800 border border-gray-700 hover:border-cyan-500 rounded-xl p-6 text-center transition-all group">
                <div className="w-12 h-12 bg-cyan-500/10 rounded-xl flex items-center justify-center mx-auto mb-3 group-hover:bg-cyan-500/20">
                  <Box className="h-6 w-6 text-cyan-400" />
                </div>
                <div className="font-semibold text-white mb-1">STEP File</div>
                <div className="text-xs text-gray-500">For CNC machining</div>
              </button>
              <button className="bg-gray-800 border border-gray-700 hover:border-purple-500 rounded-xl p-6 text-center transition-all group">
                <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center mx-auto mb-3 group-hover:bg-purple-500/20">
                  <Layers className="h-6 w-6 text-purple-400" />
                </div>
                <div className="font-semibold text-white mb-1">STL File</div>
                <div className="text-xs text-gray-500">For 3D printing</div>
              </button>
            </div>
          </div>
          <div className="flex justify-center">
            <div className="flex items-center gap-2 text-sm text-green-400">
              <Check className="h-4 w-4" />
              <span>Production-ready quality guaranteed</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================
// Feature Card Component
// =============================

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  color: 'cyan' | 'purple' | 'green' | 'orange';
}

function FeatureCard({ icon, title, description, color }: FeatureCardProps) {
  const colorClasses = {
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    orange: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:border-gray-600 transition-colors">
      <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center border mb-4', colorClasses[color])}>
        {icon}
      </div>
      <h3 className="font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-gray-400">{description}</p>
    </div>
  );
}

// =============================
// Main Demo Page Component
// =============================

export function DemoPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Auto-advance steps when playing
  useEffect(() => {
    if (isPlaying) {
      const timeout = setTimeout(() => {
        if (currentStep < DEMO_STEPS.length - 1) {
          setCurrentStep(currentStep + 1);
        } else {
          setIsPlaying(false);
        }
      }, 4000);
      return () => clearTimeout(timeout);
    }
  }, [isPlaying, currentStep]);

  const handlePlayPause = () => {
    if (!isPlaying && currentStep === DEMO_STEPS.length - 1) {
      setCurrentStep(0);
    }
    setIsPlaying(!isPlaying);
  };

  const handleStepClick = (index: number) => {
    setCurrentStep(index);
    setIsPlaying(false);
  };

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center">
              <LogoLight size="md" />
            </Link>

            <div className="flex items-center gap-4">
              <ThemeToggle size="sm" />
              <Link
                to="/login"
                className="text-gray-300 hover:text-white font-medium"
              >
                Sign in
              </Link>
              <Link to="/register" className="btn-primary btn-md">
                Get started
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-12 lg:py-16 border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/20 rounded-full px-4 py-1.5 mb-6">
              <Play className="h-4 w-4 text-cyan-400" />
              <span className="text-sm font-medium text-cyan-400">Interactive Demo</span>
            </div>
            <h1 className="text-4xl lg:text-5xl font-bold text-white leading-tight">
              See AI Part Design in Action
            </h1>
            <p className="mt-4 text-xl text-gray-400">
              Watch how our platform transforms natural language descriptions into
              production-ready CAD files in seconds.
            </p>
          </div>
        </div>
      </section>

      {/* Interactive Demo Section */}
      <section className="py-12 lg:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Step Navigator */}
            <div className="lg:col-span-1">
              <div className="sticky top-8 space-y-4">
                {/* Play/Pause Button */}
                <button
                  onClick={handlePlayPause}
                  className="w-full flex items-center justify-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white font-medium py-3 px-4 rounded-xl transition-colors"
                >
                  {isPlaying ? (
                    <>
                      <Pause className="h-5 w-5" />
                      Pause Demo
                    </>
                  ) : (
                    <>
                      <Play className="h-5 w-5" />
                      {currentStep === DEMO_STEPS.length - 1 ? 'Replay Demo' : 'Play Demo'}
                    </>
                  )}
                </button>

                {/* Step List */}
                <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
                  {DEMO_STEPS.map((step, index) => (
                    <button
                      key={step.id}
                      onClick={() => handleStepClick(index)}
                      className={cn(
                        'w-full flex items-start gap-3 p-4 text-left transition-all border-b border-gray-700 last:border-0',
                        currentStep === index
                          ? 'bg-cyan-500/10'
                          : 'hover:bg-gray-800'
                      )}
                    >
                      <div
                        className={cn(
                          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-medium text-sm',
                          currentStep === index
                            ? 'bg-cyan-500 text-white'
                            : currentStep > index
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-gray-700 text-gray-400'
                        )}
                      >
                        {currentStep > index ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          step.id
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div
                          className={cn(
                            'font-medium text-sm',
                            currentStep === index ? 'text-white' : 'text-gray-400'
                          )}
                        >
                          {step.title}
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                          {step.description}
                        </p>
                      </div>
                      <ChevronRight
                        className={cn(
                          'h-5 w-5 flex-shrink-0',
                          currentStep === index ? 'text-cyan-400' : 'text-gray-600'
                        )}
                      />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Demo Viewer */}
            <div className="lg:col-span-2">
              <DemoViewer step={DEMO_STEPS[currentStep]} isAnimating={isPlaying} />
              <div className="mt-4 text-center">
                <p className="text-gray-400">{DEMO_STEPS[currentStep].description}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Key Features Section */}
      <section className="py-12 lg:py-16 bg-gray-800/30 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white">Why Choose AssemblematicAI?</h2>
            <p className="mt-4 text-gray-400 max-w-2xl mx-auto">
              Our platform combines cutting-edge AI with professional CAD tools to deliver
              production-ready parts faster than ever.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <FeatureCard
              icon={<Sparkles className="h-5 w-5" />}
              title="Natural Language"
              description="Describe parts in plain English. No CAD experience needed."
              color="cyan"
            />
            <FeatureCard
              icon={<Zap className="h-5 w-5" />}
              title="Instant Generation"
              description="Get production-ready CAD files in seconds, not hours."
              color="purple"
            />
            <FeatureCard
              icon={<Settings2 className="h-5 w-5" />}
              title="Parametric Control"
              description="Fine-tune dimensions and features with precision."
              color="green"
            />
            <FeatureCard
              icon={<Download className="h-5 w-5" />}
              title="Export Anywhere"
              description="STEP for machining, STL for 3D printing, or both."
              color="orange"
            />
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-12 lg:py-16 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white">Built for Makers & Engineers</h2>
            <p className="mt-4 text-gray-400 max-w-2xl mx-auto">
              From hobbyists to professional engineers, our platform accelerates every stage of
              the design process.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-cyan-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Box className="h-8 w-8 text-cyan-400" />
              </div>
              <h3 className="font-semibold text-white mb-2">3D Printing Enthusiasts</h3>
              <p className="text-sm text-gray-400">
                Create custom brackets, enclosures, and fixtures for your projects without learning
                complex CAD software.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Settings2 className="h-8 w-8 text-purple-400" />
              </div>
              <h3 className="font-semibold text-white mb-2">Product Designers</h3>
              <p className="text-sm text-gray-400">
                Rapidly prototype ideas and iterate on designs. Export STEP files for manufacturer
                review.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-green-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Cpu className="h-8 w-8 text-green-400" />
              </div>
              <h3 className="font-semibold text-white mb-2">Hardware Engineers</h3>
              <p className="text-sm text-gray-400">
                Generate parametric parts with precise tolerances. Perfect for mechanical assemblies
                and tooling.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-12 lg:py-16 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-gradient-to-r from-cyan-600 to-blue-600 rounded-2xl p-12 text-center">
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to Start Designing?
            </h2>
            <p className="text-xl text-cyan-100 mb-8 max-w-2xl mx-auto">
              Create your free account and generate your first part in under 5 minutes.
              No credit card required.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register" className="btn bg-white text-cyan-600 hover:bg-gray-100 btn-lg">
                Create Free Account
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link to="/pricing" className="btn bg-white/10 text-white hover:bg-white/20 btn-lg border border-white/20">
                View Pricing
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center gap-2 mb-4 md:mb-0">
              <LogoIcon size={24} />
              <span className="font-semibold text-white">AssemblematicAI</span>
            </div>
            <div className="flex gap-6 text-sm text-gray-400">
              <Link to="/demo" className="hover:text-white">Demo</Link>
              <Link to="/pricing" className="hover:text-white">Pricing</Link>
              <Link to="/terms" className="hover:text-white">Terms</Link>
              <Link to="/privacy" className="hover:text-white">Privacy</Link>
              <Link to="/contact" className="hover:text-white">Contact</Link>
            </div>
          </div>
          <p className="mt-8 text-center text-sm text-gray-500">
            © 2026 AssemblematicAI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default DemoPage;
