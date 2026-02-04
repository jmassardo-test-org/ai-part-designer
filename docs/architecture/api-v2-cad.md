# CAD v2 API Reference

## Overview

The CAD v2 API provides a declarative schema-based approach to 3D enclosure generation.
It replaces the v1 natural language processing with a structured `EnclosureSpec` schema
that enables precise control over generated geometry.

## Base URL

```
/api/v2/
```

## Authentication

All endpoints support optional Bearer token authentication:

```http
Authorization: Bearer <jwt-token>
```

Authenticated requests enable:
- Job history tracking
- Save to project functionality
- WebSocket progress notifications

---

## Endpoints

### Generate from Description

Generate an enclosure from a natural language description.

```http
POST /api/v2/generate/
```

**Request Body:**

```json
{
  "description": "Create a box 100x80x50mm with snap-fit lid and ventilation",
  "export_format": "step"
}
```

**Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "generated_schema": {
    "exterior": {
      "width": {"value": 100, "unit": "mm"},
      "depth": {"value": 80, "unit": "mm"},
      "height": {"value": 50, "unit": "mm"}
    },
    "walls": {"thickness": {"value": 2, "unit": "mm"}},
    "corner_radius": {"value": 3, "unit": "mm"},
    "lid": {"type": "snap_fit", "side": "top"},
    "ventilation": {"enabled": true, "sides": ["left", "right"]}
  },
  "parts": ["body", "lid"],
  "downloads": {
    "body.step": "/api/v2/downloads/550e8400.../body.step",
    "lid.step": "/api/v2/downloads/550e8400.../lid.step"
  },
  "warnings": [],
  "errors": []
}
```

---

### Preview Schema

Generate schema from description without compiling geometry.

```http
POST /api/v2/generate/preview
```

**Request Body:**

```json
{
  "description": "Compact case for Arduino Nano with USB cutout"
}
```

**Response:**

```json
{
  "success": true,
  "generated_schema": {
    "exterior": {...},
    "walls": {...},
    "features": [
      {
        "type": "cutout",
        "subtype": "usb_micro",
        "face": "front",
        "position": {"x": 0, "y": 0}
      }
    ]
  },
  "validation_errors": [],
  "clarification_needed": null
}
```

---

### Compile Schema

Compile a complete EnclosureSpec to 3D geometry.

```http
POST /api/v2/generate/compile
```

**Request Body:**

```json
{
  "enclosure_schema": {
    "exterior": {
      "width": {"value": 120, "unit": "mm"},
      "depth": {"value": 80, "unit": "mm"},
      "height": {"value": 50, "unit": "mm"}
    },
    "walls": {"thickness": {"value": 2.5, "unit": "mm"}},
    "corner_radius": {"value": 5, "unit": "mm"},
    "lid": {
      "type": "snap_fit",
      "side": "top",
      "gap": {"value": 0.3, "unit": "mm"}
    },
    "ventilation": {
      "enabled": true,
      "sides": ["left", "right"],
      "pattern": "slots"
    }
  },
  "export_format": "step",
  "async_mode": false
}
```

**Sync Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "parts": ["body", "lid"],
  "files": ["body.step", "body.stl", "lid.step", "lid.stl"],
  "downloads": {
    "body.step": "/api/v2/downloads/550e8400.../body.step",
    "body.stl": "/api/v2/downloads/550e8400.../body.stl",
    "lid.step": "/api/v2/downloads/550e8400.../lid.step",
    "lid.stl": "/api/v2/downloads/550e8400.../lid.stl"
  },
  "errors": [],
  "warnings": [],
  "metadata": {
    "exterior": [120, 80, 50],
    "interior": [115, 75, 45],
    "wall_thickness": 2.5,
    "part_count": 2
  }
}
```

**Async Response (when `async_mode: true`):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Compilation queued as background job"
}
```

---

### Job Status

Get status of an async compilation job.

```http
GET /api/v2/generate/job/{job_id}/status
```

**Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "message": "Compilation complete",
  "files": ["body.step", "body.stl", "lid.step", "lid.stl"],
  "error": null
}
```

**Status Values:**
- `pending` - Job is queued
- `running` - Compilation in progress
- `completed` - Successfully completed
- `failed` - Compilation failed (see `error` field)

---

### Download File

Download a generated CAD file.

```http
GET /api/v2/downloads/{job_id}/{filename}
```

**Parameters:**
- `job_id` - The job ID from generation response
- `filename` - File to download (e.g., `body.step`, `lid.stl`)

**Response:**
Binary file with appropriate Content-Type header.

---

### List Job Files

List all files available for a job.

```http
GET /api/v2/downloads/{job_id}
```

**Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "files": [
    {"name": "body.step", "size": 45678, "format": "step"},
    {"name": "body.stl", "size": 123456, "format": "stl"},
    {"name": "lid.step", "size": 34567, "format": "step"},
    {"name": "lid.stl", "size": 98765, "format": "stl"}
  ]
}
```

---

### Save Design

Save a generated design to a project.

```http
POST /api/v2/designs/save
```

**Request Body:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Electronics Enclosure v1",
  "description": "Compact case for Arduino project",
  "project_id": "optional-project-uuid",
  "tags": ["arduino", "enclosure"]
}
```

