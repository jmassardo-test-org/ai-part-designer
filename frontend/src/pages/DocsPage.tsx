/**
 * Documentation Page.
 * 
 * In-app documentation with Getting Started guide, template usage,
 * API documentation, and FAQ with search functionality.
 */

import {
  Search,
  ChevronRight,
  ChevronDown,
  Sparkles,
  FileCode,
  HelpCircle,
  Rocket,
  Layers,
  Download,
  Code,
  ExternalLink,
  Copy,
  Check,
} from 'lucide-react';
import { useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { LogoLight, LogoIcon } from '@/components/brand';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { cn } from '@/lib/utils';

// =============================
// Types
// =============================

interface DocSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

interface NavItem {
  id: string;
  title: string;
  icon: React.ReactNode;
  children?: { id: string; title: string }[];
}

// =============================
// Code Block Component
// =============================

interface CodeBlockProps {
  code: string;
  language?: string;
  title?: string;
}

function CodeBlock({ code, language = 'bash', title }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden border border-gray-700 my-4">
      {title && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
          <span className="text-sm text-gray-400">{title}</span>
          <button
            onClick={handleCopy}
            className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
            title="Copy to clipboard"
          >
            {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
          </button>
        </div>
      )}
      <pre className={cn('p-4 overflow-x-auto text-sm', !title && 'relative group')}>
        {!title && (
          <button
            onClick={handleCopy}
            className="absolute top-2 right-2 p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
            title="Copy to clipboard"
          >
            {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
          </button>
        )}
        <code className={`language-${language} text-gray-300`}>{code}</code>
      </pre>
    </div>
  );
}

// =============================
// Navigation Data
// =============================

const NAV_ITEMS: NavItem[] = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    icon: <Rocket className="h-4 w-4" />,
    children: [
      { id: 'introduction', title: 'Introduction' },
      { id: 'quick-start', title: 'Quick Start' },
      { id: 'first-part', title: 'Your First Part' },
    ],
  },
  {
    id: 'templates',
    title: 'Using Templates',
    icon: <Layers className="h-4 w-4" />,
    children: [
      { id: 'template-overview', title: 'Template Overview' },
      { id: 'template-parameters', title: 'Parameters' },
      { id: 'template-customization', title: 'Customization' },
    ],
  },
  {
    id: 'ai-generation',
    title: 'AI Generation',
    icon: <Sparkles className="h-4 w-4" />,
    children: [
      { id: 'prompts', title: 'Writing Prompts' },
      { id: 'refinement', title: 'Refining Results' },
      { id: 'best-practices', title: 'Best Practices' },
    ],
  },
  {
    id: 'exports',
    title: 'Exporting',
    icon: <Download className="h-4 w-4" />,
    children: [
      { id: 'export-formats', title: 'File Formats' },
      { id: 'export-settings', title: 'Export Settings' },
    ],
  },
  {
    id: 'api',
    title: 'API Reference',
    icon: <Code className="h-4 w-4" />,
    children: [
      { id: 'api-overview', title: 'Overview' },
      { id: 'api-authentication', title: 'Authentication' },
      { id: 'api-endpoints', title: 'Endpoints' },
    ],
  },
  {
    id: 'faq',
    title: 'FAQ',
    icon: <HelpCircle className="h-4 w-4" />,
  },
];

// =============================
// Documentation Content
// =============================

