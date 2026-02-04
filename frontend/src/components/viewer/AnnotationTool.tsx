/**
 * 3D Annotations Tool for the CAD viewer.
 *
 * Allows users to click on the model to add annotations,
 * view annotation markers, and manage annotations.
 */

import { Html } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import {
  MessageCircle,
  HelpCircle,
  AlertCircle,
  CheckCircle,
  Lightbulb,
  Ruler,
  X,
  Plus,
  Filter,
  Check,
  Reply,
  Trash2,
} from 'lucide-react';
import { useRef, useState, useCallback, useEffect } from 'react';
import * as THREE from 'three';
import {
  ANNOTATION_TYPE_LABELS,
  ANNOTATION_TYPE_COLORS,
  PRIORITY_LABELS,
  PRIORITY_COLORS,
  type Annotation,
  type AnnotationType,
  type AnnotationStatus,
  type Position3D,
  type CreateAnnotationData,
} from '../../lib/api/annotations';

// --- Types ---

interface AnnotationMarkerProps {
  annotation: Annotation;
  isSelected: boolean;
  onClick: () => void;
}

interface AnnotationPickerProps {
  enabled: boolean;
  onPick: (position: Position3D, normal: Position3D | null) => void;
}

interface AnnotationFormProps {
  position: Position3D;
  onSubmit: (data: CreateAnnotationData) => void;
  onCancel: () => void;
  parentId?: string;
}

interface AnnotationDetailProps {
  annotation: Annotation;
  onClose: () => void;
  onResolve: () => void;
  onReopen: () => void;
  onDelete: () => void;
  onReply: () => void;
  replies: Annotation[];
}

interface AnnotationListPanelProps {
  annotations: Annotation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onFilterChange: (filter: AnnotationFilter) => void;
  filter: AnnotationFilter;
  onAddClick: () => void;
}

interface AnnotationFilter {
  type: AnnotationType | 'all';
  status: AnnotationStatus | 'all';
}

// --- Icon Mapping ---

const ANNOTATION_ICONS: Record<AnnotationType, typeof MessageCircle> = {
  note: MessageCircle,
  question: HelpCircle,
  issue: AlertCircle,
  approval: CheckCircle,
  suggestion: Lightbulb,
  dimension: Ruler,
};

// --- Components ---

/**
 * 3D marker for an annotation in the scene.
 */
