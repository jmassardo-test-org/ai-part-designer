"""
End-to-end CAD generation from natural language.

Uses a reasoning-first approach:
1. Understand - Deep analysis of what the user wants
2. Plan - Create a step-by-step build plan  
3. Generate - Execute the plan with CadQuery code
4. Validate - Verify the result matches intent

Example:
    >>> from app.ai.generator import generate_from_description
    >>> result = await generate_from_description("Create a mounting bracket with holes")
    >>> print(result.step_path)  # Path to generated STEP file
"""

from __future__ import annotations

import logging
import re
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cadquery as cq

from app.ai.codegen import generate_cadquery_code, CodeGenerationResult
from app.ai.exceptions import AIValidationError
from app.ai.reasoning import reason_and_plan, PartIntent, BuildPlan, generate_step_code, validate_result
from app.cad.export import export_step, export_stl, ExportQuality

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """
    Result of end-to-end CAD generation.
    
    Contains generated geometry, export paths, and timing info.
    """
    
    # Generation info
    description: str
    shape: cq.Workplane | None = None
    generated_code: str | None = None  # The AI-generated CadQuery code
    
    # Reasoning info
    intent: PartIntent | None = None
    build_plan: BuildPlan | None = None
    
    # Export files
    step_data: bytes | None = None
    stl_data: bytes | None = None
    step_path: Path | None = None
    stl_path: Path | None = None
    
    # Timing
    reasoning_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    export_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Metadata
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    warnings: list[str] = field(default_factory=list)
    
    # Validation
    validation_result: dict[str, Any] | None = None
    
    # For API compatibility
    confidence: float = 0.9
    shape_type: str = "custom"
    dimensions: dict[str, float] = field(default_factory=dict)
    
    @property
    def is_successful(self) -> bool:
        """Check if generation completed successfully."""
        return self.shape is not None and (self.step_data is not None or self.stl_data is not None)
    
    def get_stats(self) -> dict[str, Any]:
        """Get generation statistics."""
        return {
            "job_id": self.job_id,
            "shape": self.shape_type,
            "confidence": self.confidence,
            "reasoning_time_ms": round(self.reasoning_time_ms, 1),
            "generation_time_ms": round(self.generation_time_ms, 1),
            "execution_time_ms": round(self.execution_time_ms, 1),
            "export_time_ms": round(self.export_time_ms, 1),
            "total_time_ms": round(self.total_time_ms, 1),
            "has_step": self.step_data is not None,
            "has_stl": self.stl_data is not None,
            "warnings": self.warnings,
        }
    
    # Backward compatibility properties
    @property
    def parse_time_ms(self) -> float:
        return self.reasoning_time_ms + self.generation_time_ms
    
    @property
    def generate_time_ms(self) -> float:
        return self.execution_time_ms


