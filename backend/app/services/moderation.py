"""
Content Moderation Service.

Detects prohibited content in uploaded CAD files through:
- Geometry signature analysis
- Filename/metadata pattern matching
- Machine learning classification (optional)
- Rule-based detection

Migrated from CadQuery to Build123d.
"""

import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from build123d import Part
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.file import File as UploadedFile


class ContentCategory(str, Enum):
    """Categories of prohibited content."""
    
    WEAPON = "weapon"
    WEAPON_COMPONENT = "weapon_component"
    DRUG_PARAPHERNALIA = "drug_paraphernalia"
    COUNTERFEIT = "counterfeit"
    RESTRICTED_EXPORT = "restricted_export"
    COPYRIGHT_VIOLATION = "copyright_violation"
    OTHER_PROHIBITED = "other_prohibited"


class FlagSeverity(str, Enum):
    """Severity levels for content flags."""
    
    LOW = "low"           # Needs review but likely OK
    MEDIUM = "medium"     # Suspicious, requires human review
    HIGH = "high"         # Likely prohibited, auto-quarantine
    CRITICAL = "critical"  # Definite violation, auto-reject


class ModerationStatus(str, Enum):
    """Status of moderation review."""
    
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


@dataclass
class ContentFlag:
    """A single content flag from analysis."""
    
    id: UUID = field(default_factory=uuid4)
    category: ContentCategory = ContentCategory.OTHER_PROHIBITED
    severity: FlagSeverity = FlagSeverity.LOW
    confidence: float = 0.0  # 0.0 to 1.0
    reason: str = ""
    details: dict = field(default_factory=dict)
    rule_id: str | None = None


@dataclass
class ModerationResult:
    """Result of content moderation analysis."""
    
    file_id: UUID
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    flags: list[ContentFlag] = field(default_factory=list)
    overall_status: ModerationStatus = ModerationStatus.PENDING
    auto_decision: bool = False
    requires_human_review: bool = True
    geometry_hash: str | None = None
    
    @property
    def is_flagged(self) -> bool:
        """Check if any flags were raised."""
        return len(self.flags) > 0
    
    @property
    def highest_severity(self) -> FlagSeverity | None:
        """Get the highest severity flag."""
        if not self.flags:
            return None
        severity_order = [
            FlagSeverity.LOW,
            FlagSeverity.MEDIUM,
            FlagSeverity.HIGH,
            FlagSeverity.CRITICAL,
        ]
        max_idx = max(
            severity_order.index(f.severity) for f in self.flags
        )
        return severity_order[max_idx]
    
    @property
    def max_confidence(self) -> float:
        """Get maximum confidence score."""
        if not self.flags:
            return 0.0
        return max(f.confidence for f in self.flags)


# =============================================================================
# Detection Rules
# =============================================================================

# Prohibited filename patterns
# Note: Using (?:^|[\W_]) and (?:[\W_]|$) instead of \b because
# Python regex treats underscore as a word character, but filenames
# often use underscores as word separators
FILENAME_PATTERNS: list[tuple[str, ContentCategory, FlagSeverity]] = [
    # Weapons
    (r"(?:^|[\W_])(gun|pistol|rifle|firearm|weapon)(?:[\W_]|$)", ContentCategory.WEAPON, FlagSeverity.HIGH),
    (r"(?:^|[\W_])(ar[-_]?15|ak[-_]?47|glock|m16)(?:[\W_]|$)", ContentCategory.WEAPON, FlagSeverity.CRITICAL),
    (r"(?:^|[\W_])(receiver|lower|upper|trigger|barrel)(?:[\W_]|$)", ContentCategory.WEAPON_COMPONENT, FlagSeverity.MEDIUM),
    (r"(?:^|[\W_])(suppressor|silencer)(?:[\W_]|$)", ContentCategory.WEAPON_COMPONENT, FlagSeverity.CRITICAL),
    (r"(?:^|[\W_])(magazine|mag[-_]?clip)(?:[\W_]|$)", ContentCategory.WEAPON_COMPONENT, FlagSeverity.MEDIUM),
    
    # Drug paraphernalia
    (r"(?:^|[\W_])(pipe|bong|grinder)(?:[\W_]|$)", ContentCategory.DRUG_PARAPHERNALIA, FlagSeverity.LOW),
    
    # Counterfeit
    (r"(?:^|[\W_])(replica|fake|counterfeit)(?:[\W_]|$)", ContentCategory.COUNTERFEIT, FlagSeverity.MEDIUM),
    
    # Restricted
    (r"(?:^|[\W_])(itar|munition|export[-_]?control)(?:[\W_]|$)", ContentCategory.RESTRICTED_EXPORT, FlagSeverity.HIGH),
]

