"""
Thread library API endpoints (v2).

Provides thread standard lookup, tap drill information, thread geometry
generation, and print-optimised generation. Read-only endpoints are
public; mutation endpoints require authentication.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.cad.exceptions import ThreadDataError, ThreadGenerationError
from app.cad.thread_generator import (
    ThreadGenerationResult,
    ThreadGeneratorConfig,
    generate_thread,
)
from app.cad.thread_print_optimizer import (
    PrintProcess,
    PrintThreadConfig,
    ToleranceClass,
    get_print_recommendation,
    optimize_thread_for_print,
)
from app.cad.threads import (
    THREAD_FAMILY_INFO,
    PitchSeries,
    ThreadFamily,
    ThreadHand,
    ThreadType,
    get_tap_drill_info,
    get_thread_spec,
    list_thread_families,
    list_thread_sizes,
)
from app.core.auth import get_current_user
from app.schemas.threads import (
    PrintOptimizedGenerateRequest,
    PrintOptimizedGenerateResponse,
    PrintRecommendationResponse,
    TapDrillResponse,
    ThreadFamilyListResponse,
    ThreadFamilyResponse,
    ThreadGenerateRequest,
    ThreadGenerateResponse,
    ThreadSizeListResponse,
    ThreadSpecResponse,
)

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Helpers
# =============================================================================


def _resolve_family(family: str) -> ThreadFamily:
    """Resolve a string to a ThreadFamily enum member.

    Args:
        family: Raw family identifier from the URL path.

    Returns:
        Matching ThreadFamily enum value.

    Raises:
        HTTPException: 404 if the family is not recognised.
    """
    try:
        return ThreadFamily(family)
    except ValueError:
        valid = [f.value for f in ThreadFamily]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Unknown thread family: '{family}'. Valid families: {', '.join(valid)}"),
        )


def _resolve_enum(
    value: str,
    enum_cls: type,
    label: str,
) -> Any:
    """Resolve a string to an arbitrary StrEnum member.

    Args:
        value: Raw string value.
        enum_cls: StrEnum class to match against.
        label: Human-readable label for error messages.

    Returns:
        Matching enum member.

    Raises:
        HTTPException: 400 if the value is invalid.
    """
    try:
        return enum_cls(value)
    except ValueError:
        valid = [e.value for e in enum_cls]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Invalid {label}: '{value}'. Valid values: {', '.join(valid)}"),
        )


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/families",
    response_model=ThreadFamilyListResponse,
    summary="List all thread families",
)
async def list_families() -> ThreadFamilyListResponse:
    """Return every available thread family with metadata.

    Returns:
        ThreadFamilyListResponse containing all registered families.
    """
    families_out: list[ThreadFamilyResponse] = []
    for fam in list_thread_families():
        info = THREAD_FAMILY_INFO[fam]
        sizes = list_thread_sizes(fam)
        families_out.append(
            ThreadFamilyResponse(
                family=fam.value,
                name=info["name"],
                description=info["description"],
                standard_ref=info["standard_ref"],
                size_count=len(sizes),
            )
        )

    return ThreadFamilyListResponse(
        families=families_out,
        total=len(families_out),
    )


@router.get(
    "/standards/{family}",
    response_model=ThreadSizeListResponse,
    summary="List sizes for a thread family",
)
async def list_sizes(
    family: str,
    pitch_series: str | None = Query(
        None,
        description="Filter by pitch series (coarse, fine)",
    ),
) -> ThreadSizeListResponse:
    """List available thread sizes for a given family.

    Args:
        family: Thread family identifier (e.g. ``iso_metric``).
        pitch_series: Optional pitch series filter.

    Returns:
        ThreadSizeListResponse with the list of size labels.

    Raises:
        HTTPException: 404 if the family is unknown.
    """
    fam_enum = _resolve_family(family)

    ps_enum: PitchSeries | None = None
    if pitch_series is not None:
        ps_enum = _resolve_enum(pitch_series, PitchSeries, "pitch_series")

    try:
        sizes = list_thread_sizes(fam_enum, pitch_series=ps_enum)
    except ThreadDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )

    return ThreadSizeListResponse(
        family=fam_enum.value,
        sizes=sizes,
        total=len(sizes),
        pitch_series=ps_enum.value if ps_enum else None,
    )


@router.get(
    "/standards/{family}/{size:path}",
    response_model=ThreadSpecResponse,
    summary="Get a specific thread specification",
)
async def get_spec(
    family: str,
    size: str,
) -> ThreadSpecResponse:
    """Return the full thread specification for a family/size pair.

    The ``size`` path segment accepts slashes (e.g. ``1/4-20``).

    Args:
        family: Thread family identifier.
        size: Thread size label.

    Returns:
        ThreadSpecResponse with all dimensional data.

    Raises:
        HTTPException: 404 if family or size is not found.
    """
    fam_enum = _resolve_family(family)

    try:
        spec = get_thread_spec(fam_enum, size)
    except ThreadDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )

    return ThreadSpecResponse(
        family=spec.family.value,
        size=spec.size,
        pitch_mm=spec.pitch_mm,
        form=spec.form.value,
        pitch_series=spec.pitch_series.value if spec.pitch_series else None,
        major_diameter=spec.major_diameter,
        pitch_diameter_ext=spec.pitch_diameter_ext,
        minor_diameter_ext=spec.minor_diameter_ext,
        major_diameter_int=spec.major_diameter_int,
        pitch_diameter_int=spec.pitch_diameter_int,
        minor_diameter_int=spec.minor_diameter_int,
        profile_angle_deg=spec.profile_angle_deg,
        taper_per_mm=spec.taper_per_mm,
        tap_drill_mm=spec.tap_drill_mm,
        clearance_hole_close_mm=spec.clearance_hole_close_mm,
        clearance_hole_medium_mm=spec.clearance_hole_medium_mm,
        clearance_hole_free_mm=spec.clearance_hole_free_mm,
        tpi=spec.tpi,
        nominal_size_inch=spec.nominal_size_inch,
        engagement_length_mm=spec.engagement_length_mm,
        standard_ref=spec.standard_ref,
        notes=spec.notes,
    )


@router.get(
    "/tap-drill/{family}/{size:path}",
    response_model=TapDrillResponse,
    summary="Get tap drill information",
)
async def get_tap_drill(
    family: str,
    size: str,
) -> TapDrillResponse:
    """Return tap drill and clearance hole information for a thread size.

    Args:
        family: Thread family identifier.
        size: Thread size label.

    Returns:
        TapDrillResponse with drilling dimensions.

    Raises:
        HTTPException: 404 if family or size is not found.
    """
    fam_enum = _resolve_family(family)

    try:
        info = get_tap_drill_info(fam_enum, size)
    except ThreadDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )

    return TapDrillResponse(
        family=fam_enum.value,
        size=size,
        tap_drill_mm=info["tap_drill_mm"],
        clearance_hole_close_mm=info["clearance_hole_close_mm"],
        clearance_hole_medium_mm=info["clearance_hole_medium_mm"],
        clearance_hole_free_mm=info["clearance_hole_free_mm"],
    )


@router.post(
    "/generate",
    response_model=ThreadGenerateResponse,
    summary="Generate thread geometry",
    status_code=status.HTTP_200_OK,
)
async def generate(
    request: ThreadGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> ThreadGenerateResponse:
    """Generate 3D thread geometry from a specification.

    Requires authentication. Validates family/size, constructs a
    ``ThreadGeneratorConfig``, and delegates to ``generate_thread()``.

    Args:
        request: Thread generation parameters.
        current_user: Authenticated user (injected).

    Returns:
        ThreadGenerateResponse with metadata and timing.

    Raises:
        HTTPException: 400 for invalid enum values, 404 for unknown
            family/size, 500 for generation failures.
    """
    fam_enum = _resolve_family(request.family)
    thread_type = _resolve_enum(
        request.thread_type,
        ThreadType,
        "thread_type",
    )
    hand = _resolve_enum(request.hand, ThreadHand, "hand")

    ps_enum: PitchSeries | None = None
    if request.pitch_series is not None:
        ps_enum = _resolve_enum(
            request.pitch_series,
            PitchSeries,
            "pitch_series",
        )

    try:
        spec = get_thread_spec(fam_enum, request.size, pitch_series=ps_enum)
    except ThreadDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )

    config = ThreadGeneratorConfig(
        spec=spec,
        thread_type=thread_type,
        length_mm=request.length_mm,
        hand=hand,
        add_chamfer=request.add_chamfer,
        custom_pitch_mm=request.custom_pitch_mm,
        custom_diameter_mm=request.custom_diameter_mm,
    )

    try:
        result: ThreadGenerationResult = generate_thread(config)
    except ThreadGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
        )

    logger.info(
        "User %s generated %s thread %s (%s)",
        current_user.id,
        thread_type.value,
        request.size,
        fam_enum.value,
    )

    return ThreadGenerateResponse(
        success=True,
        metadata=result.metadata,
        generation_time_ms=result.generation_time_ms,
        estimated_face_count=result.estimated_face_count,
        message=f"Generated {thread_type.value} {spec.size} thread",
    )


@router.post(
    "/generate/print-optimized",
    response_model=PrintOptimizedGenerateResponse,
    summary="Generate print-optimized thread geometry",
    status_code=status.HTTP_200_OK,
)
async def generate_print_optimized(
    request: PrintOptimizedGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> PrintOptimizedGenerateResponse:
    """Generate 3D thread geometry optimised for a specific print process.

    Requires authentication. Evaluates feasibility, applies clearance
    adjustments, then generates the thread.

    Args:
        request: Print-optimised generation parameters.
        current_user: Authenticated user (injected).

    Returns:
        PrintOptimizedGenerateResponse with feasibility details
        and the underlying generation result.

    Raises:
        HTTPException: 400 for invalid enum values, 404 for unknown
            family/size, 500 for generation failures.
    """
    fam_enum = _resolve_family(request.family)
    thread_type = _resolve_enum(
        request.thread_type,
        ThreadType,
        "thread_type",
    )
    hand = _resolve_enum(request.hand, ThreadHand, "hand")
    process = _resolve_enum(request.process, PrintProcess, "process")
    tol_class = _resolve_enum(
        request.tolerance_class,
        ToleranceClass,
        "tolerance_class",
    )

    ps_enum: PitchSeries | None = None
    if request.pitch_series is not None:
        ps_enum = _resolve_enum(
            request.pitch_series,
            PitchSeries,
            "pitch_series",
        )

    try:
        spec = get_thread_spec(fam_enum, request.size, pitch_series=ps_enum)
    except ThreadDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )

    # Build print config and optimise
    print_config = PrintThreadConfig(
        spec=spec,
        process=process,
        tolerance_class=tol_class,
        thread_type=thread_type,
        nozzle_diameter_mm=request.nozzle_diameter_mm,
        layer_height_mm=request.layer_height_mm,
        use_flat_bottom=request.use_flat_bottom,
        add_lead_in_chamfer=request.add_chamfer,
        custom_clearance_mm=request.custom_clearance_mm,
    )

    print_result = optimize_thread_for_print(print_config)
    rec = print_result.recommendation

    recommendation_resp = PrintRecommendationResponse(
        family=fam_enum.value,
        size=request.size,
        feasibility=rec.feasibility.value,
        min_recommended_size=rec.min_recommended_size,
        recommended_tolerance=rec.recommended_tolerance.value,
        clearance_mm=rec.clearance_mm,
        notes=list(rec.notes),
        orientation_advice=rec.orientation_advice,
        estimated_strength_pct=rec.estimated_strength_pct,
    )

    # Generate using adjusted spec
    gen_config = ThreadGeneratorConfig(
        spec=print_result.adjusted_spec,
        thread_type=thread_type,
        length_mm=request.length_mm,
        hand=hand,
        add_chamfer=request.add_chamfer,
        custom_pitch_mm=None,
        custom_diameter_mm=None,
    )

    gen_response: ThreadGenerateResponse | None = None
    try:
        gen_result = generate_thread(gen_config)
        gen_response = ThreadGenerateResponse(
            success=True,
            metadata=gen_result.metadata,
            generation_time_ms=gen_result.generation_time_ms,
            estimated_face_count=gen_result.estimated_face_count,
            message=f"Generated print-optimized {thread_type.value} {spec.size} thread",
        )
    except ThreadGenerationError as exc:
        logger.warning(
            "Print-optimised generation failed for %s %s: %s",
            fam_enum.value,
            request.size,
            exc.message,
        )

    logger.info(
        "User %s generated print-optimized %s thread %s (%s, %s)",
        current_user.id,
        thread_type.value,
        request.size,
        fam_enum.value,
        process.value,
    )

    return PrintOptimizedGenerateResponse(
        success=gen_response is not None,
        feasibility=rec.feasibility.value,
        adjustments_applied=print_result.adjustments_applied,
        recommendation=recommendation_resp,
        generation_result=gen_response,
        message=(
            gen_response.message
            if gen_response
            else "Print optimization completed but geometry generation failed"
        ),
    )


@router.get(
    "/print-recommendations/{family}/{size:path}",
    response_model=PrintRecommendationResponse,
    summary="Get print feasibility recommendation",
)
async def get_print_recommendation_endpoint(
    family: str,
    size: str,
    process: str = Query("fdm", description="Print process"),
    nozzle_diameter_mm: float = Query(
        0.4,
        gt=0,
        description="FDM nozzle diameter in mm",
    ),
    layer_height_mm: float = Query(
        0.2,
        gt=0,
        description="Layer height in mm",
    ),
) -> PrintRecommendationResponse:
    """Assess whether a thread can be reliably 3D-printed.

    Args:
        family: Thread family identifier.
        size: Thread size label.
        process: Target print process (fdm, sla, sls, mjf).
        nozzle_diameter_mm: FDM nozzle diameter.
        layer_height_mm: Print layer height.

    Returns:
        PrintRecommendationResponse with feasibility rating and advice.

    Raises:
        HTTPException: 400 for invalid process, 404 for unknown
            family/size.
    """
    fam_enum = _resolve_family(family)
    process_enum = _resolve_enum(process, PrintProcess, "process")

    try:
        spec = get_thread_spec(fam_enum, size)
    except ThreadDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )

    rec = get_print_recommendation(
        spec=spec,
        process=process_enum,
        nozzle_diameter_mm=nozzle_diameter_mm,
        layer_height_mm=layer_height_mm,
    )

    return PrintRecommendationResponse(
        family=fam_enum.value,
        size=size,
        feasibility=rec.feasibility.value,
        min_recommended_size=rec.min_recommended_size,
        recommended_tolerance=rec.recommended_tolerance.value,
        clearance_mm=rec.clearance_mm,
        notes=list(rec.notes),
        orientation_advice=rec.orientation_advice,
        estimated_strength_pct=rec.estimated_strength_pct,
    )
