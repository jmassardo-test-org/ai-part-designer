"""
Engineering terminology glossary for CAD/3D-printing assistance.

Provides a comprehensive glossary of mechanical-engineering and CAD terms,
fuzzy-search capability to match informal user queries to the correct terms,
and a condensed context string that can be injected into AI system prompts.

Example:
    >>> from app.ai.engineering_glossary import search_glossary
    >>> results = search_glossary("shave off edge")
    >>> results[0]["term"]
    'chamfer'
"""

from __future__ import annotations

import difflib
import re
from enum import StrEnum
from typing import TypedDict

# =============================================================================
# Types
# =============================================================================


class GlossaryCategory(StrEnum):
    """Categories for engineering glossary terms."""

    PRIMITIVES = "primitives"
    FEATURES = "features"
    OPERATIONS = "operations"
    MANUFACTURING = "manufacturing"
    MATERIALS = "materials"
    TOLERANCES = "tolerances"


class GlossaryEntry(TypedDict):
    """A single glossary entry."""

    term: str
    definition: str
    category: str
    aliases: list[str]
    keywords: list[str]


# =============================================================================
# Glossary Data
# =============================================================================

ENGINEERING_GLOSSARY: list[GlossaryEntry] = [
    # ── Primitives ──────────────────────────────────────────────────────
    {
        "term": "box",
        "definition": ("A rectangular prism / cuboid defined by length, width, and height."),
        "category": GlossaryCategory.PRIMITIVES,
        "aliases": ["cube", "rectangular prism", "cuboid", "block"],
        "keywords": ["rectangle", "square", "brick", "slab"],
    },
    {
        "term": "cylinder",
        "definition": (
            "A solid with circular cross-section defined by radius/diameter and height."
        ),
        "category": GlossaryCategory.PRIMITIVES,
        "aliases": ["tube", "rod", "pipe", "round bar"],
        "keywords": ["circular", "round", "tubular"],
    },
    {
        "term": "sphere",
        "definition": "A perfectly round solid defined by its radius or diameter.",
        "category": GlossaryCategory.PRIMITIVES,
        "aliases": ["ball", "globe"],
        "keywords": ["round", "ball-shaped"],
    },
    {
        "term": "cone",
        "definition": (
            "A solid that tapers from a circular base to a point or smaller "
            "circle (frustum). Defined by base radius, top radius, and height."
        ),
        "category": GlossaryCategory.PRIMITIVES,
        "aliases": ["frustum", "tapered cylinder"],
        "keywords": ["taper", "pointed", "conical"],
    },
    {
        "term": "torus",
        "definition": (
            "A donut-shaped solid defined by a major radius (center to tube "
            "center) and minor radius (tube radius)."
        ),
        "category": GlossaryCategory.PRIMITIVES,
        "aliases": ["donut", "ring"],
        "keywords": ["donut-shaped", "ring-shaped", "o-shape"],
    },
    {
        "term": "wedge",
        "definition": (
            "A triangular-prism solid that slopes from one edge to another, like a doorstop."
        ),
        "category": GlossaryCategory.PRIMITIVES,
        "aliases": ["ramp", "incline"],
        "keywords": ["slope", "triangular", "angled"],
    },
    # ── Features ────────────────────────────────────────────────────────
    {
        "term": "chamfer",
        "definition": (
            "A flat angled cut applied to an edge or corner, creating a "
            "beveled transition instead of a sharp 90° edge. Commonly used "
            "to ease assembly, reduce stress concentrations, and remove "
            "sharp edges."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["bevel", "edge break", "edge cut"],
        "keywords": [
            "shave off edge",
            "cut edge",
            "angled edge",
            "angle cut",
            "beveled edge",
            "remove corner",
            "flat edge cut",
            "45 degree edge",
        ],
    },
    {
        "term": "fillet",
        "definition": (
            "A rounded transition between two surfaces, creating a smooth "
            "concave curve at an interior edge. Reduces stress concentrations "
            "and improves aesthetics."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["round", "radius", "blend"],
        "keywords": [
            "round edge",
            "smooth edge",
            "curved edge",
            "round corner",
            "smooth corner",
            "rounded transition",
        ],
    },
    {
        "term": "boss",
        "definition": (
            "A raised cylindrical feature on a surface, often used as a "
            "mounting point for screws or press-fit inserts."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["stud", "post", "pillar"],
        "keywords": [
            "raised cylinder",
            "mounting post",
            "screw post",
            "standoff post",
            "protruding cylinder",
        ],
    },
    {
        "term": "pocket",
        "definition": (
            "A recessed area (cavity) machined or modeled into a surface. "
            "Can be rectangular, circular, or any profile. Does not go all "
            "the way through the part."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["cavity", "recess", "depression"],
        "keywords": [
            "cut into surface",
            "hollowed out",
            "recessed area",
            "carved out",
            "indentation",
            "dugout",
        ],
    },
    {
        "term": "bore",
        "definition": (
            "A precision-machined cylindrical hole, typically with tight "
            "tolerances. Often larger than a simple drilled hole."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["precision hole", "bored hole"],
        "keywords": ["large hole", "precision cylindrical hole", "machine hole"],
    },
    {
        "term": "counterbore",
        "definition": (
            "A flat-bottomed enlargement at the entry of a hole, allowing a "
            "bolt head or socket-head cap screw to sit flush with or below "
            "the surface."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["cbore", "spot face"],
        "keywords": [
            "flat bottom hole",
            "bolt recess",
            "screw head recess",
            "socket head clearance",
            "stepped hole",
        ],
    },
    {
        "term": "countersink",
        "definition": (
            "A conical enlargement at the entry of a hole, allowing a "
            "flat-head screw to sit flush with the surface."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["csink", "csk"],
        "keywords": [
            "cone-shaped hole",
            "screw flush",
            "flat head screw hole",
            "angled hole entry",
            "bevel hole",
        ],
    },
    {
        "term": "through-hole",
        "definition": ("A hole that passes completely through a part from one side to the other."),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["thru hole", "thru-hole"],
        "keywords": [
            "hole all the way through",
            "complete hole",
            "passes through",
            "open both sides",
        ],
    },
    {
        "term": "blind hole",
        "definition": (
            "A hole that does not pass all the way through the part; it has a defined depth."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["dead-end hole", "closed hole"],
        "keywords": [
            "partial hole",
            "hole with depth",
            "hole not through",
            "stopped hole",
        ],
    },
    {
        "term": "slot",
        "definition": (
            "An elongated rectangular or profiled cut-out in a part. Can be through or blind."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["groove", "channel", "track"],
        "keywords": [
            "long cut",
            "elongated hole",
            "sliding track",
            "rectangular cut",
        ],
    },
    {
        "term": "keyway",
        "definition": (
            "A slot machined into a shaft or hub to accept a key, preventing "
            "relative rotation between components."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["key slot", "key seat"],
        "keywords": [
            "shaft slot",
            "key groove",
            "anti-rotation slot",
            "locking slot",
        ],
    },
    {
        "term": "spline",
        "definition": (
            "A series of ridges or teeth on a shaft that mesh with grooves "
            "in a mating part to transmit torque."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["splined shaft", "serration"],
        "keywords": [
            "ridged shaft",
            "toothed shaft",
            "torque transmission",
            "gear-like shaft",
        ],
    },
    {
        "term": "dovetail",
        "definition": (
            "A fan-shaped interlocking joint where a trapezoidal tenon fits "
            "into a matching mortise. Very strong against pulling apart."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["dovetail joint", "dovetail slide"],
        "keywords": [
            "interlocking joint",
            "fan-shaped joint",
            "trapezoidal joint",
            "woodworking joint",
            "sliding joint",
        ],
    },
    {
        "term": "rabbet",
        "definition": (
            "A step-shaped recess cut along the edge of a part, forming an "
            "L-shaped profile. Used for joining panels or creating overlaps."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["rebate"],
        "keywords": [
            "edge step",
            "L-shaped cut",
            "edge recess",
            "panel joint",
            "overlap cut",
        ],
    },
    {
        "term": "dado",
        "definition": (
            "A flat-bottomed groove cut across the grain or face of a part, "
            "typically used to receive another piece."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["housing joint", "trench"],
        "keywords": [
            "cross groove",
            "shelf slot",
            "panel groove",
            "flat groove",
        ],
    },
    {
        "term": "mortise",
        "definition": (
            "A rectangular hole or slot cut into a part to receive a tenon "
            "for a mortise-and-tenon joint."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["mortice"],
        "keywords": [
            "rectangular hole",
            "tenon receiver",
            "joint socket",
            "square hole",
        ],
    },
    {
        "term": "tenon",
        "definition": (
            "A projecting tongue on a part that fits into a mortise to form a strong joint."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["tongue"],
        "keywords": [
            "projecting tab",
            "joint tongue",
            "insert tab",
            "protruding piece",
        ],
    },
    {
        "term": "flange",
        "definition": (
            "A protruding rim, lip, or edge on a part used for "
            "strengthening, guiding, or attaching to another object."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["rim", "lip", "collar", "mounting flange"],
        "keywords": [
            "protruding edge",
            "mounting rim",
            "attachment lip",
            "bolt circle",
            "pipe connection",
        ],
    },
    {
        "term": "o-ring groove",
        "definition": (
            "A precisely dimensioned channel that holds an O-ring seal. "
            "Size follows standard AS568 or ISO 3601 dimensions."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["o-ring channel", "seal groove", "gland"],
        "keywords": [
            "seal channel",
            "rubber ring groove",
            "gasket groove",
            "sealing groove",
        ],
    },
    {
        "term": "thread",
        "definition": (
            "A helical ridge on internal or external cylindrical surfaces, "
            "used for fastening (bolts/nuts) or motion (lead screws). "
            "Common standards: metric (M3, M4…), UNC, UNF."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["screw thread", "threading"],
        "keywords": [
            "helical ridge",
            "screw pattern",
            "bolt thread",
            "nut thread",
            "threaded hole",
            "tapped hole",
        ],
    },
    {
        "term": "knurl",
        "definition": (
            "A cross-hatched or straight-line pattern rolled or cut into a "
            "cylindrical surface to improve grip."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["knurling", "grip pattern"],
        "keywords": [
            "textured surface",
            "grip texture",
            "diamond pattern",
            "anti-slip surface",
            "rough surface",
        ],
    },
    {
        "term": "undercut",
        "definition": (
            "A recessed surface that cannot be reached by a straight tool "
            "path. In 3D printing refers to overhanging geometry that "
            "may need support material."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["recess", "back-cut"],
        "keywords": [
            "hidden recess",
            "overhang",
            "unreachable area",
            "negative draft",
            "support needed",
        ],
    },
    {
        "term": "relief",
        "definition": (
            "A small groove or recess cut at the intersection of two "
            "surfaces to provide clearance, allow full seating, or "
            "reduce stress."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["relief groove", "tool relief", "stress relief"],
        "keywords": [
            "clearance groove",
            "stress reducer",
            "corner clearance",
            "runout groove",
        ],
    },
    {
        "term": "shoulder",
        "definition": (
            "A step or ledge formed by a change in diameter on a shaft or "
            "a change in thickness on a plate."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["step", "ledge"],
        "keywords": [
            "diameter change",
            "step down",
            "shaft step",
            "locating shoulder",
        ],
    },
    {
        "term": "standoff",
        "definition": (
            "A small post or spacer used to elevate a PCB or component "
            "above a surface at a fixed distance."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["spacer post", "PCB standoff"],
        "keywords": [
            "circuit board mount",
            "PCB post",
            "board spacer",
            "raised mount",
            "hex standoff",
        ],
    },
    {
        "term": "spacer",
        "definition": (
            "A component placed between two parts to maintain a fixed distance or gap between them."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["shim", "washer"],
        "keywords": [
            "gap filler",
            "distance keeper",
            "separator",
            "spacing ring",
        ],
    },
    {
        "term": "bushing",
        "definition": (
            "A cylindrical sleeve inserted into a housing to reduce "
            "friction, provide a bearing surface, or protect against wear."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["sleeve", "bush", "liner"],
        "keywords": [
            "sleeve bearing",
            "cylindrical insert",
            "wear liner",
            "guide bushing",
        ],
    },
    {
        "term": "bearing",
        "definition": (
            "A component that supports relative motion (rotation or linear) "
            "between parts while minimizing friction."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["ball bearing", "roller bearing"],
        "keywords": [
            "rotation support",
            "friction reducer",
            "rolling element",
            "shaft support",
        ],
    },
    {
        "term": "journal",
        "definition": ("The portion of a shaft that rides inside a bearing or bushing."),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["bearing journal", "shaft journal"],
        "keywords": [
            "shaft bearing surface",
            "rotating surface",
            "bearing seat",
        ],
    },
    {
        "term": "gasket",
        "definition": (
            "A flat sealing element placed between two mating surfaces to "
            "prevent leakage of fluids or gases."
        ),
        "category": GlossaryCategory.FEATURES,
        "aliases": ["seal", "packing"],
        "keywords": [
            "sealing material",
            "leak prevention",
            "joint seal",
            "flat seal",
        ],
    },
    # ── Operations ──────────────────────────────────────────────────────
    {
        "term": "extrude",
        "definition": (
            "To create a 3D solid by pushing a 2D profile along a straight "
            "path (usually perpendicular to the sketch plane)."
        ),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["extrusion", "pad", "protrusion"],
        "keywords": [
            "push profile",
            "stretch shape",
            "add material along path",
            "pull up sketch",
        ],
    },
    {
        "term": "revolve",
        "definition": ("To create a 3D solid by rotating a 2D profile around an axis."),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["revolution", "lathe", "turn"],
        "keywords": [
            "spin profile",
            "rotate sketch",
            "axis rotation",
            "turned part",
        ],
    },
    {
        "term": "sweep",
        "definition": (
            "To create a 3D solid by moving a 2D profile along a curved or complex path."
        ),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["swept feature"],
        "keywords": [
            "follow path",
            "profile along curve",
            "pipe shape",
            "path extrusion",
        ],
    },
    {
        "term": "loft",
        "definition": (
            "To create a 3D solid that transitions smoothly between two or "
            "more different cross-section profiles."
        ),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["blend", "transition"],
        "keywords": [
            "morph between shapes",
            "cross-section transition",
            "blended shape",
            "smooth transition",
        ],
    },
    {
        "term": "boolean union",
        "definition": (
            "Combining two or more solids into a single body, merging overlapping volumes."
        ),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["fuse", "join", "add", "combine"],
        "keywords": [
            "merge shapes",
            "add together",
            "join solids",
            "combine bodies",
        ],
    },
    {
        "term": "boolean subtraction",
        "definition": (
            "Removing the volume of one solid from another (e.g., cutting a "
            "hole). Also called a 'cut'."
        ),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["cut", "subtract", "difference"],
        "keywords": [
            "remove material",
            "cut away",
            "carve out",
            "subtract shape",
        ],
    },
    {
        "term": "boolean intersection",
        "definition": ("Keeping only the volume shared by two overlapping solids."),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["intersect", "common"],
        "keywords": [
            "shared volume",
            "overlapping region",
            "common area",
        ],
    },
    {
        "term": "mirror",
        "definition": (
            "Duplicating geometry across a plane of symmetry to create a symmetric part or pattern."
        ),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["reflect", "symmetric copy"],
        "keywords": [
            "flip copy",
            "symmetry",
            "mirror image",
            "reflected geometry",
        ],
    },
    {
        "term": "pattern",
        "definition": (
            "Repeating a feature in a linear or circular arrangement (e.g., a ring of bolt holes)."
        ),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["array", "linear pattern", "circular pattern"],
        "keywords": [
            "repeat feature",
            "copy in circle",
            "array of holes",
            "bolt circle",
        ],
    },
    {
        "term": "shell",
        "definition": (
            "Hollowing out a solid to create a thin-walled part with a specified wall thickness."
        ),
        "category": GlossaryCategory.OPERATIONS,
        "aliases": ["hollow", "thin wall"],
        "keywords": [
            "hollow out",
            "make thin wall",
            "empty inside",
            "create cavity",
        ],
    },
    # ── Manufacturing ───────────────────────────────────────────────────
    {
        "term": "draft angle",
        "definition": (
            "A slight taper applied to vertical faces so a part can be "
            "ejected from a mold or die. Typically 1°–3° for injection "
            "molding."
        ),
        "category": GlossaryCategory.MANUFACTURING,
        "aliases": ["draft", "mold taper", "demolding angle"],
        "keywords": [
            "mold release angle",
            "taper for molding",
            "ejection taper",
            "slight angle on wall",
        ],
    },
    {
        "term": "taper",
        "definition": (
            "A gradual change in diameter or width along the length of a feature or part."
        ),
        "category": GlossaryCategory.MANUFACTURING,
        "aliases": ["tapered"],
        "keywords": [
            "narrowing",
            "widening",
            "gradual change",
            "cone-like change",
        ],
    },
    {
        "term": "kerf",
        "definition": (
            "The width of material removed by a cutting tool (saw blade, "
            "laser, waterjet). Important for accounting for material loss."
        ),
        "category": GlossaryCategory.MANUFACTURING,
        "aliases": ["cut width", "blade width"],
        "keywords": [
            "saw cut width",
            "laser cut width",
            "material loss",
            "cutting width",
        ],
    },
    {
        "term": "deburr",
        "definition": (
            "Removing sharp edges, burrs, or rough material left after machining or cutting."
        ),
        "category": GlossaryCategory.MANUFACTURING,
        "aliases": ["deburring", "edge finishing"],
        "keywords": [
            "remove burrs",
            "smooth after cutting",
            "clean edges",
            "finishing",
        ],
    },
    {
        "term": "annealing",
        "definition": (
            "A heat treatment process that softens a material, relieves "
            "internal stresses, and improves ductility."
        ),
        "category": GlossaryCategory.MANUFACTURING,
        "aliases": ["heat treatment", "stress relief annealing"],
        "keywords": [
            "heat and cool",
            "soften metal",
            "relieve stress",
            "thermal treatment",
        ],
    },
    # ── Materials ───────────────────────────────────────────────────────
    {
        "term": "PLA",
        "definition": (
            "Polylactic Acid — the most common FDM 3D-printing filament. "
            "Biodegradable, easy to print, low warp, but brittle and poor "
            "heat resistance (~60 °C)."
        ),
        "category": GlossaryCategory.MATERIALS,
        "aliases": ["polylactic acid"],
        "keywords": [
            "beginner filament",
            "eco-friendly filament",
            "basic 3d printing material",
        ],
    },
    {
        "term": "ABS",
        "definition": (
            "Acrylonitrile Butadiene Styrene — strong, heat-resistant "
            "3D-printing filament (~100 °C). Requires heated bed; tends "
            "to warp."
        ),
        "category": GlossaryCategory.MATERIALS,
        "aliases": ["acrylonitrile butadiene styrene"],
        "keywords": [
            "tough filament",
            "heat resistant filament",
            "lego material",
        ],
    },
    {
        "term": "PETG",
        "definition": (
            "Polyethylene Terephthalate Glycol — combines ease of printing "
            "(like PLA) with better strength and temperature resistance "
            "(like ABS). Good chemical resistance."
        ),
        "category": GlossaryCategory.MATERIALS,
        "aliases": ["polyethylene terephthalate glycol"],
        "keywords": [
            "food safe filament",
            "balanced filament",
            "durable filament",
        ],
    },
    {
        "term": "TPU",
        "definition": (
            "Thermoplastic Polyurethane — a flexible, rubber-like "
            "3D-printing filament. Great for gaskets, bumpers, and "
            "flexible parts."
        ),
        "category": GlossaryCategory.MATERIALS,
        "aliases": ["thermoplastic polyurethane", "flexible filament"],
        "keywords": [
            "rubber-like",
            "flexible material",
            "elastic filament",
            "soft filament",
        ],
    },
    {
        "term": "nylon",
        "definition": (
            "A strong, wear-resistant engineering thermoplastic. Excellent "
            "for functional parts, gears, and hinges. Absorbs moisture."
        ),
        "category": GlossaryCategory.MATERIALS,
        "aliases": ["PA", "polyamide", "PA6", "PA12"],
        "keywords": [
            "engineering plastic",
            "strong filament",
            "wear resistant filament",
            "gear material",
        ],
    },
    # ── Tolerances & Dimensioning ───────────────────────────────────────
    {
        "term": "tolerance",
        "definition": (
            "The permissible range of variation in a dimension. "
            "Example: 50 ± 0.1 mm means the part can be 49.9–50.1 mm."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["dimensional tolerance", "tol"],
        "keywords": [
            "allowable variation",
            "plus minus",
            "accuracy range",
            "acceptable range",
        ],
    },
    {
        "term": "clearance",
        "definition": (
            "The intentional gap between two mating parts to allow free movement or easy assembly."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["clearance fit", "running fit"],
        "keywords": [
            "gap between parts",
            "loose fit",
            "free movement",
            "play between parts",
        ],
    },
    {
        "term": "interference fit",
        "definition": (
            "A fit where the shaft is slightly larger than the hole, "
            "requiring force or temperature change to assemble. Creates a "
            "very tight, permanent connection."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["press fit", "force fit", "shrink fit"],
        "keywords": [
            "tight fit",
            "forced assembly",
            "permanent fit",
            "oversized shaft",
            "no gap",
        ],
    },
    {
        "term": "press fit",
        "definition": (
            "An interference fit assembled by pressing one part into "
            "another with force, commonly used for pins, bushings, and "
            "bearings."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["force fit", "friction fit"],
        "keywords": [
            "push in fit",
            "pressed insert",
            "friction hold",
            "tight insertion",
        ],
    },
    {
        "term": "datum",
        "definition": (
            "A theoretically exact reference point, line, or plane used "
            "for dimensioning and tolerancing. Identified by a letter "
            "(A, B, C…) in GD&T."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["reference surface", "datum plane"],
        "keywords": [
            "measurement reference",
            "origin surface",
            "reference point",
            "GD&T reference",
        ],
    },
    {
        "term": "GD&T",
        "definition": (
            "Geometric Dimensioning and Tolerancing — an international "
            "standard (ASME Y14.5 / ISO 1101) for defining and "
            "communicating engineering tolerances using symbols on "
            "technical drawings."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": [
            "geometric dimensioning and tolerancing",
            "geometric tolerancing",
        ],
        "keywords": [
            "engineering symbols",
            "tolerance symbols",
            "flatness",
            "perpendicularity",
            "position tolerance",
        ],
    },
    {
        "term": "concentricity",
        "definition": (
            "A GD&T condition where two or more cylindrical features share the same center axis."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["concentric", "coaxial"],
        "keywords": [
            "same center",
            "shared axis",
            "aligned centers",
            "centered circles",
        ],
    },
    {
        "term": "perpendicularity",
        "definition": (
            "A GD&T condition where a surface or axis is exactly 90° to a datum reference."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["perpendicular", "squareness"],
        "keywords": [
            "right angle",
            "90 degrees",
            "square to reference",
            "normal to surface",
        ],
    },
    {
        "term": "parallelism",
        "definition": (
            "A GD&T condition where a surface or axis maintains a "
            "constant distance from a datum plane or axis."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["parallel"],
        "keywords": [
            "same distance apart",
            "equidistant surfaces",
            "constant gap",
            "uniform distance",
        ],
    },
    {
        "term": "flatness",
        "definition": (
            "A GD&T condition controlling how much a surface can deviate "
            "from a perfect plane. No datum reference required."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["surface flatness"],
        "keywords": [
            "flat surface",
            "planar",
            "no waviness",
            "level surface",
        ],
    },
    {
        "term": "runout",
        "definition": (
            "A GD&T condition that controls the variation of a surface "
            "as the part is rotated 360° around a datum axis. Combines "
            "circularity and coaxiality."
        ),
        "category": GlossaryCategory.TOLERANCES,
        "aliases": ["total runout", "TIR"],
        "keywords": [
            "wobble",
            "rotation variation",
            "shaft wobble",
            "total indicator reading",
        ],
    },
]

# Build a lookup index by term name (lower-case)
_GLOSSARY_INDEX: dict[str, GlossaryEntry] = {
    entry["term"].lower(): entry for entry in ENGINEERING_GLOSSARY
}

# Build an alias → term mapping for fast lookup
_ALIAS_INDEX: dict[str, str] = {}
for _entry in ENGINEERING_GLOSSARY:
    for _alias in _entry["aliases"]:
        _ALIAS_INDEX[_alias.lower()] = _entry["term"].lower()


# =============================================================================
# Public API
# =============================================================================


def search_glossary(
    query: str,
    *,
    max_results: int = 5,
    score_cutoff: float = 0.25,
) -> list[dict[str, str | float]]:
    """Search the engineering glossary using fuzzy matching.

    Matches against term names, aliases, keywords, and definitions.
    Returns results sorted by relevance score (highest first).

    Args:
        query: The user's search text (e.g., "what do you call shaving
            off an edge?" or "chamfer").
        max_results: Maximum number of results to return.
        score_cutoff: Minimum relevance score (0-1) to include a result.

    Returns:
        List of dicts with keys: term, definition, category, score.

    Example:
        >>> results = search_glossary("shave off edge")
        >>> results[0]["term"]
        'chamfer'
    """
    query_lower = _normalize(query)
    query_tokens = set(query_lower.split())

    # Direct term / alias hit — return immediately with score 1.0
    if query_lower in _GLOSSARY_INDEX:
        entry = _GLOSSARY_INDEX[query_lower]
        return [_make_result(entry, 1.0)]
    if query_lower in _ALIAS_INDEX:
        entry = _GLOSSARY_INDEX[_ALIAS_INDEX[query_lower]]
        return [_make_result(entry, 1.0)]

    scored: list[tuple[float, GlossaryEntry]] = []

    for entry in ENGINEERING_GLOSSARY:
        score = _score_entry(entry, query_lower, query_tokens)
        if score >= score_cutoff:
            scored.append((score, entry))

    # Sort descending by score, then alphabetically by term
    scored.sort(key=lambda t: (-t[0], t[1]["term"]))

    return [_make_result(entry, score) for score, entry in scored[:max_results]]


def get_term(term_name: str) -> GlossaryEntry | None:
    """Look up a single glossary entry by exact term name.

    Args:
        term_name: The engineering term to look up (case-insensitive).

    Returns:
        The GlossaryEntry if found, otherwise None.
    """
    key = term_name.strip().lower()
    if key in _GLOSSARY_INDEX:
        return _GLOSSARY_INDEX[key]
    if key in _ALIAS_INDEX:
        return _GLOSSARY_INDEX[_ALIAS_INDEX[key]]
    return None


def list_terms_by_category(category: str) -> list[GlossaryEntry]:
    """Return all glossary entries in a given category.

    Args:
        category: One of the GlossaryCategory values (e.g., "features").

    Returns:
        List of matching GlossaryEntry dicts.
    """
    cat_lower = category.strip().lower()
    return [e for e in ENGINEERING_GLOSSARY if e["category"] == cat_lower]


def format_glossary_context() -> str:
    """Return a condensed glossary reference for embedding in AI prompts.

    Produces a compact multi-line string listing every term with a
    one-line definition, grouped by category.  Designed to fit within
    a system-prompt context window without excessive token usage.

    Returns:
        A formatted string suitable for inclusion in a system prompt.
    """
    lines: list[str] = [
        "## Engineering Terminology Reference",
        "",
    ]

    grouped: dict[str, list[GlossaryEntry]] = {}
    for entry in ENGINEERING_GLOSSARY:
        cat = entry["category"]
        grouped.setdefault(cat, []).append(entry)

    for cat in GlossaryCategory:
        entries = grouped.get(cat, [])
        if not entries:
            continue
        lines.append(f"### {cat.value.title()}")
        for entry in entries:
            # Truncate definition to first sentence for compactness
            short_def = entry["definition"].split(".")[0].strip() + "."
            aliases_str = ", ".join(entry["aliases"][:3])
            line = f"- **{entry['term']}**: {short_def}"
            if aliases_str:
                line += f" _(also: {aliases_str})_"
            lines.append(line)
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# Internal Helpers
# =============================================================================


def _normalize(text: str) -> str:
    """Lower-case and strip non-alphanumeric chars for matching."""
    text = text.lower().strip()
    # Remove common question phrasing
    for prefix in (
        "what is a ",
        "what is an ",
        "what is the ",
        "what is ",
        "what do you call ",
        "what's a ",
        "what's an ",
        "what's the ",
        "define ",
        "explain ",
        "meaning of ",
        "tell me about ",
    ):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    # Strip trailing punctuation
    text = re.sub(r"[?!.,;:]+$", "", text)
    return text.strip()


def _score_entry(
    entry: GlossaryEntry,
    query: str,
    query_tokens: set[str],
) -> float:
    """Score how well a glossary entry matches a query.

    Uses a weighted combination of:
    - Exact / substring match on term name (highest weight)
    - Exact / substring match on aliases
    - Token overlap with keywords
    - difflib sequence matching against definition

    Args:
        entry: The glossary entry to score.
        query: Normalised query string.
        query_tokens: Set of individual query words.

    Returns:
        A relevance score between 0.0 and 1.0.
    """
    score = 0.0
    term_lower = entry["term"].lower()

    # --- Term name matching (weight: high) ---
    if term_lower == query:
        return 1.0  # exact match
    if term_lower in query or query in term_lower:
        score = max(score, 0.85)
    else:
        ratio = difflib.SequenceMatcher(None, term_lower, query).ratio()
        if ratio > 0.6:
            score = max(score, ratio * 0.8)

    # --- Alias matching ---
    for alias in entry["aliases"]:
        alias_lower = alias.lower()
        if alias_lower == query:
            return 0.95
        if alias_lower in query or query in alias_lower:
            score = max(score, 0.80)
        else:
            ratio = difflib.SequenceMatcher(None, alias_lower, query).ratio()
            if ratio > 0.6:
                score = max(score, ratio * 0.75)

    # --- Keyword matching (token overlap) ---
    for kw in entry["keywords"]:
        kw_lower = kw.lower()
        kw_tokens = set(kw_lower.split())
        overlap = query_tokens & kw_tokens
        if overlap:
            # Score based on fraction of keyword tokens matched
            kw_score = len(overlap) / max(len(kw_tokens), len(query_tokens))
            score = max(score, kw_score * 0.75)
        # Also do substring matching on the full keyword string
        if kw_lower in query or query in kw_lower:
            score = max(score, 0.70)

    # --- Definition substring matching (lower weight) ---
    def_lower = entry["definition"].lower()
    if query in def_lower:
        score = max(score, 0.50)
    else:
        # Check token overlap with definition
        def_tokens = set(re.findall(r"\w+", def_lower))
        meaningful_overlap = query_tokens & def_tokens - {
            "a",
            "an",
            "the",
            "is",
            "are",
            "to",
            "of",
            "and",
            "or",
            "in",
            "on",
            "for",
            "with",
            "it",
            "that",
            "this",
        }
        if meaningful_overlap:
            def_score = len(meaningful_overlap) / max(len(query_tokens), 1)
            score = max(score, def_score * 0.45)

    return min(score, 1.0)


def _make_result(
    entry: GlossaryEntry,
    score: float,
) -> dict[str, str | float]:
    """Create a result dict from a glossary entry and score."""
    return {
        "term": entry["term"],
        "definition": entry["definition"],
        "category": entry["category"],
        "score": round(score, 3),
    }