# Suspicious geometry signatures (simplified heuristics)
# In production, this would use ML-based shape classification
GEOMETRY_SIGNATURES: list[dict[str, Any]] = [
    {
        "name": "barrel_like",
        "description": "Cylindrical with internal bore",
        "check": lambda info: (
            info.get("aspect_ratio", 0) > 3.0 and
            info.get("has_internal_cavity", False) and
            info.get("cavity_ratio", 0) > 0.3
        ),
        "category": ContentCategory.WEAPON_COMPONENT,
        "severity": FlagSeverity.MEDIUM,
        "confidence": 0.4,
    },
    {
        "name": "receiver_like",
        "description": "Box-like with multiple internal features",
        "check": lambda info: (
            0.5 < info.get("aspect_ratio", 0) < 2.0 and
            info.get("internal_feature_count", 0) > 5 and
            info.get("has_pin_holes", False)
        ),
        "category": ContentCategory.WEAPON_COMPONENT,
        "severity": FlagSeverity.MEDIUM,
        "confidence": 0.35,
    },
    {
        "name": "magazine_like",
        "description": "Rectangular with spring cavity",
        "check": lambda info: (
            info.get("aspect_ratio", 0) > 2.0 and
            info.get("has_internal_cavity", False) and
            info.get("wall_thickness", 0) < 3.0
        ),
        "category": ContentCategory.WEAPON_COMPONENT,
        "severity": FlagSeverity.LOW,
        "confidence": 0.25,
    },
]


