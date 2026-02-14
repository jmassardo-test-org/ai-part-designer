/**
 * Assembly Page
 * 
 * View and edit assemblies with 3D viewer, component tree, and BOM.
 */

import {
  ChevronLeft,
  Plus,
  Loader2,
  AlertCircle,
  Package,
  DollarSign,
  Layers,
  Trash2,
  Save,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { AssemblyViewer, BOMTable } from '@/components/assembly';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

// =============================================================================
// Types
// =============================================================================

interface Position {
  x: number;
  y: number;
  z: number;
}

interface Rotation {
  rx: number;
  ry: number;
  rz: number;
}

interface Scale {
  sx: number;
  sy: number;
  sz: number;
}

interface Component {
  id: string;
  name: string;
  description: string | null;
  design_id: string | null;
  design_name: string | null;
  quantity: number;
  position: Position;
  rotation: Rotation;
  scale: Scale;
  is_cots: boolean;
  part_number: string | null;
  color: string | null;
  created_at: string;
  updated_at: string;
}

interface Relationship {
  id: string;
  parent_component_id: string;
  child_component_id: string;
  relationship_type: string;
  name: string | null;
  constraint_data: Record<string, unknown>;
  assembly_order: number | null;
}

interface Assembly {
  id: string;
  name: string;
  description: string | null;
  project_id: string;
  project_name: string;
  root_design_id: string | null;
  status: string;
  thumbnail_url: string | null;
  component_count: number;
  total_quantity: number;
  version: number;
  created_at: string;
  updated_at: string;
  components: Component[];
  relationships: Relationship[];
}

interface BOMItem {
  id: string;
  component_id: string;
  component_name: string;
  part_number: string | null;
  vendor_part_number: string | null;
  description: string;
  category: string;
  vendor_id: string | null;
  vendor_name: string | null;
  quantity: number;
  unit_cost: number | null;
  total_cost: number | null;
  currency: string;
  lead_time_days: number | null;
  minimum_order_quantity: number;
  in_stock: boolean | null;
  notes: string | null;
}

interface BOMSummary {
  total_items: number;
  total_quantity: number;
  total_cost: number | null;
  currency: string;
  categories: Record<string, number>;
  longest_lead_time: number | null;
}

interface BOMData {
  assembly_id: string;
  assembly_name: string;
  items: BOMItem[];
  summary: BOMSummary;
}

interface Vendor {
  id: string;
  name: string;
  display_name: string;
}

type TabType = 'viewer' | 'components' | 'bom';

// =============================================================================
// Component
// =============================================================================

export function AssemblyPage() {
  const { assemblyId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();

  // State
  const [assembly, setAssembly] = useState<Assembly | null>(null);
  const [bomData, setBomData] = useState<BOMData | null>(null);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('viewer');
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);

  // Edit state
  const [isEditingName, setIsEditingName] = useState(false);
  const [editName, setEditName] = useState('');

  // Fetch assembly
  const fetchAssembly = useCallback(async () => {
    if (!token || !assemblyId) return;

    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/assemblies/${assemblyId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Assembly not found');
        }
        throw new Error('Failed to load assembly');
      }

      const data = await response.json();
      setAssembly(data);
      setEditName(data.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assembly');
    } finally {
      setIsLoading(false);
    }
  }, [token, assemblyId]);

  // Fetch BOM
  const fetchBOM = useCallback(async () => {
    if (!token || !assemblyId) return;

    try {
      const response = await fetch(`${API_BASE}/assemblies/${assemblyId}/bom`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setBomData(data);
      }
    } catch (err) {
      console.error('Failed to load BOM:', err);
    }
  }, [token, assemblyId]);

  // Fetch vendors
  const fetchVendors = useCallback(async () => {
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/vendors`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setVendors(data);
      }
    } catch (err) {
      console.error('Failed to load vendors:', err);
    }
  }, [token]);

  // Load data on mount
  useEffect(() => {
    fetchAssembly();
    fetchBOM();
    fetchVendors();
  }, [fetchAssembly, fetchBOM, fetchVendors]);

  // Update assembly name
  const handleUpdateName = async () => {
    if (!token || !assembly || !editName.trim()) return;

    try {
      const response = await fetch(`${API_BASE}/assemblies/${assembly.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: editName.trim() }),
      });

      if (response.ok) {
        const updated = await response.json();
        setAssembly({ ...assembly, name: updated.name, version: updated.version });
        setIsEditingName(false);
      }
    } catch (err) {
      console.error('Failed to update name:', err);
    }
  };

  // Delete component
  const handleDeleteComponent = async (componentId: string) => {
    if (!token || !assembly) return;

    if (!confirm('Remove this component from the assembly?')) return;

    try {
      const response = await fetch(
        `${API_BASE}/assemblies/${assembly.id}/components/${componentId}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        fetchAssembly();
        if (selectedComponentId === componentId) {
          setSelectedComponentId(null);
        }
      }
    } catch (err) {
      console.error('Failed to delete component:', err);
    }
  };

  // Update BOM item
  const handleUpdateBOMItem = async (itemId: string, data: Partial<BOMItem>) => {
    if (!token || !assembly) return;

    try {
      const response = await fetch(`${API_BASE}/assemblies/${assembly.id}/bom/${itemId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        fetchBOM();
      }
    } catch (err) {
      console.error('Failed to update BOM item:', err);
    }
  };

  // Delete BOM item
  const handleDeleteBOMItem = async (itemId: string) => {
    if (!token || !assembly) return;

    if (!confirm('Remove this item from the BOM?')) return;

    try {
      const response = await fetch(`${API_BASE}/assemblies/${assembly.id}/bom/${itemId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchBOM();
      }
    } catch (err) {
      console.error('Failed to delete BOM item:', err);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  // Error state
  if (error || !assembly) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <p className="text-gray-600">{error || 'Assembly not found'}</p>
        <button
          onClick={() => navigate('/projects')}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          Back to Projects
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-white">
        <div className="flex items-center gap-4">
          <Link
            to={`/projects/${assembly.project_id}`}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <ChevronLeft className="w-5 h-5" />
          </Link>

          <div>
            {isEditingName ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="px-2 py-1 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleUpdateName();
                    if (e.key === 'Escape') {
                      setIsEditingName(false);
                      setEditName(assembly.name);
                    }
                  }}
                />
                <button onClick={handleUpdateName} className="p-1 text-green-600">
                  <Save className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <h1
                className="text-xl font-semibold text-gray-900 cursor-pointer hover:text-primary-600"
                onClick={() => setIsEditingName(true)}
              >
                {assembly.name}
              </h1>
            )}
            <p className="text-sm text-gray-500">
              {assembly.project_name} • v{assembly.version}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Stats */}
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span className="flex items-center gap-1">
              <Package className="w-4 h-4" />
              {assembly.component_count} components
            </span>
            <span className="flex items-center gap-1">
              <Layers className="w-4 h-4" />
              {assembly.total_quantity} parts
            </span>
            {bomData?.summary.total_cost && (
              <span className="flex items-center gap-1">
                <DollarSign className="w-4 h-4" />
                ${bomData.summary.total_cost.toFixed(2)}
              </span>
            )}
          </div>

          {/* Status badge */}
          <span
            className={`px-3 py-1 text-sm rounded-full ${
              assembly.status === 'complete'
                ? 'bg-green-100 text-green-700'
                : assembly.status === 'in_progress'
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-gray-100 text-gray-700'
            }`}
          >
            {assembly.status.replace('_', ' ')}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b bg-white">
        <button
          onClick={() => setActiveTab('viewer')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'viewer'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          3D Viewer
        </button>
        <button
          onClick={() => setActiveTab('components')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'components'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          Components ({assembly.component_count})
        </button>
        <button
          onClick={() => setActiveTab('bom')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'bom'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          Bill of Materials
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {/* 3D Viewer Tab */}
        {activeTab === 'viewer' && (
          <div className="h-full p-4">
            <AssemblyViewer
              components={assembly.components.map((c) => ({
                id: c.id,
                name: c.name,
                design_id: c.design_id || undefined,
                quantity: c.quantity,
                position: c.position,
                rotation: c.rotation,
                scale: c.scale,
                is_cots: c.is_cots,
                color: c.color || undefined,
              }))}
              selectedComponentId={selectedComponentId}
              onSelectComponent={setSelectedComponentId}
              assemblyId={assemblyId}
              className="h-full"
            />
          </div>
        )}

        {/* Components Tab */}
        {activeTab === 'components' && (
          <div className="h-full overflow-auto p-4">
            <div className="bg-white rounded-lg border">
              <div className="px-4 py-3 border-b flex items-center justify-between">
                <h3 className="font-medium">Components</h3>
                <button className="flex items-center gap-1 px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                  <Plus className="w-4 h-4" />
                  Add Component
                </button>
              </div>
              <div className="divide-y">
                {assembly.components.length === 0 ? (
                  <div className="px-4 py-8 text-center text-gray-500">
                    No components yet. Add designs to this assembly.
                  </div>
                ) : (
                  assembly.components.map((component) => (
                    <div
                      key={component.id}
                      className={`px-4 py-3 flex items-center justify-between hover:bg-gray-50 cursor-pointer ${
                        selectedComponentId === component.id ? 'bg-primary-50' : ''
                      }`}
                      onClick={() => setSelectedComponentId(component.id)}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className="w-4 h-4 rounded"
                          style={{ backgroundColor: component.color || '#6b7280' }}
                        />
                        <div>
                          <p className="font-medium text-gray-900">{component.name}</p>
                          <p className="text-sm text-gray-500">
                            {component.is_cots ? 'COTS Part' : component.design_name || 'Custom'}
                            {component.quantity > 1 && ` × ${component.quantity}`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {component.part_number && (
                          <span className="text-sm text-gray-500">{component.part_number}</span>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteComponent(component.id);
                          }}
                          className="p-1 text-gray-400 hover:text-red-600 rounded"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* BOM Tab */}
        {activeTab === 'bom' && bomData && (
          <div className="h-full overflow-auto p-4">
            <BOMTable
              assemblyId={assembly.id}
              items={bomData.items}
              summary={bomData.summary}
              vendors={vendors}
              onItemUpdate={handleUpdateBOMItem}
              onItemDelete={handleDeleteBOMItem}
              onRefresh={fetchBOM}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default AssemblyPage;