const GettingStartedContent = () => (
  <div className="space-y-8">
    <section id="introduction">
      <h2 className="text-2xl font-bold text-white mb-4">Introduction</h2>
      <p className="text-gray-400 mb-4">
        AssemblematicAI is an AI-powered CAD generation platform that lets you create 
        production-ready 3D parts using natural language. Simply describe what you need, 
        and our AI will generate precise CAD models that you can export for manufacturing.
      </p>
      <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-4">
        <h4 className="font-medium text-cyan-400 mb-2">Key Features</h4>
        <ul className="list-disc list-inside text-gray-400 space-y-1">
          <li>Natural language part generation</li>
          <li>Pre-built parametric templates</li>
          <li>Real-time 3D preview</li>
          <li>STEP and STL export</li>
          <li>Version history and collaboration</li>
        </ul>
      </div>
    </section>

    <section id="quick-start">
      <h2 className="text-2xl font-bold text-white mb-4">Quick Start</h2>
      <ol className="list-decimal list-inside text-gray-400 space-y-4">
        <li>
          <strong className="text-white">Create an account</strong> - Sign up for free at{' '}
          <Link to="/register" className="text-cyan-400 hover:underline">
            assemblematicai.com/register
          </Link>
        </li>
        <li>
          <strong className="text-white">Choose a template</strong> - Browse our template library 
          or start with a blank canvas
        </li>
        <li>
          <strong className="text-white">Describe your part</strong> - Use natural language or 
          adjust template parameters
        </li>
        <li>
          <strong className="text-white">Preview and refine</strong> - View your part in 3D and 
          make adjustments
        </li>
        <li>
          <strong className="text-white">Export</strong> - Download STEP or STL files for 
          manufacturing
        </li>
      </ol>
    </section>

    <section id="first-part">
      <h2 className="text-2xl font-bold text-white mb-4">Your First Part</h2>
      <p className="text-gray-400 mb-4">
        Let's create a simple mounting bracket to get you familiar with the platform:
      </p>
      <CodeBlock
        title="Example Prompt"
        code={`Create a mounting bracket with:
- Base plate: 100mm x 60mm x 5mm
- Two 8mm mounting holes, 80mm apart
- 45-degree support flange, 30mm tall
- M6 threaded insert hole in the flange`}
        language="text"
      />
      <p className="text-gray-400 mt-4">
        The AI will analyze your requirements and generate a precise CadQuery model. You can then 
        preview it in 3D, make adjustments, and export when ready.
      </p>
    </section>
  </div>
);

const TemplatesContent = () => (
  <div className="space-y-8">
    <section id="template-overview">
      <h2 className="text-2xl font-bold text-white mb-4">Template Overview</h2>
      <p className="text-gray-400 mb-4">
        Templates are pre-built parametric designs that you can customize for your specific needs. 
        They're perfect for common parts like enclosures, brackets, and mounting plates.
      </p>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          <h4 className="font-medium text-white mb-2">Benefits</h4>
          <ul className="list-disc list-inside text-gray-400 text-sm space-y-1">
            <li>Faster than starting from scratch</li>
            <li>Guaranteed manufacturable designs</li>
            <li>Professional engineering standards</li>
            <li>Extensive parameter options</li>
          </ul>
        </div>
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          <h4 className="font-medium text-white mb-2">Available Templates</h4>
          <ul className="list-disc list-inside text-gray-400 text-sm space-y-1">
            <li>Enclosures (electronics, project boxes)</li>
            <li>Brackets (L, U, corner, mounting)</li>
            <li>Flanges and adapters</li>
            <li>Spacers and standoffs</li>
          </ul>
        </div>
      </div>
    </section>

    <section id="template-parameters">
      <h2 className="text-2xl font-bold text-white mb-4">Parameters</h2>
      <p className="text-gray-400 mb-4">
        Each template has customizable parameters. Common parameter types include:
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left py-2 text-gray-400">Type</th>
            <th className="text-left py-2 text-gray-400">Description</th>
            <th className="text-left py-2 text-gray-400">Example</th>
          </tr>
        </thead>
        <tbody className="text-gray-400">
          <tr className="border-b border-gray-800">
            <td className="py-2 text-white">Dimensions</td>
            <td>Length, width, height, thickness</td>
            <td>100mm, 50mm, 25mm</td>
          </tr>
          <tr className="border-b border-gray-800">
            <td className="py-2 text-white">Holes</td>
            <td>Diameter, depth, pattern</td>
            <td>M6, through-hole, 4x grid</td>
          </tr>
          <tr className="border-b border-gray-800">
            <td className="py-2 text-white">Features</td>
            <td>Fillets, chamfers, ribs</td>
            <td>2mm fillet, 45° chamfer</td>
          </tr>
          <tr>
            <td className="py-2 text-white">Boolean</td>
            <td>Enable/disable features</td>
            <td>Include lid, add vents</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section id="template-customization">
      <h2 className="text-2xl font-bold text-white mb-4">Customization</h2>
      <p className="text-gray-400 mb-4">
        After generating from a template, you can further customize using AI:
      </p>
      <CodeBlock
        title="Customization Example"
        code={`# Start with a template, then refine:
"Add ventilation slots on the top surface"
"Round all corners with 3mm radius"
"Add mounting tabs on each side"`}
        language="text"
      />
    </section>
  </div>
);

