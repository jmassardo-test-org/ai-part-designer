/**
 * Measurement Tool for 3D viewer.
 *
 * Provides point-to-point distance, edge length, face area,
 * and angle measurement capabilities.
 */

import { Html } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import { Ruler, Trash2, Download, CornerDownRight } from 'lucide-react';
import { useRef, useState, useCallback, useEffect } from 'react';
import * as THREE from 'three';

export type MeasurementType = 'distance' | 'angle' | 'edge' | 'area';

export interface Measurement {
  id: string;
  type: MeasurementType;
  points: THREE.Vector3[];
  value: number;
  unit: string;
  label: string;
}

interface MeasurementToolProps {
  /** Whether measurement mode is active */
  enabled: boolean;
  /** Current measurement type */
  measurementType: MeasurementType;
  /** Callback when measurement is completed */
  onMeasurementComplete?: (measurement: Measurement) => void;
  /** Unit for measurements (mm, cm, m, in) */
  unit?: 'mm' | 'cm' | 'm' | 'in';
  /** Line color for measurements */
  lineColor?: string;
  /** Label color for measurements */
  labelColor?: string;
}

interface MeasurementLineProps {
  measurement: Measurement;
  lineColor: string;
  labelColor: string;
  onDelete?: (id: string) => void;
}

const UNIT_FACTORS: Record<string, number> = {
  mm: 1,
  cm: 10,
  m: 1000,
  in: 25.4,
};

/**
 * Format measurement value with appropriate precision.
 */
function formatValue(value: number, unit: string): string {
  const converted = value / UNIT_FACTORS[unit];
  if (unit === 'm') {
    return converted.toFixed(3);
  }
  return converted.toFixed(2);
}

/**
 * Generate a unique ID for measurements.
 */