class ContentModerator:
    """
    Service for analyzing and moderating uploaded content.
    
    Uses multi-layered detection:
    1. Filename pattern matching
    2. Metadata analysis
    3. Geometry signature detection
    4. Hash-based known-bad detection
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._known_bad_hashes: set[str] = set()
        self._load_known_bad_hashes()
    
    def _load_known_bad_hashes(self) -> None:
        """Load known-bad geometry hashes from database/config."""
        # In production, load from database or external service
        # For now, use empty set
        self._known_bad_hashes = set()
    
    async def analyze_file(
        self,
        file_id: UUID,
        shape: Part | None = None,
    ) -> ModerationResult:
        """
        Perform full content moderation analysis on a file.
        
        Args:
            file_id: The file to analyze
            shape: Optional pre-loaded Build123d Part
            
        Returns:
            ModerationResult with all detected flags
        """
        # Get file info
        query = select(UploadedFile).where(UploadedFile.id == file_id)
        result = await self.db.execute(query)
        file_record = result.scalar_one_or_none()
        
        if not file_record:
            raise ValueError(f"File {file_id} not found")
        
        all_flags: list[ContentFlag] = []
        
        # Check filename
        filename_flags = self.check_filename(file_record.original_filename)
        all_flags.extend(filename_flags)
        
        # Check metadata
        if file_record.metadata:
            metadata_flags = self.check_metadata(file_record.metadata)
            all_flags.extend(metadata_flags)
        
        # Check geometry if shape provided
        geometry_hash = None
        if shape:
            geometry_flags, geometry_hash = self.check_geometry(shape)
            all_flags.extend(geometry_flags)
            
            # Check against known-bad hashes
            if geometry_hash in self._known_bad_hashes:
                all_flags.append(ContentFlag(
                    category=ContentCategory.OTHER_PROHIBITED,
                    severity=FlagSeverity.CRITICAL,
                    confidence=1.0,
                    reason="Matches known prohibited content",
                    rule_id="known_bad_hash",
                ))
        
        # Determine overall status
        mod_result = ModerationResult(
            file_id=file_id,
            flags=all_flags,
            geometry_hash=geometry_hash,
        )
        
        # Auto-decision logic
        mod_result = self._apply_auto_decision(mod_result)
        
        return mod_result
    
    def check_filename(self, filename: str) -> list[ContentFlag]:
        """Check filename for prohibited patterns."""
        flags = []
        filename_lower = filename.lower()
        
        for pattern, category, severity in FILENAME_PATTERNS:
            if re.search(pattern, filename_lower, re.IGNORECASE):
                flags.append(ContentFlag(
                    category=category,
                    severity=severity,
                    confidence=0.7,
                    reason=f"Filename matches prohibited pattern: {pattern}",
                    details={"filename": filename, "pattern": pattern},
                    rule_id=f"filename_{pattern[:20]}",
                ))
        
        return flags
    
    def check_metadata(self, metadata: dict) -> list[ContentFlag]:
        """Check file metadata for suspicious content."""
        flags = []
        
        # Check description, tags, etc.
        searchable_text = " ".join([
            str(metadata.get("description", "")),
            str(metadata.get("title", "")),
            " ".join(metadata.get("tags", [])),
            str(metadata.get("author", "")),
        ]).lower()
        
        for pattern, category, severity in FILENAME_PATTERNS:
            if re.search(pattern, searchable_text, re.IGNORECASE):
                # Lower confidence for metadata than filename
                flags.append(ContentFlag(
                    category=category,
                    severity=FlagSeverity.LOW if severity == FlagSeverity.MEDIUM else severity,
                    confidence=0.5,
                    reason=f"Metadata matches prohibited pattern: {pattern}",
                    details={"pattern": pattern},
                    rule_id=f"metadata_{pattern[:20]}",
                ))
        
        return flags
    
    def check_geometry(
        self,
        shape: Part,
    ) -> tuple[list[ContentFlag], str]:
        """
        Check geometry for suspicious signatures.
        
        Returns:
            Tuple of (flags, geometry_hash)
        """
        flags = []
        
        # Calculate geometry hash
        geometry_hash = self._compute_geometry_hash(shape)
        
        # Extract geometry features
        features = self._extract_geometry_features(shape)
        
        # Check against signatures
        for sig in GEOMETRY_SIGNATURES:
            try:
                if sig["check"](features):
                    flags.append(ContentFlag(
                        category=sig["category"],
                        severity=sig["severity"],
                        confidence=sig["confidence"],
                        reason=sig["description"],
                        details={"signature": sig["name"], "features": features},
                        rule_id=f"geometry_{sig['name']}",
                    ))
            except Exception:
                # Skip failed checks
                continue
        
        return flags, geometry_hash
    
    def _compute_geometry_hash(self, shape: Part) -> str:
        """Compute a hash of the geometry for deduplication."""
        try:
            # Get solid properties using Build123d
            props = [
                f"v:{shape.volume:.2f}",
                f"a:{shape.area:.2f}",
            ]
            
            # Add bounding box
            bb = shape.bounding_box()
            xlen = bb.max.X - bb.min.X
            ylen = bb.max.Y - bb.min.Y
            zlen = bb.max.Z - bb.min.Z
            props.extend([
                f"x:{xlen:.2f}",
                f"y:{ylen:.2f}",
                f"z:{zlen:.2f}",
            ])
            
            hash_input = "|".join(props)
            return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        except Exception:
            return hashlib.sha256(str(uuid4()).encode()).hexdigest()[:16]
    
    def _extract_geometry_features(self, shape: Part) -> dict:
        """Extract geometry features for signature matching."""
        features = {}
        
        try:
            bb = shape.bounding_box()
            xlen = bb.max.X - bb.min.X
            ylen = bb.max.Y - bb.min.Y
            zlen = bb.max.Z - bb.min.Z
            
            # Basic dimensions
            dims = sorted([xlen, ylen, zlen], reverse=True)
            features["length"] = dims[0]
            features["width"] = dims[1]
            features["height"] = dims[2]
            features["aspect_ratio"] = dims[0] / dims[2] if dims[2] > 0 else 0
            
            # Volume and area
            features["volume"] = shape.volume
            features["surface_area"] = shape.area
            
            # Estimate if hollow (low volume/area ratio suggests hollow)
            expected_solid_volume = dims[0] * dims[1] * dims[2]
            features["fill_ratio"] = features["volume"] / expected_solid_volume if expected_solid_volume > 0 else 1.0
            features["has_internal_cavity"] = features["fill_ratio"] < 0.7
            
            # Count faces/edges (complex internals = more features)
            try:
                faces = shape.faces()
                edges = shape.edges()
                features["face_count"] = len(faces)
                features["edge_count"] = len(edges)
                features["internal_feature_count"] = max(0, len(faces) - 6)  # More than a box
            except Exception:
                features["face_count"] = 0
                features["edge_count"] = 0
                features["internal_feature_count"] = 0
            
            # Estimate wall thickness (very rough)
            if features["has_internal_cavity"]:
                cavity_volume = expected_solid_volume - features["volume"]
                features["cavity_ratio"] = cavity_volume / expected_solid_volume
                features["wall_thickness"] = min(dims) * (1 - features["cavity_ratio"] ** 0.33)
            else:
                features["cavity_ratio"] = 0
                features["wall_thickness"] = min(dims) / 2
            
            # Check for small holes (potential pin holes) - simplified for Build123d
            try:
                # In Build123d, checking for circular edges is different
                circular_edges = [e for e in edges if hasattr(e, 'radius') and e.radius() < 5.0]
                features["has_pin_holes"] = len(circular_edges) >= 2
            except Exception:
                features["has_pin_holes"] = False
                
        except Exception:
            # Return empty features on error
            pass
        
        return features
    
    def _apply_auto_decision(self, result: ModerationResult) -> ModerationResult:
        """Apply automatic decision based on flags."""
        if not result.flags:
            # No flags = auto-approve
            result.overall_status = ModerationStatus.APPROVED
            result.auto_decision = True
            result.requires_human_review = False
            return result
        
        highest = result.highest_severity
        max_conf = result.max_confidence
        
        if highest == FlagSeverity.CRITICAL and max_conf >= 0.8:
            # Critical with high confidence = auto-reject
            result.overall_status = ModerationStatus.REJECTED
            result.auto_decision = True
            result.requires_human_review = False
        elif highest == FlagSeverity.CRITICAL or (highest == FlagSeverity.HIGH and max_conf >= 0.7):
            # Critical or high severity = quarantine pending review
            result.overall_status = ModerationStatus.QUARANTINED
            result.auto_decision = True
            result.requires_human_review = True
        else:
            # Lower severity = pending human review
            result.overall_status = ModerationStatus.PENDING
            result.auto_decision = False
            result.requires_human_review = True
        
        return result
    
    async def add_to_known_bad(self, geometry_hash: str) -> None:
        """Add a geometry hash to the known-bad list."""
        self._known_bad_hashes.add(geometry_hash)
        # In production, persist to database
    
    async def get_moderation_stats(self) -> dict:
        """Get moderation statistics."""
        # Would query database for stats
        return {
            "pending_review": 0,
            "approved_today": 0,
            "rejected_today": 0,
            "quarantined": 0,
        }