const AIGenerationContent = () => (
  <div className="space-y-8">
    <section id="prompts">
      <h2 className="text-2xl font-bold text-white mb-4">Writing Effective Prompts</h2>
      <p className="text-gray-400 mb-4">
        The quality of your generated part depends on how well you describe it. 
        Here are tips for writing effective prompts:
      </p>
      
      <div className="space-y-4">
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
          <h4 className="font-medium text-green-400 mb-2">✓ Good Prompt</h4>
          <p className="text-gray-400 text-sm">
            "Create a rectangular enclosure 150mm x 100mm x 50mm with 3mm wall thickness. 
            Add a removable lid with 4 screw holes in the corners. Include ventilation slots 
            on both long sides."
          </p>
        </div>
        
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <h4 className="font-medium text-red-400 mb-2">✗ Vague Prompt</h4>
          <p className="text-gray-400 text-sm">
            "Make a box with a lid and some holes"
          </p>
        </div>
      </div>

      <h4 className="font-medium text-white mt-6 mb-2">Key Elements to Include</h4>
      <ul className="list-disc list-inside text-gray-400 space-y-1">
        <li><strong className="text-white">Dimensions:</strong> Specify exact sizes in mm</li>
        <li><strong className="text-white">Features:</strong> List holes, fillets, chamfers</li>
        <li><strong className="text-white">Relationships:</strong> Describe how parts connect</li>
        <li><strong className="text-white">Purpose:</strong> Mention the intended use</li>
      </ul>
    </section>

    <section id="refinement">
      <h2 className="text-2xl font-bold text-white mb-4">Refining Results</h2>
      <p className="text-gray-400 mb-4">
        After initial generation, you can refine the result using follow-up prompts:
      </p>
      <CodeBlock
        title="Refinement Commands"
        code={`# Modify dimensions
"Make it 20mm taller"
"Reduce the wall thickness to 2mm"

# Add features
"Add a cable routing channel on the bottom"
"Include standoffs for a PCB"

# Adjust details
"Increase the fillet radius to 5mm"
"Move the mounting holes 10mm inward"`}
        language="text"
      />
    </section>

    <section id="best-practices">
      <h2 className="text-2xl font-bold text-white mb-4">Best Practices</h2>
      <ul className="list-disc list-inside text-gray-400 space-y-2">
        <li>Start with a template when possible for faster results</li>
        <li>Use metric units (mm) for consistency</li>
        <li>Reference standard hole sizes (M3, M4, M6)</li>
        <li>Mention manufacturing method (3D printing, CNC) for optimized design</li>
        <li>Include tolerances for critical dimensions</li>
        <li>Break complex parts into simpler components</li>
      </ul>
    </section>
  </div>
);