function generateId(): string {
  return `measurement-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Calculate angle between three points (in degrees).
 */
function calculateAngle(p1: THREE.Vector3, vertex: THREE.Vector3, p2: THREE.Vector3): number {
  const v1 = new THREE.Vector3().subVectors(p1, vertex).normalize();
  const v2 = new THREE.Vector3().subVectors(p2, vertex).normalize();
  const angle = Math.acos(Math.max(-1, Math.min(1, v1.dot(v2))));
  return THREE.MathUtils.radToDeg(angle);
}

/**
 * Calculate area of a triangle defined by three points.
 */
function calculateTriangleArea(p1: THREE.Vector3, p2: THREE.Vector3, p3: THREE.Vector3): number {
  const v1 = new THREE.Vector3().subVectors(p2, p1);
  const v2 = new THREE.Vector3().subVectors(p3, p1);
  const cross = new THREE.Vector3().crossVectors(v1, v2);
  return cross.length() / 2;
}

/**
 * Component to render a single measurement line with label.
 */
function MeasurementLine({ measurement, lineColor, labelColor }: MeasurementLineProps) {
  const { points, value, unit, type } = measurement;
  
  if (points.length < 2) return null;

  const midpoint = new THREE.Vector3();
  if (type === 'angle' && points.length === 3) {
    // For angles, position label near the vertex
    midpoint.copy(points[1]);
  } else {
    // For distance, position at midpoint
    midpoint.addVectors(points[0], points[1]).multiplyScalar(0.5);
  }

  // Create line geometry
  const linePoints = type === 'angle' && points.length === 3
    ? [points[0], points[1], points[2]]
    : [points[0], points[1]];

  return (
    <group>
      {/* Measurement line */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={linePoints.length}
            array={new Float32Array(linePoints.flatMap(p => [p.x, p.y, p.z]))}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color={lineColor} linewidth={2} />
      </line>

      {/* Point markers */}
      {points.map((point, index) => (
        <mesh key={index} position={point}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial color={lineColor} />
        </mesh>
      ))}

      {/* Measurement label */}
      <Html position={midpoint} center>
        <div
          className="px-2 py-1 rounded text-xs font-medium whitespace-nowrap pointer-events-none"
          style={{
            backgroundColor: labelColor,
            color: 'white',
            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
          }}
        >
          {type === 'angle' ? (
            <span>{value.toFixed(1)}°</span>
          ) : type === 'area' ? (
            <span>{formatValue(value, unit)} {unit}²</span>
          ) : (
            <span>{formatValue(value, unit)} {unit}</span>
          )}
        </div>
      </Html>
    </group>
  );
}

/**
 * Raycasting interaction handler for measurement picking.
 */
function MeasurementPicker({
  enabled,
  measurementType,
  onMeasurementComplete,
  unit = 'mm',
}: MeasurementToolProps) {
  const { camera, scene, gl } = useThree();
  const [pickingPoints, setPickingPoints] = useState<THREE.Vector3[]>([]);
  const raycaster = useRef(new THREE.Raycaster());
  const mouse = useRef(new THREE.Vector2());

  const requiredPoints = measurementType === 'angle' ? 3 : 
                         measurementType === 'area' ? 3 : 2;

  const handleClick = useCallback((event: MouseEvent) => {
    if (!enabled) return;

    const rect = gl.domElement.getBoundingClientRect();
    mouse.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.current.setFromCamera(mouse.current, camera);
    
    // Find intersections with meshes
    const meshes: THREE.Mesh[] = [];
    scene.traverse((obj) => {
      if (obj instanceof THREE.Mesh && obj.geometry) {
        meshes.push(obj);
      }
    });

    const intersects = raycaster.current.intersectObjects(meshes, true);
    
    if (intersects.length > 0) {
      const point = intersects[0].point.clone();
      const newPoints = [...pickingPoints, point];
      setPickingPoints(newPoints);

      if (newPoints.length >= requiredPoints) {
        // Complete measurement
        let value = 0;
        let label = '';

        switch (measurementType) {
          case 'distance':
          case 'edge':
            value = newPoints[0].distanceTo(newPoints[1]);
            label = `Distance: ${formatValue(value, unit)} ${unit}`;
            break;
          case 'angle':
            value = calculateAngle(newPoints[0], newPoints[1], newPoints[2]);
            label = `Angle: ${value.toFixed(1)}°`;
            break;
          case 'area':
            value = calculateTriangleArea(newPoints[0], newPoints[1], newPoints[2]);
            label = `Area: ${formatValue(value, unit)} ${unit}²`;
            break;
        }

        const measurement: Measurement = {
          id: generateId(),
          type: measurementType,
          points: newPoints,
          value,
          unit,
          label,
        };

        onMeasurementComplete?.(measurement);
        setPickingPoints([]);
      }
    }
  }, [enabled, pickingPoints, measurementType, camera, scene, gl, unit, requiredPoints, onMeasurementComplete]);

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

  // Reset picking points when measurement type changes
  useEffect(() => {
    setPickingPoints([]);
  }, [measurementType]);

  // Render preview points while picking
  return (
    <group>
      {pickingPoints.map((point, index) => (
        <mesh key={index} position={point}>
          <sphereGeometry args={[1.5, 16, 16]} />
          <meshBasicMaterial color="#ef4444" transparent opacity={0.8} />
        </mesh>
      ))}
      {pickingPoints.length === 2 && measurementType !== 'angle' && measurementType !== 'area' && (
        <line>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              count={2}
              array={new Float32Array([
                pickingPoints[0].x, pickingPoints[0].y, pickingPoints[0].z,
                pickingPoints[1].x, pickingPoints[1].y, pickingPoints[1].z,
              ])}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial color="#ef4444" linewidth={2} />
        </line>
      )}
    </group>
  );
}

/**
 * Measurement tool overlay that shows existing measurements.
 */
function MeasurementOverlay({
  measurements,
  lineColor = '#3b82f6',
  labelColor = '#1d4ed8',
}: {
  measurements: Measurement[];
  lineColor?: string;
  labelColor?: string;
}) {
  return (
    <group>
      {measurements.map((m) => (
        <MeasurementLine
          key={m.id}
          measurement={m}
          lineColor={lineColor}
          labelColor={labelColor}
        />
      ))}
    </group>
  );
}

interface MeasurementToolbarProps {
  enabled: boolean;
  onToggle: () => void;
  measurementType: MeasurementType;
  onTypeChange: (type: MeasurementType) => void;
  measurements: Measurement[];
  onClear: () => void;
  onExport: () => void;
  unit: 'mm' | 'cm' | 'm' | 'in';
  onUnitChange: (unit: 'mm' | 'cm' | 'm' | 'in') => void;
}

/**
 * UI toolbar for measurement controls.
 */
export function MeasurementToolbar({
  enabled,
  onToggle,
  measurementType,
  onTypeChange,
  measurements,
  onClear,
  onExport,
  unit,
  onUnitChange,
}: MeasurementToolbarProps) {
  return (
    <div className="flex flex-col gap-2 p-2 bg-white rounded-lg shadow-lg">
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className={`p-2 rounded-lg transition-colors ${
          enabled
            ? 'bg-blue-500 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
        }`}
        title={enabled ? 'Disable measurement' : 'Enable measurement'}
      >
        <Ruler className="h-5 w-5" />
      </button>

      {enabled && (
        <>
          {/* Measurement type buttons */}
          <div className="flex flex-col gap-1 border-t pt-2">
            <button
              onClick={() => onTypeChange('distance')}
              className={`px-3 py-1.5 text-xs rounded ${
                measurementType === 'distance'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
            >
              Distance
            </button>
            <button
              onClick={() => onTypeChange('angle')}
              className={`px-3 py-1.5 text-xs rounded flex items-center gap-1 ${
                measurementType === 'angle'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
            >
              <CornerDownRight className="h-3 w-3" />
              Angle
            </button>
            <button
              onClick={() => onTypeChange('area')}
              className={`px-3 py-1.5 text-xs rounded ${
                measurementType === 'area'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
            >
              Area
            </button>
          </div>

          {/* Unit selector */}
          <div className="border-t pt-2">
            <select
              value={unit}
              onChange={(e) => onUnitChange(e.target.value as 'mm' | 'cm' | 'm' | 'in')}
              className="w-full text-xs p-1.5 border rounded bg-white"
            >
              <option value="mm">mm</option>
              <option value="cm">cm</option>
              <option value="m">m</option>
              <option value="in">in</option>
            </select>
          </div>

          {/* Measurements count and actions */}
          {measurements.length > 0 && (
            <div className="border-t pt-2 space-y-1">
              <div className="text-xs text-gray-500 text-center">
                {measurements.length} measurement{measurements.length !== 1 ? 's' : ''}
              </div>
              <div className="flex gap-1">
                <button
                  onClick={onClear}
                  className="flex-1 p-1.5 text-xs bg-gray-50 text-gray-600 hover:bg-red-50 hover:text-red-600 rounded flex items-center justify-center gap-1"
                  title="Clear all measurements"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
                <button
                  onClick={onExport}
                  className="flex-1 p-1.5 text-xs bg-gray-50 text-gray-600 hover:bg-blue-50 hover:text-blue-600 rounded flex items-center justify-center gap-1"
                  title="Export measurements"
                >
                  <Download className="h-3 w-3" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Hook to manage measurements state.
 */
export function useMeasurements() {
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [measurementEnabled, setMeasurementEnabled] = useState(false);
  const [measurementType, setMeasurementType] = useState<MeasurementType>('distance');
  const [unit, setUnit] = useState<'mm' | 'cm' | 'm' | 'in'>('mm');

  const addMeasurement = useCallback((measurement: Measurement) => {
    setMeasurements((prev) => [...prev, measurement]);
  }, []);

  const removeMeasurement = useCallback((id: string) => {
    setMeasurements((prev) => prev.filter((m) => m.id !== id));
  }, []);

  const clearMeasurements = useCallback(() => {
    setMeasurements([]);
  }, []);

  const exportMeasurements = useCallback(() => {
    const data = measurements.map((m) => ({
      type: m.type,
      value: formatValue(m.value, unit),
      unit: m.type === 'angle' ? '°' : unit,
      label: m.label,
    }));

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `measurements-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [measurements, unit]);

  const toggleMeasurement = useCallback(() => {
    setMeasurementEnabled((prev) => !prev);
  }, []);

  return {
    measurements,
    measurementEnabled,
    measurementType,
    unit,
    addMeasurement,
    removeMeasurement,
    clearMeasurements,
    exportMeasurements,
    toggleMeasurement,
    setMeasurementType,
    setUnit,
  };
}

// Re-export components for use in viewer
export { MeasurementPicker, MeasurementOverlay };
export default MeasurementToolbar;
