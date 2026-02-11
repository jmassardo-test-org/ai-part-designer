# Interactive Part Selection & Movement

## Overview

The Interactive Assembly Viewer provides powerful 3D part manipulation capabilities with intuitive transform controls, snapping, and full undo/redo support.

## Features

### Part Selection
- **Click to select**: Click any part in the 3D viewer to select it
- **Visual feedback**: Selected parts are highlighted in blue with an outline
- **Hover effects**: Cursor changes to pointer when hovering over parts
- **Part labels**: Selected parts show name and quantity labels

### Transform Controls
- **Move mode (G)**: Translate parts in 3D space
- **Rotate mode (R)**: Rotate parts around their center
- **Interactive gizmos**: Visual transform controls with colored axes
- **Constrained movement**: Drag along individual axes or planes

### Snapping (S)
- **Position snapping**: Snap to grid when moving (default: 5 units)
- **Rotation snapping**: Snap to angles when rotating (default: 15°)
- **Toggle on/off**: Press 'S' or click the grid icon

### Undo/Redo
- **Full history**: All transforms are recorded
- **Keyboard shortcuts**: Ctrl+Z to undo, Ctrl+Y (or Ctrl+Shift+Z) to redo
- **UI buttons**: Undo/redo buttons with tooltips showing next action
- **State preservation**: History survives component re-renders

### Additional Controls
- **Exploded view**: View parts separated for better visibility
- **Component list**: Toggle sidebar showing all parts
- **Hide/show parts**: Toggle visibility of individual components
- **Camera reset**: Reset view to default position

## Usage

### Basic Usage

```tsx
import { InteractiveAssemblyViewer } from '@/components/assembly';

function MyAssembly() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  
  const components = [
    {
      id: 'part-1',
      name: 'Base Plate',
      quantity: 1,
      position: { x: 0, y: 0, z: 0 },
      rotation: { rx: 0, ry: 0, rz: 0 },
      scale: { sx: 1, sy: 1, sz: 1 },
      is_cots: false,
      color: '#3b82f6',
      file_url: '/models/base-plate.stl',
    },
    // ... more components
  ];

  return (
    <InteractiveAssemblyViewer
      components={components}
      selectedComponentId={selectedId}
      onSelectComponent={setSelectedId}
      onComponentTransform={(id, transform) => {
        console.log(`Part ${id} moved to`, transform.position);
      }}
    />
  );
}
```

### Advanced Usage with External State

```tsx
import { InteractiveAssemblyViewer } from '@/components/assembly';

function AdvancedAssembly() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hiddenParts, setHiddenParts] = useState(new Set<string>());
  const [explodeFactor, setExplodeFactor] = useState(0);

  return (
    <InteractiveAssemblyViewer
      components={components}
      selectedComponentId={selectedId}
      onSelectComponent={setSelectedId}
      hiddenComponents={hiddenParts}
      explodeFactor={explodeFactor}
      onComponentTransform={async (id, transform) => {
        // Save to backend
        await updatePartPosition(id, transform);
      }}
    />
  );
}
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `G` | Switch to Move mode |
| `R` | Switch to Rotate mode |
| `S` | Toggle snapping on/off |
| `Ctrl+Z` | Undo last transform |
| `Ctrl+Y` | Redo last undone transform |
| `Ctrl+Shift+Z` | Redo (alternative) |

## Props

### InteractiveAssemblyViewer

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `components` | `AssemblyComponent[]` | required | Array of parts to display |
| `selectedComponentId` | `string \| null` | `null` | ID of currently selected part |
| `onSelectComponent` | `(id: string \| null) => void` | - | Callback when part is selected |
| `onComponentTransform` | `(id: string, transform: PartTransform) => void` | - | Callback when part is moved/rotated |
| `explodedView` | `boolean` | `false` | Enable exploded view |
| `explodeFactor` | `number` | `0` | Exploded view distance factor |
| `hiddenComponents` | `Set<string>` | `new Set()` | Set of hidden part IDs |
| `className` | `string` | `''` | Additional CSS classes |

### AssemblyComponent

```typescript
interface AssemblyComponent {
  id: string;                // Unique identifier
  name: string;              // Display name
  quantity: number;          // Number of instances
  position: {                // Position in 3D space
    x: number;
    y: number;
    z: number;
  };
  rotation: {                // Rotation in degrees
    rx: number;
    ry: number;
    rz: number;
  };
  scale: {                   // Scale factors
    sx: number;
    sy: number;
    sz: number;
  };
  is_cots: boolean;          // Is Commercial Off-The-Shelf
  color?: string;            // Custom color (hex)
  file_url?: string;         // STL file URL
  design_id?: string;        // Reference to design
  thumbnail_url?: string;    // Preview image URL
}
```

### PartTransform

```typescript
interface PartTransform {
  position: { x: number; y: number; z: number };
  rotation: { rx: number; ry: number; rz: number };
  scale: { sx: number; sy: number; sz: number };
}
```

## Custom Hooks

### usePartTransforms

Manages part transformations with undo/redo support.

```typescript
const {
  transforms,           // Current transform state
  updateTransform,      // Update a part's transform
  resetTransform,       // Reset a part to original position
  resetAllTransforms,   // Reset all parts
  canUndo,             // Can undo?
  canRedo,             // Can redo?
  undo,                // Undo last change
  redo,                // Redo last undo
  undoDescription,     // Description of next undo
  redoDescription,     // Description of next redo
  clearHistory,        // Clear history
} = usePartTransforms({
  initialTransforms: {},
  onTransformUpdate: (partId, transform) => {
    // Handle transform update
  },
  maxHistory: 50,
});
```

## Components

### PartTransformControls

Low-level transform controls component.

```typescript
<PartTransformControls
  object={meshObject}
  mode="translate"
  enablePositionSnap={true}
  positionSnapIncrement={5}
  enableRotationSnap={true}
  rotationSnapIncrement={15}
  onTransformChange={(transform) => {
    // Real-time updates during drag
  }}
  onTransformEnd={(transform) => {
    // Final transform when drag ends
  }}
  onDraggingChange={(isDragging) => {
    // Dragging state changed
  }}
/>
```

## Styling

The component uses Tailwind CSS and supports dark mode:

- Light mode: Light gray background, dark text
- Dark mode: Dark gray background, light text
- Selected parts: Blue highlight (#3b82f6)
- COTS parts: Gray color (#9ca3af)

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support (WebGL 2.0 required)
- Mobile: Limited support (touch controls not optimized)

## Performance Tips

1. **Limit components**: 50-100 parts max for smooth performance
2. **Use STL files wisely**: Keep models under 10MB
3. **Enable WebGL**: Ensure hardware acceleration is enabled
4. **Reduce polygon count**: Simplify complex models

## Troubleshooting

### Parts not visible
- Check `file_url` is accessible
- Verify STL file is valid
- Check browser console for errors

### Controls not responding
- Ensure part is selected
- Check if dragging is enabled
- Verify no overlay blocking clicks

### Poor performance
- Reduce number of parts
- Simplify STL models
- Check browser WebGL support

## Future Enhancements

- [ ] Scale mode support
- [ ] Multi-part selection
- [ ] Copy/paste parts
- [ ] Touch gesture support
- [ ] Collision detection
- [ ] Alignment guides
- [ ] Measurement tools during transform

## Related Documentation

- [AssemblyViewer](./AssemblyViewer.md) - Basic assembly viewer
- [TransformControls](https://threejs.org/docs/#examples/en/controls/TransformControls) - Three.js docs
- [React Three Fiber](https://docs.pmnd.rs/react-three-fiber) - R3F documentation