const ExportsContent = () => (
  <div className="space-y-8">
    <section id="export-formats">
      <h2 className="text-2xl font-bold text-white mb-4">File Formats</h2>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <FileCode className="h-5 w-5 text-cyan-400" />
            <h4 className="font-medium text-white">STEP (.step, .stp)</h4>
          </div>
          <p className="text-gray-400 text-sm mb-2">
            Industry-standard format for CAD interchange. Best for:
          </p>
          <ul className="list-disc list-inside text-gray-400 text-sm space-y-1">
            <li>CNC machining</li>
            <li>Professional CAD software</li>
            <li>Manufacturing quotes</li>
            <li>Design collaboration</li>
          </ul>
        </div>
        
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="h-5 w-5 text-purple-400" />
            <h4 className="font-medium text-white">STL (.stl)</h4>
          </div>
          <p className="text-gray-400 text-sm mb-2">
            Mesh format for additive manufacturing. Best for:
          </p>
          <ul className="list-disc list-inside text-gray-400 text-sm space-y-1">
            <li>3D printing (FDM, SLA, SLS)</li>
            <li>Prototyping</li>
            <li>Mesh-based visualization</li>
            <li>Slicer software</li>
          </ul>
        </div>
      </div>
    </section>

    <section id="export-settings">
      <h2 className="text-2xl font-bold text-white mb-4">Export Settings</h2>
      <p className="text-gray-400 mb-4">
        Customize export quality based on your needs:
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left py-2 text-gray-400">Setting</th>
            <th className="text-left py-2 text-gray-400">Description</th>
            <th className="text-left py-2 text-gray-400">Recommended For</th>
          </tr>
        </thead>
        <tbody className="text-gray-400">
          <tr className="border-b border-gray-800">
            <td className="py-2 text-white">Draft Quality</td>
            <td>Fast export, larger file size</td>
            <td>Quick previews, iteration</td>
          </tr>
          <tr className="border-b border-gray-800">
            <td className="py-2 text-white">Standard Quality</td>
            <td>Balanced resolution</td>
            <td>Most 3D printing</td>
          </tr>
          <tr>
            <td className="py-2 text-white">High Quality</td>
            <td>Maximum precision</td>
            <td>CNC, professional manufacturing</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
);

const APIContent = () => (
  <div className="space-y-8">
    <section id="api-overview">
      <h2 className="text-2xl font-bold text-white mb-4">API Overview</h2>
      <p className="text-gray-400 mb-4">
        The AssemblematicAI API allows you to integrate part generation into your own applications. 
        Available on Pro and Enterprise plans.
      </p>
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
        <p className="text-gray-400 text-sm">
          <strong className="text-white">Base URL:</strong>{' '}
          <code className="bg-gray-900 px-2 py-1 rounded">https://api.assemblematicai.com/v1</code>
        </p>
      </div>
    </section>

    <section id="api-authentication">
      <h2 className="text-2xl font-bold text-white mb-4">Authentication</h2>
      <p className="text-gray-400 mb-4">
        All API requests require an API key in the Authorization header:
      </p>
      <CodeBlock
        title="Authentication Header"
        code={`curl -X GET "https://api.assemblematicai.com/v1/templates" \\
  -H "Authorization: Bearer YOUR_API_KEY"`}
        language="bash"
      />
      <p className="text-gray-400 mt-4">
        Generate API keys in your{' '}
        <Link to="/settings" className="text-cyan-400 hover:underline">
          account settings
        </Link>.
      </p>
    </section>

    <section id="api-endpoints">
      <h2 className="text-2xl font-bold text-white mb-4">Key Endpoints</h2>
      <div className="space-y-4">
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs font-medium rounded">GET</span>
            <code className="text-white">/templates</code>
          </div>
          <p className="text-gray-400 text-sm">List available templates</p>
        </div>
        
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs font-medium rounded">POST</span>
            <code className="text-white">/generate</code>
          </div>
          <p className="text-gray-400 text-sm">Generate a part from a prompt</p>
        </div>
        
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs font-medium rounded">GET</span>
            <code className="text-white">/designs/:id/export</code>
          </div>
          <p className="text-gray-400 text-sm">Export a design to STEP or STL</p>
        </div>
      </div>
      
      <p className="text-gray-400 mt-4">
        View the complete{' '}
        <a 
          href="/api/docs" 
          className="text-cyan-400 hover:underline inline-flex items-center gap-1"
          target="_blank"
        >
          API documentation <ExternalLink className="h-3 w-3" />
        </a>
      </p>
    </section>
  </div>
);