async def generate_from_description(
    description: str,
    *,
    output_dir: Path | str | None = None,
    export_step: bool = True,
    export_stl: bool = True,
    stl_quality: ExportQuality | str = ExportQuality.STANDARD,
    job_id: str | None = None,
    use_reasoning: bool = True,
) -> GenerationResult:
    """
    Generate CAD file from natural language description.
    
    Uses a reasoning-first pipeline:
    1. Understand - Deep analysis of user intent
    2. Plan - Create step-by-step build plan
    3. Generate - Execute plan with CadQuery code
    4. Validate - Verify result matches intent
    
    Args:
        description: Natural language part description
        output_dir: Directory for output files (default: temp dir)
        export_step: Whether to export STEP file
        export_stl: Whether to export STL file
        stl_quality: Quality preset for STL export
        job_id: Optional job ID for tracking
        use_reasoning: Use reasoning pipeline (default True)
    
    Returns:
        GenerationResult with geometry and export files
    """
    total_start = time.monotonic()
    warnings: list[str] = []
    job_id = job_id or str(uuid.uuid4())
    
    logger.info(f"Starting generation job {job_id}: {description[:100]}...")
    
    shape = None
    generated_code = None
    intent = None
    build_plan = None
    reasoning_time_ms = 0.0
    generation_time_ms = 0.0
    execution_time_ms = 0.0
    validation_result = None
    
    # =========================================================================
    # STEP 1: Reasoning - Understand and Plan
    # =========================================================================
    if use_reasoning:
        reasoning_start = time.monotonic()
        try:
            intent, build_plan = await reason_and_plan(description)
            reasoning_time_ms = (time.monotonic() - reasoning_start) * 1000
            
            logger.info(
                f"Reasoning complete in {reasoning_time_ms:.0f}ms: "
                f"part_type={intent.part_type}, confidence={intent.confidence}, "
                f"steps={len(build_plan.steps)}"
            )
            
            # Add any assumptions made as warnings
            if intent.assumptions_made:
                warnings.extend([f"Assumption: {a}" for a in intent.assumptions_made])
            
            # Add clarifications needed as warnings
            if intent.clarifications_needed:
                warnings.extend([f"Note: {c}" for c in intent.clarifications_needed])
                
        except Exception as e:
            logger.warning(f"Reasoning failed: {e}, falling back to direct generation")
            reasoning_time_ms = (time.monotonic() - reasoning_start) * 1000
            use_reasoning = False  # Fall back
    
    # =========================================================================
    # STEP 2: Generation - Execute the plan or use direct code generation
    # =========================================================================
    gen_start = time.monotonic()
    
    # Use direct AI code generation (will be enhanced to use build_plan)
    code_result = await generate_cadquery_code(description, intent=intent, build_plan=build_plan)
    
    generation_time_ms = code_result.generation_time_ms
    execution_time_ms = code_result.execution_time_ms
    
    if code_result.error:
        logger.error(f"Code generation failed: {code_result.error}")
        raise AIValidationError(f"Failed to generate CAD: {code_result.error}")
    
    if code_result.shape is None:
        raise AIValidationError("Generated code did not produce a valid shape")
    
    shape = code_result.shape
    generated_code = code_result.code
    
    # Add any adjustments made during generation
    if code_result.adjustments:
        warnings.extend(code_result.adjustments)
    
    # =========================================================================
    # STEP 3: Validation - Verify result matches intent
    # =========================================================================
    if use_reasoning and intent:
        try:
            validation_result = await validate_result(description, intent, shape)
            
            if not validation_result.get("is_valid", True):
                warnings.extend(validation_result.get("issues", []))
                logger.warning(f"Validation issues: {validation_result.get('issues')}")
                
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
    
    # =========================================================================
    # STEP 4: Export
    # =========================================================================
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Path(tempfile.gettempdir()) / "cad_exports"
    output_path.mkdir(parents=True, exist_ok=True)
    
    export_start = time.monotonic()
    
    base_name = f"custom_{job_id[:8]}"
    
    step_data = None
    stl_data = None
    step_path = None
    stl_path = None
    
    if export_step:
        from app.cad.export import export_step as do_export_step
        step_data = do_export_step(shape, product_name=description[:50])
        step_path = output_path / f"{base_name}.step"
        step_path.write_bytes(step_data)
    
    if export_stl:
        from app.cad.export import export_stl as do_export_stl
        stl_data = do_export_stl(shape, quality=stl_quality)
        stl_path = output_path / f"{base_name}.stl"
        stl_path.write_bytes(stl_data)
    
    export_time_ms = (time.monotonic() - export_start) * 1000
    total_time_ms = (time.monotonic() - total_start) * 1000
    
    logger.info(
        f"Generation complete in {total_time_ms:.0f}ms "
        f"(reason: {reasoning_time_ms:.0f}ms, gen: {generation_time_ms:.0f}ms, "
        f"exec: {execution_time_ms:.0f}ms, export: {export_time_ms:.0f}ms)"
    )
    
    # Set confidence from intent or validation
    confidence = 0.9
    if intent:
        confidence = intent.confidence
    if validation_result:
        confidence = min(confidence, validation_result.get("confidence", 0.9))
    
    return GenerationResult(
        description=description,
        shape=shape,
        generated_code=generated_code,
        intent=intent,
        build_plan=build_plan,
        step_data=step_data,
        stl_data=stl_data,
        step_path=step_path,
        stl_path=stl_path,
        reasoning_time_ms=reasoning_time_ms,
        generation_time_ms=generation_time_ms,
        execution_time_ms=execution_time_ms,
        export_time_ms=export_time_ms,
        total_time_ms=total_time_ms,
        job_id=job_id,
        warnings=warnings,
        validation_result=validation_result,
        confidence=confidence,
        shape_type=intent.part_type if intent else "custom",
        dimensions=intent.overall_dimensions if intent else {},
    )