**Response:**

```json
{
  "id": "design-uuid",
  "name": "Electronics Enclosure v1",
  "description": "Compact case for Arduino project",
  "project_id": "project-uuid",
  "project_name": "My Projects",
  "source_type": "cad_v2",
  "status": "completed",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "enclosure_spec": {...},
  "downloads": {
    "body.step": "/api/v2/downloads/...",
    "lid.step": "/api/v2/downloads/..."
  },
  "created_at": "2026-01-30T12:00:00Z"
}
```

---

### List Designs

List saved v2 designs.

```http
GET /api/v2/designs/
```

**Query Parameters:**
- `page` (default: 1)
- `per_page` (default: 20)

**Response:**

```json
{
  "designs": [...],
  "total": 15,
  "page": 1,
  "per_page": 20
}
```

---

### Get Design

Get a specific saved design.

```http
GET /api/v2/designs/{design_id}
```

---

## EnclosureSpec Schema

The core schema for defining enclosure geometry.

```typescript
interface EnclosureSpec {
  // Required: Exterior dimensions
  exterior: {
    width: Dimension;   // X axis
    depth: Dimension;   // Y axis
    height: Dimension;  // Z axis
  };

  // Optional: Wall configuration
  walls?: {
    thickness?: Dimension;  // Uniform thickness
    front?: Dimension;      // Per-face override
    back?: Dimension;
    left?: Dimension;
    right?: Dimension;
    top?: Dimension;
    bottom?: Dimension;
  };

  // Optional: Corner styling
  corner_radius?: Dimension;

  // Optional: Lid configuration
  lid?: {
    type: "snap_fit" | "screw_on" | "slide_on" | "friction" | "hinge" | "none";
    side?: "top" | "bottom" | "front" | "back" | "left" | "right";
    gap?: Dimension;
    separate_part?: boolean;
  };

  // Optional: Ventilation
  ventilation?: {
    enabled: boolean;
    sides?: WallSide[];
    pattern?: "slots" | "holes" | "honeycomb";
    slot_width?: Dimension;
    slot_length?: Dimension;
    slot_spacing?: Dimension;
    margin?: Dimension;
  };

  // Optional: Feature cutouts
  features?: Feature[];

  // Optional: Mounting options
  mounting_tabs?: {
    enabled: boolean;
    sides?: WallSide[];
    width?: Dimension;
    hole_diameter?: Dimension;
  };

  // Optional: Component mounts
  component_mounts?: ComponentMount[];

  // Optional: Custom metadata
  metadata?: Record<string, unknown>;
}

interface Dimension {
  value: number;
  unit?: "mm" | "in";  // Default: mm
}

type WallSide = "front" | "back" | "left" | "right" | "top" | "bottom";
```

---

## Feature Types

### Port Cutout

```json
{
  "type": "cutout",
  "subtype": "usb_c",
  "face": "back",
  "position": {"x": 0, "y": 5},
  "width": {"value": 9, "unit": "mm"},
  "height": {"value": 3.5, "unit": "mm"}
}
```

**Subtypes:** `usb_c`, `usb_a`, `usb_micro`, `hdmi`, `ethernet`, `power_jack`, `sd_card`, `audio`, `custom`

### Button Cutout

```json
{
  "type": "button",
  "face": "top",
  "position": {"x": 20, "y": 0},
  "diameter": {"value": 12, "unit": "mm"}
}
```

### Display Cutout

```json
{
  "type": "display",
  "subtype": "lcd_2004",
  "face": "front",
  "position": {"x": 0, "y": 0},
  "width": {"value": 98, "unit": "mm"},
  "height": {"value": 60, "unit": "mm"}
}
```

---

## Error Responses

### Validation Error

```json
{
  "detail": "Validation error",
  "errors": [
    {
      "loc": ["body", "exterior", "width", "value"],
      "msg": "Value must be greater than 0",
      "type": "value_error"
    }
  ]
}
```

### Compilation Error

```json
{
  "job_id": "...",
  "success": false,
  "parts": [],
  "files": [],
  "downloads": {},
  "errors": ["Wall thickness exceeds half of smallest dimension"],
  "warnings": []
}
```

---

## Deprecation Notice

The v1 CAD generation API (`/api/v1/generate`) is deprecated and routes through the v2 pipeline.
New integrations should use v2 endpoints directly.

**Deprecated:** `/api/v1/generate`  
**Replacement:** `/api/v2/generate/` or `/api/v2/generate/compile`

v1 responses include deprecation headers:
```http
Deprecation: true
Sunset: Mon, 01 Jul 2026 00:00:00 GMT
Link: </api/v2/generate/>; rel="successor-version"
```