const FAQContent = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  
  const faqs = [
    {
      q: 'What is AssemblematicAI?',
      a: 'AssemblematicAI is an AI-powered CAD generation platform that creates production-ready 3D parts from natural language descriptions. It combines advanced language models with CadQuery to generate precise, manufacturable designs.',
    },
    {
      q: 'Do I need CAD experience to use it?',
      a: 'No! AssemblematicAI is designed for everyone, from hobbyists to professional engineers. Simply describe what you need in plain English, and our AI handles the technical details.',
    },
    {
      q: 'What file formats are supported?',
      a: 'We export to STEP (for CNC machining and professional CAD software) and STL (for 3D printing). Both formats are industry-standard and widely supported.',
    },
    {
      q: 'How accurate are the generated parts?',
      a: 'Generated parts are production-ready with precise dimensions. However, we recommend reviewing and validating designs before manufacturing, especially for critical applications.',
    },
    {
      q: 'Can I use the designs commercially?',
      a: 'Yes! You own all designs you create. They can be used for personal projects, commercial products, or client work.',
    },
    {
      q: 'Is my design data private?',
      a: 'Absolutely. Your designs are encrypted and never used to train AI models. See our Privacy Policy for complete details.',
    },
    {
      q: 'What happens if I exceed my monthly generation limit?',
      a: 'You can continue viewing and exporting existing designs. To generate new parts, wait for the next billing cycle or upgrade your plan.',
    },
    {
      q: 'How do I get support?',
      a: 'Contact us through the Contact page, email support@assemblematicai.com, or use the in-app help feature. Pro and Enterprise users get priority support.',
    },
  ];

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-white mb-6">Frequently Asked Questions</h2>
      {faqs.map((faq, index) => (
        <div
          key={index}
          className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden"
        >
          <button
            onClick={() => setOpenIndex(openIndex === index ? null : index)}
            className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-800/80 transition-colors"
          >
            <span className="font-medium text-white pr-4">{faq.q}</span>
            <ChevronDown
              className={cn(
                'h-5 w-5 text-gray-400 flex-shrink-0 transition-transform',
                openIndex === index && 'rotate-180'
              )}
            />
          </button>
          {openIndex === index && (
            <div className="px-4 pb-4">
              <p className="text-gray-400 text-sm leading-relaxed">{faq.a}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

// =============================
// Section Content Map
// =============================

const SECTION_CONTENT: Record<string, DocSection> = {
  'getting-started': {
    id: 'getting-started',
    title: 'Getting Started',
    icon: <Rocket className="h-5 w-5" />,
    content: <GettingStartedContent />,
  },
  'templates': {
    id: 'templates',
    title: 'Using Templates',
    icon: <Layers className="h-5 w-5" />,
    content: <TemplatesContent />,
  },
  'ai-generation': {
    id: 'ai-generation',
    title: 'AI Generation',
    icon: <Sparkles className="h-5 w-5" />,
    content: <AIGenerationContent />,
  },
  'exports': {
    id: 'exports',
    title: 'Exporting',
    icon: <Download className="h-5 w-5" />,
    content: <ExportsContent />,
  },
  'api': {
    id: 'api',
    title: 'API Reference',
    icon: <Code className="h-5 w-5" />,
    content: <APIContent />,
  },
  'faq': {
    id: 'faq',
    title: 'FAQ',
    icon: <HelpCircle className="h-5 w-5" />,
    content: <FAQContent />,
  },
};

// =============================
// Main Documentation Page
// =============================

export function DocsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedSections, setExpandedSections] = useState<string[]>(['getting-started']);

  const activeSection = searchParams.get('section') || 'getting-started';
  const currentSection = SECTION_CONTENT[activeSection] || SECTION_CONTENT['getting-started'];

  const handleNavClick = (sectionId: string) => {
    setSearchParams({ section: sectionId });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev =>
      prev.includes(sectionId)
        ? prev.filter(id => id !== sectionId)
        : [...prev, sectionId]
    );
  };

  // Filter nav items based on search
  const filteredNavItems = useMemo(() => {
    if (!searchQuery) return NAV_ITEMS;
    const query = searchQuery.toLowerCase();
    return NAV_ITEMS.filter(item => {
      const matchesTitle = item.title.toLowerCase().includes(query);
      const matchesChildren = item.children?.some(child =>
        child.title.toLowerCase().includes(query)
      );
      return matchesTitle || matchesChildren;
    });
  }, [searchQuery]);

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800 sticky top-0 bg-gray-900/95 backdrop-blur z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <Link to="/" className="flex items-center">
                <LogoLight size="md" />
              </Link>
              <span className="text-gray-600">|</span>
              <span className="text-gray-400 font-medium">Documentation</span>
            </div>

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

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-4 gap-8">
          {/* Sidebar Navigation */}
          <aside className="lg:col-span-1">
            <div className="sticky top-24">
              {/* Search */}
              <div className="relative mb-6">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search docs..."
                  className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                />
              </div>

              {/* Navigation */}
              <nav className="space-y-1">
                {filteredNavItems.map((item) => (
                  <div key={item.id}>
                    <button
                      onClick={() => {
                        if (item.children) {
                          toggleSection(item.id);
                        }
                        handleNavClick(item.id);
                      }}
                      className={cn(
                        'w-full flex items-center justify-between px-3 py-2 rounded-lg text-left transition-colors',
                        activeSection === item.id
                          ? 'bg-cyan-500/10 text-cyan-400'
                          : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                      )}
                    >
                      <span className="flex items-center gap-2">
                        {item.icon}
                        <span className="font-medium">{item.title}</span>
                      </span>
                      {item.children && (
                        <ChevronRight
                          className={cn(
                            'h-4 w-4 transition-transform',
                            expandedSections.includes(item.id) && 'rotate-90'
                          )}
                        />
                      )}
                    </button>

                    {/* Sub-navigation */}
                    {item.children && expandedSections.includes(item.id) && (
                      <div className="ml-6 mt-1 space-y-1">
                        {item.children.map((child) => (
                          <a
                            key={child.id}
                            href={`#${child.id}`}
                            className="block px-3 py-1.5 text-sm text-gray-500 hover:text-gray-300 transition-colors"
                          >
                            {child.title}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </nav>
            </div>
          </aside>

          {/* Content Area */}
          <main className="lg:col-span-3">
            <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-6 lg:p-8">
              <div className="flex items-center gap-3 mb-6 pb-6 border-b border-gray-700">
                <div className="w-10 h-10 bg-cyan-500/10 rounded-lg flex items-center justify-center text-cyan-400">
                  {currentSection.icon}
                </div>
                <h1 className="text-2xl font-bold text-white">{currentSection.title}</h1>
              </div>
              
              <div className="prose prose-invert max-w-none">
                {currentSection.content}
              </div>
            </div>

            {/* Navigation Footer */}
            <div className="flex justify-between mt-8 pt-8 border-t border-gray-800">
              <div>
                {/* Previous section logic could go here */}
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500 mb-1">Need help?</p>
                <Link to="/contact" className="text-cyan-400 hover:text-cyan-300">
                  Contact Support →
                </Link>
              </div>
            </div>
          </main>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-12 mt-8">
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

export default DocsPage;