function AnnotationMarker({ annotation, isSelected, onClick }: AnnotationMarkerProps) {
  const color = ANNOTATION_TYPE_COLORS[annotation.annotation_type];
  const Icon = ANNOTATION_ICONS[annotation.annotation_type];
  const position = new THREE.Vector3(
    annotation.position.x,
    annotation.position.y,
    annotation.position.z
  );

  return (
    <group position={position}>
      {/* Marker sphere */}
      <mesh onClick={(e) => { e.stopPropagation(); onClick(); }}>
        <sphereGeometry args={[2, 16, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={isSelected ? 1 : 0.8}
        />
      </mesh>

      {/* Selection ring */}
      {isSelected && (
        <mesh>
          <ringGeometry args={[3, 3.5, 32]} />
          <meshBasicMaterial color="#ffffff" side={THREE.DoubleSide} />
        </mesh>
      )}

      {/* Label */}
      <Html
        center
        style={{
          pointerEvents: 'auto',
          userSelect: 'none',
        }}
        distanceFactor={100}
      >
        <button
          onClick={(e) => { e.stopPropagation(); onClick(); }}
          className={`
            flex items-center gap-1 px-2 py-1 rounded-full text-white text-xs font-medium
            transition-transform hover:scale-110 cursor-pointer
            ${isSelected ? 'ring-2 ring-white' : ''}
          `}
          style={{ backgroundColor: color }}
        >
          <Icon className="h-3 w-3" />
          {annotation.reply_count > 0 && (
            <span className="bg-white/20 px-1 rounded-full text-[10px]">
              {annotation.reply_count}
            </span>
          )}
        </button>
      </Html>
    </group>
  );
}

/**
 * Raycasting picker for adding annotations.
 */
function AnnotationPicker({ enabled, onPick }: AnnotationPickerProps) {
  const { camera, scene, gl } = useThree();
  const raycaster = useRef(new THREE.Raycaster());
  const mouse = useRef(new THREE.Vector2());

  const handleClick = useCallback((event: MouseEvent) => {
    if (!enabled) return;

    const rect = gl.domElement.getBoundingClientRect();
    mouse.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.current.setFromCamera(mouse.current, camera);

    // Find meshes to intersect
    const meshes: THREE.Mesh[] = [];
    scene.traverse((obj) => {
      if (obj instanceof THREE.Mesh && obj.geometry && !obj.userData.isAnnotationMarker) {
        meshes.push(obj);
      }
    });

    const intersects = raycaster.current.intersectObjects(meshes, true);

    if (intersects.length > 0) {
      const hit = intersects[0];
      const position: Position3D = {
        x: hit.point.x,
        y: hit.point.y,
        z: hit.point.z,
      };
      const normal: Position3D | null = hit.face
        ? { x: hit.face.normal.x, y: hit.face.normal.y, z: hit.face.normal.z }
        : null;

      onPick(position, normal);
    }
  }, [enabled, camera, scene, gl, onPick]);

  useEffect(() => {
    if (enabled) {
      gl.domElement.addEventListener('click', handleClick);
      gl.domElement.style.cursor = 'crosshair';
    }

    return () => {
      gl.domElement.removeEventListener('click', handleClick);
      gl.domElement.style.cursor = 'default';
    };
  }, [enabled, handleClick, gl.domElement]);

  return null;
}

/**
 * Form for creating a new annotation.
 */
function AnnotationForm({ position, onSubmit, onCancel, parentId }: AnnotationFormProps) {
  const [content, setContent] = useState('');
  const [annotationType, setAnnotationType] = useState<AnnotationType>('note');
  const [priority, setPriority] = useState(0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    onSubmit({
      position,
      content: content.trim(),
      annotation_type: annotationType,
      priority,
      parent_id: parentId,
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-xl p-4 w-80">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-gray-900">
            {parentId ? 'Add Reply' : 'Add Annotation'}
          </h3>
          <button
            type="button"
            onClick={onCancel}
            className="p-1 text-gray-400 hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Type selector */}
        {!parentId && (
          <div className="mb-3">
            <label className="text-xs text-gray-500 mb-1 block">Type</label>
            <div className="grid grid-cols-3 gap-1">
              {(Object.keys(ANNOTATION_TYPE_LABELS) as AnnotationType[]).map((type) => {
                const Icon = ANNOTATION_ICONS[type];
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setAnnotationType(type)}
                    className={`
                      flex items-center gap-1 px-2 py-1.5 text-xs rounded
                      ${annotationType === type
                        ? 'text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}
                    `}
                    style={annotationType === type ? { backgroundColor: ANNOTATION_TYPE_COLORS[type] } : {}}
                  >
                    <Icon className="h-3 w-3" />
                    <span>{ANNOTATION_TYPE_LABELS[type]}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Content */}
        <div className="mb-3">
          <label className="text-xs text-gray-500 mb-1 block">Content</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Enter your annotation..."
            className="w-full px-3 py-2 border rounded-lg text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            rows={3}
            autoFocus
          />
        </div>

        {/* Priority */}
        {!parentId && (
          <div className="mb-4">
            <label className="text-xs text-gray-500 mb-1 block">Priority</label>
            <div className="flex gap-1">
              {[0, 1, 2, 3].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPriority(p)}
                  className={`
                    flex-1 px-2 py-1 text-xs rounded
                    ${priority === p ? 'text-white' : 'bg-gray-100 text-gray-600'}
                  `}
                  style={priority === p ? { backgroundColor: PRIORITY_COLORS[p] } : {}}
                >
                  {PRIORITY_LABELS[p]}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Submit */}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-3 py-2 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!content.trim()}
            className="flex-1 px-3 py-2 text-sm text-white bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg"
          >
            {parentId ? 'Reply' : 'Add'}
          </button>
        </div>
      </form>
    </div>
  );
}

/**
 * Detail view for a selected annotation.
 */
function AnnotationDetail({
  annotation,
  onClose,
  onResolve,
  onReopen,
  onDelete,
  onReply,
  replies,
}: AnnotationDetailProps) {
  const Icon = ANNOTATION_ICONS[annotation.annotation_type];
  const color = ANNOTATION_TYPE_COLORS[annotation.annotation_type];

  return (
    <div className="bg-white rounded-lg shadow-xl overflow-hidden w-80">
      {/* Header */}
      <div className="px-4 py-3 border-b flex items-center justify-between" style={{ backgroundColor: `${color}10` }}>
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-full" style={{ backgroundColor: color }}>
            <Icon className="h-4 w-4 text-white" />
          </div>
          <div>
            <div className="font-medium text-gray-900">
              {ANNOTATION_TYPE_LABELS[annotation.annotation_type]}
            </div>
            <div className="text-xs text-gray-500">
              by {annotation.user_name || 'Unknown'} • {new Date(annotation.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
        <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        <p className="text-sm text-gray-700 whitespace-pre-wrap">{annotation.content}</p>

        {/* Tags */}
        {annotation.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {annotation.tags.map((tag) => (
              <span key={tag} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-full">
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Status badge */}
        <div className="mt-3 flex items-center gap-2">
          <span
            className={`
              px-2 py-0.5 text-xs rounded-full
              ${annotation.is_resolved ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}
            `}
          >
            {annotation.is_resolved ? 'Resolved' : 'Open'}
          </span>
          <span
            className="px-2 py-0.5 text-xs rounded-full"
            style={{ backgroundColor: `${PRIORITY_COLORS[annotation.priority]}20`, color: PRIORITY_COLORS[annotation.priority] }}
          >
            {PRIORITY_LABELS[annotation.priority]}
          </span>
        </div>

        {/* Resolution note */}
        {annotation.resolution_note && (
          <div className="mt-3 p-2 bg-green-50 rounded text-xs text-green-700">
            <strong>Resolution:</strong> {annotation.resolution_note}
          </div>
        )}
      </div>

      {/* Replies */}
      {replies.length > 0 && (
        <div className="border-t">
          <div className="px-4 py-2 bg-gray-50 text-xs font-medium text-gray-500">
            {replies.length} {replies.length === 1 ? 'Reply' : 'Replies'}
          </div>
          <div className="max-h-48 overflow-y-auto">
            {replies.map((reply) => (
              <div key={reply.id} className="px-4 py-2 border-t">
                <div className="text-xs text-gray-500 mb-1">
                  {reply.user_name || 'Unknown'} • {new Date(reply.created_at).toLocaleDateString()}
                </div>
                <p className="text-sm text-gray-700">{reply.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-3 border-t bg-gray-50 flex gap-2">
        <button
          onClick={onReply}
          className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 text-xs text-gray-600 bg-white border rounded hover:bg-gray-50"
        >
          <Reply className="h-3 w-3" />
          Reply
        </button>
        {annotation.is_resolved ? (
          <button
            onClick={onReopen}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 text-xs text-yellow-600 bg-yellow-50 border border-yellow-200 rounded hover:bg-yellow-100"
          >
            Reopen
          </button>
        ) : (
          <button
            onClick={onResolve}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 text-xs text-green-600 bg-green-50 border border-green-200 rounded hover:bg-green-100"
          >
            <Check className="h-3 w-3" />
            Resolve
          </button>
        )}
        <button
          onClick={onDelete}
          className="px-3 py-1.5 text-xs text-red-600 bg-red-50 border border-red-200 rounded hover:bg-red-100"
        >
          <Trash2 className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

/**
 * Side panel showing list of annotations.
 */
export function AnnotationListPanel({
  annotations,
  selectedId,
  onSelect,
  onFilterChange,
  filter,
  onAddClick,
}: AnnotationListPanelProps) {
  const [showFilters, setShowFilters] = useState(false);

  const filteredAnnotations = annotations.filter((a) => {
    if (filter.type !== 'all' && a.annotation_type !== filter.type) return false;
    if (filter.status !== 'all') {
      if (filter.status === 'open' && a.is_resolved) return false;
      if (filter.status === 'resolved' && !a.is_resolved) return false;
    }
    return true;
  });

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden w-72">
      {/* Header */}
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <h3 className="font-medium text-gray-900">Annotations</h3>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-1.5 rounded ${showFilters ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
          >
            <Filter className="h-4 w-4" />
          </button>
          <button
            onClick={onAddClick}
            className="p-1.5 text-blue-500 hover:text-blue-600"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="px-4 py-2 border-b bg-gray-50 space-y-2">
          <div>
            <label className="text-[10px] text-gray-500 uppercase tracking-wide">Type</label>
            <select
              value={filter.type}
              onChange={(e) => onFilterChange({ ...filter, type: e.target.value as AnnotationType | 'all' })}
              className="w-full text-xs p-1.5 border rounded bg-white mt-1"
            >
              <option value="all">All Types</option>
              {(Object.keys(ANNOTATION_TYPE_LABELS) as AnnotationType[]).map((type) => (
                <option key={type} value={type}>{ANNOTATION_TYPE_LABELS[type]}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-gray-500 uppercase tracking-wide">Status</label>
            <select
              value={filter.status}
              onChange={(e) => onFilterChange({ ...filter, status: e.target.value as AnnotationStatus | 'all' })}
              className="w-full text-xs p-1.5 border rounded bg-white mt-1"
            >
              <option value="all">All</option>
              <option value="open">Open</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>
      )}

      {/* List */}
      <div className="max-h-96 overflow-y-auto">
        {filteredAnnotations.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">
            No annotations found
          </div>
        ) : (
          filteredAnnotations.map((annotation) => {
            const Icon = ANNOTATION_ICONS[annotation.annotation_type];
            const color = ANNOTATION_TYPE_COLORS[annotation.annotation_type];
            const isSelected = annotation.id === selectedId;

            return (
              <button
                key={annotation.id}
                onClick={() => onSelect(annotation.id)}
                className={`
                  w-full px-4 py-3 text-left border-b hover:bg-gray-50 transition-colors
                  ${isSelected ? 'bg-blue-50' : ''}
                `}
              >
                <div className="flex items-start gap-2">
                  <div
                    className="p-1 rounded-full flex-shrink-0 mt-0.5"
                    style={{ backgroundColor: `${color}20` }}
                  >
                    <Icon className="h-3 w-3" style={{ color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-700 truncate">{annotation.content}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-400">
                        {annotation.user_name || 'Unknown'}
                      </span>
                      {annotation.reply_count > 0 && (
                        <span className="text-xs text-gray-400">
                          • {annotation.reply_count} replies
                        </span>
                      )}
                    </div>
                  </div>
                  {annotation.is_resolved && (
                    <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                  )}
                </div>
              </button>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t bg-gray-50 text-xs text-gray-500 text-center">
        {filteredAnnotations.length} of {annotations.length} annotations
      </div>
    </div>
  );
}

/**
 * Hook to manage annotation state and interactions.
 */
export function useAnnotations(designId: string) {
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [selectedAnnotationId, setSelectedAnnotationId] = useState<string | null>(null);
  const [isAddingAnnotation, setIsAddingAnnotation] = useState(false);
  const [pendingPosition, setPendingPosition] = useState<Position3D | null>(null);
  const [filter, setFilter] = useState<AnnotationFilter>({ type: 'all', status: 'all' });
  const [replies, setReplies] = useState<Annotation[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const selectedAnnotation = annotations.find((a) => a.id === selectedAnnotationId) || null;

  const loadAnnotations = useCallback(async () => {
    setIsLoading(true);
    try {
      // In real implementation, call API
      // const response = await listAnnotations(designId);
      // setAnnotations(response.items);
    } catch (error) {
      console.error('Failed to load annotations:', error);
    } finally {
      setIsLoading(false);
    }
  }, [designId]);

  const loadReplies = useCallback(async (_annotationId: string) => {
    try {
      // In real implementation, call API
      // const data = await getAnnotationReplies(designId, _annotationId);
      // setReplies(data);
    } catch (error) {
      console.error('Failed to load replies:', error);
    }
  }, [designId]);

  const selectAnnotation = useCallback((id: string | null) => {
    setSelectedAnnotationId(id);
    if (id) {
      loadReplies(id);
    } else {
      setReplies([]);
    }
  }, [loadReplies]);

  const startAddingAnnotation = useCallback(() => {
    setIsAddingAnnotation(true);
    setSelectedAnnotationId(null);
  }, []);

  const cancelAddingAnnotation = useCallback(() => {
    setIsAddingAnnotation(false);
    setPendingPosition(null);
  }, []);

  const handlePick = useCallback((position: Position3D, _normal: Position3D | null) => {
    // Store position for annotation creation, normal reserved for future use
    setPendingPosition(position);
  }, []);

  const createAnnotation = useCallback(async (_data: CreateAnnotationData) => {
    try {
      // In real implementation, call API
      // const newAnnotation = await annotationsApi.createAnnotation(designId, _data);
      // setAnnotations((prev) => [newAnnotation, ...prev]);
      setIsAddingAnnotation(false);
      setPendingPosition(null);
    } catch (error) {
      console.error('Failed to create annotation:', error);
    }
  }, [designId]);

  const resolveAnnotation = useCallback(async (id: string) => {
    try {
      // In real implementation, call API
      // await annotationsApi.resolveAnnotation(designId, id);
      setAnnotations((prev) =>
        prev.map((a) => (a.id === id ? { ...a, is_resolved: true, status: 'resolved' as AnnotationStatus } : a))
      );
    } catch (error) {
      console.error('Failed to resolve annotation:', error);
    }
  }, [designId]);

  const reopenAnnotation = useCallback(async (id: string) => {
    try {
      // In real implementation, call API
      // await annotationsApi.reopenAnnotation(designId, id);
      setAnnotations((prev) =>
        prev.map((a) => (a.id === id ? { ...a, is_resolved: false, status: 'open' as AnnotationStatus } : a))
      );
    } catch (error) {
      console.error('Failed to reopen annotation:', error);
    }
  }, [designId]);

  const deleteAnnotation = useCallback(async (id: string) => {
    try {
      // In real implementation, call API
      // await annotationsApi.deleteAnnotation(designId, id);
      setAnnotations((prev) => prev.filter((a) => a.id !== id));
      setSelectedAnnotationId(null);
    } catch (error) {
      console.error('Failed to delete annotation:', error);
    }
  }, [designId]);

  useEffect(() => {
    loadAnnotations();
  }, [loadAnnotations]);

  return {
    annotations,
    selectedAnnotation,
    selectedAnnotationId,
    isAddingAnnotation,
    pendingPosition,
    filter,
    replies,
    isLoading,
    selectAnnotation,
    startAddingAnnotation,
    cancelAddingAnnotation,
    handlePick,
    createAnnotation,
    resolveAnnotation,
    reopenAnnotation,
    deleteAnnotation,
    setFilter,
  };
}

/**
 * Annotation markers overlay for the 3D scene.
 */
export function AnnotationMarkers({
  annotations,
  selectedId,
  onSelect,
}: {
  annotations: Annotation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  // Filter to only show root annotations (not replies)
  const rootAnnotations = annotations.filter((a) => !a.parent_id);

  return (
    <group>
      {rootAnnotations.map((annotation) => (
        <AnnotationMarker
          key={annotation.id}
          annotation={annotation}
          isSelected={annotation.id === selectedId}
          onClick={() => onSelect(annotation.id)}
        />
      ))}
    </group>
  );
}

// Export components
export { AnnotationPicker, AnnotationForm, AnnotationDetail };
export default AnnotationListPanel;
