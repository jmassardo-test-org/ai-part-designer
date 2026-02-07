"""
Bill of Materials (BOM) API endpoints.

CRUD operations for BOM items with export functionality.
"""

import csv
import io
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.assembly import (
    Assembly,
    AssemblyComponent,
    BOMItem,
    Vendor,
)
from app.models.user import User

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================


class BOMItemCreate(BaseModel):
    """Request to create/update a BOM item."""

    component_id: UUID
    part_number: str | None = None
    vendor_part_number: str | None = None
    description: str = Field(..., min_length=1)
    category: str = "custom"
    vendor_id: UUID | None = None
    quantity: int = Field(1, ge=1)
    unit_cost: Decimal | None = Field(None, ge=0)
    currency: str = "USD"
    lead_time_days: int | None = Field(None, ge=0)
    minimum_order_quantity: int = Field(1, ge=1)
    notes: str | None = None


class BOMItemUpdate(BaseModel):
    """Request to update a BOM item."""

    part_number: str | None = None
    vendor_part_number: str | None = None
    description: str | None = None
    category: str | None = None
    vendor_id: UUID | None = None
    quantity: int | None = Field(None, ge=1)
    unit_cost: Decimal | None = Field(None, ge=0)
    currency: str | None = None
    lead_time_days: int | None = Field(None, ge=0)
    minimum_order_quantity: int | None = Field(None, ge=1)
    in_stock: bool | None = None
    notes: str | None = None


class BOMItemResponse(BaseModel):
    """Response for a BOM item."""

    id: UUID
    component_id: UUID
    component_name: str
    part_number: str | None
    vendor_part_number: str | None
    description: str
    category: str
    vendor_id: UUID | None
    vendor_name: str | None
    quantity: int
    unit_cost: Decimal | None
    total_cost: Decimal | None
    currency: str
    lead_time_days: int | None
    minimum_order_quantity: int
    in_stock: bool | None
    notes: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class BOMSummary(BaseModel):
    """Summary of BOM for an assembly."""

    total_items: int
    total_quantity: int
    total_cost: Decimal | None
    currency: str
    categories: dict[str, int]  # category -> item count
    longest_lead_time: int | None


class BOMResponse(BaseModel):
    """Full BOM response for an assembly."""

    assembly_id: UUID
    assembly_name: str
    items: list[BOMItemResponse]
    summary: BOMSummary


class VendorResponse(BaseModel):
    """Response for a vendor."""

    id: UUID
    name: str
    display_name: str
    website: str | None
    logo_url: str | None
    categories: list[str]

    class Config:
        from_attributes = True


# ============================================================================
# Vendor Endpoints
# ============================================================================


@router.get("/vendors", response_model=list[VendorResponse])
async def list_vendors(
    db: AsyncSession = Depends(get_db),
) -> list[VendorResponse]:
    """List all active vendors."""
    query = (
        select(Vendor)
        .where(
            Vendor.is_active,
            Vendor.deleted_at.is_(None),
        )
        .order_by(Vendor.display_name)
    )

    result = await db.execute(query)
    vendors = result.scalars().all()

    return [
        VendorResponse(
            id=v.id,
            name=v.name,
            display_name=v.display_name,
            website=v.website,
            logo_url=v.logo_url,
            categories=v.categories or [],
        )
        for v in vendors
    ]


# ============================================================================
# BOM Endpoints
# ============================================================================


@router.get("/assemblies/{assembly_id}/bom", response_model=BOMResponse)
async def get_bom(
    assembly_id: UUID,
    category: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BOMResponse:
    """Get the Bill of Materials for an assembly."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()

    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )

    # Get BOM items with components and vendors
    bom_query = (
        select(BOMItem)
        .options(
            selectinload(BOMItem.component),
            selectinload(BOMItem.vendor),
        )
        .where(BOMItem.assembly_id == assembly_id)
    )

    if category:
        bom_query = bom_query.where(BOMItem.category == category)

    bom_query = bom_query.order_by(BOMItem.category, BOMItem.part_number)

    bom_result = await db.execute(bom_query)
    bom_items = bom_result.scalars().all()

    # Build response items
    items = []
    categories: dict[str, int] = {}
    total_cost = Decimal("0")
    total_quantity = 0
    longest_lead_time = 0

    for item in bom_items:
        item_total = None
        if item.unit_cost is not None:
            item_total = item.unit_cost * item.quantity
            total_cost += item_total

        total_quantity += item.quantity

        if item.lead_time_days and item.lead_time_days > longest_lead_time:
            longest_lead_time = item.lead_time_days

        cat = item.category
        categories[cat] = categories.get(cat, 0) + 1

        items.append(
            BOMItemResponse(
                id=item.id,
                component_id=item.component_id,
                component_name=item.component.name,
                part_number=item.part_number,
                vendor_part_number=item.vendor_part_number,
                description=item.description,
                category=item.category,
                vendor_id=item.vendor_id,
                vendor_name=item.vendor.display_name if item.vendor else None,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                total_cost=item_total,
                currency=item.currency,
                lead_time_days=item.lead_time_days,
                minimum_order_quantity=item.minimum_order_quantity,
                in_stock=item.in_stock,
                notes=item.notes,
                created_at=item.created_at.isoformat(),
                updated_at=item.updated_at.isoformat(),
            )
        )

    summary = BOMSummary(
        total_items=len(items),
        total_quantity=total_quantity,
        total_cost=total_cost if total_cost > 0 else None,
        currency="USD",
        categories=categories,
        longest_lead_time=longest_lead_time if longest_lead_time > 0 else None,
    )

    return BOMResponse(
        assembly_id=assembly.id,
        assembly_name=assembly.name,
        items=items,
        summary=summary,
    )


@router.post(
    "/assemblies/{assembly_id}/bom",
    response_model=BOMItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_bom_item(
    assembly_id: UUID,
    request: BOMItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BOMItemResponse:
    """Add a BOM item for a component."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()

    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )

    # Verify component exists in assembly
    component_query = select(AssemblyComponent).where(
        AssemblyComponent.id == request.component_id,
        AssemblyComponent.assembly_id == assembly_id,
    )
    component_result = await db.execute(component_query)
    component = component_result.scalar_one_or_none()

    if not component:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Component not found in assembly",
        )

    # Check if BOM item already exists for component
    existing_query = select(BOMItem).where(
        BOMItem.component_id == request.component_id,
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BOM item already exists for this component",
        )

    # Verify vendor if provided
    vendor = None
    if request.vendor_id:
        vendor_query = select(Vendor).where(
            Vendor.id == request.vendor_id,
            Vendor.is_active,
        )
        vendor_result = await db.execute(vendor_query)
        vendor = vendor_result.scalar_one_or_none()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor not found",
            )

    bom_item = BOMItem(
        assembly_id=assembly_id,
        component_id=request.component_id,
        vendor_id=request.vendor_id,
        part_number=request.part_number,
        vendor_part_number=request.vendor_part_number,
        description=request.description,
        category=request.category,
        quantity=request.quantity,
        unit_cost=request.unit_cost,
        currency=request.currency,
        lead_time_days=request.lead_time_days,
        minimum_order_quantity=request.minimum_order_quantity,
        notes=request.notes,
    )

    db.add(bom_item)
    await db.commit()
    await db.refresh(bom_item)

    item_total = None
    if bom_item.unit_cost is not None:
        item_total = bom_item.unit_cost * bom_item.quantity

    return BOMItemResponse(
        id=bom_item.id,
        component_id=bom_item.component_id,
        component_name=component.name,
        part_number=bom_item.part_number,
        vendor_part_number=bom_item.vendor_part_number,
        description=bom_item.description,
        category=bom_item.category,
        vendor_id=bom_item.vendor_id,
        vendor_name=vendor.display_name if vendor else None,
        quantity=bom_item.quantity,
        unit_cost=bom_item.unit_cost,
        total_cost=item_total,
        currency=bom_item.currency,
        lead_time_days=bom_item.lead_time_days,
        minimum_order_quantity=bom_item.minimum_order_quantity,
        in_stock=bom_item.in_stock,
        notes=bom_item.notes,
        created_at=bom_item.created_at.isoformat(),
        updated_at=bom_item.updated_at.isoformat(),
    )


@router.put("/assemblies/{assembly_id}/bom/{item_id}", response_model=BOMItemResponse)
async def update_bom_item(
    assembly_id: UUID,
    item_id: UUID,
    request: BOMItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BOMItemResponse:
    """Update a BOM item."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()

    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )

    # Get BOM item
    bom_query = (
        select(BOMItem)
        .options(
            selectinload(BOMItem.component),
            selectinload(BOMItem.vendor),
        )
        .where(
            BOMItem.id == item_id,
            BOMItem.assembly_id == assembly_id,
        )
    )
    bom_result = await db.execute(bom_query)
    bom_item = bom_result.scalar_one_or_none()

    if not bom_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM item not found",
        )

    # Update fields
    if request.part_number is not None:
        bom_item.part_number = request.part_number
    if request.vendor_part_number is not None:
        bom_item.vendor_part_number = request.vendor_part_number
    if request.description is not None:
        bom_item.description = request.description
    if request.category is not None:
        bom_item.category = request.category
    if request.vendor_id is not None:
        bom_item.vendor_id = request.vendor_id
    if request.quantity is not None:
        bom_item.quantity = request.quantity
    if request.unit_cost is not None:
        bom_item.unit_cost = request.unit_cost
        bom_item.last_price_check = datetime.now(UTC)
    if request.currency is not None:
        bom_item.currency = request.currency
    if request.lead_time_days is not None:
        bom_item.lead_time_days = request.lead_time_days
    if request.minimum_order_quantity is not None:
        bom_item.minimum_order_quantity = request.minimum_order_quantity
    if request.in_stock is not None:
        bom_item.in_stock = request.in_stock
    if request.notes is not None:
        bom_item.notes = request.notes

    await db.commit()
    await db.refresh(bom_item)

    item_total = None
    if bom_item.unit_cost is not None:
        item_total = bom_item.unit_cost * bom_item.quantity

    return BOMItemResponse(
        id=bom_item.id,
        component_id=bom_item.component_id,
        component_name=bom_item.component.name,
        part_number=bom_item.part_number,
        vendor_part_number=bom_item.vendor_part_number,
        description=bom_item.description,
        category=bom_item.category,
        vendor_id=bom_item.vendor_id,
        vendor_name=bom_item.vendor.display_name if bom_item.vendor else None,
        quantity=bom_item.quantity,
        unit_cost=bom_item.unit_cost,
        total_cost=item_total,
        currency=bom_item.currency,
        lead_time_days=bom_item.lead_time_days,
        minimum_order_quantity=bom_item.minimum_order_quantity,
        in_stock=bom_item.in_stock,
        notes=bom_item.notes,
        created_at=bom_item.created_at.isoformat(),
        updated_at=bom_item.updated_at.isoformat(),
    )


@router.delete("/assemblies/{assembly_id}/bom/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bom_item(
    assembly_id: UUID,
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a BOM item."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()

    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )

    # Get BOM item
    bom_query = select(BOMItem).where(
        BOMItem.id == item_id,
        BOMItem.assembly_id == assembly_id,
    )
    bom_result = await db.execute(bom_query)
    bom_item = bom_result.scalar_one_or_none()

    if not bom_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM item not found",
        )

    await db.delete(bom_item)
    await db.commit()


# ============================================================================
# Export Endpoints
# ============================================================================


@router.get("/assemblies/{assembly_id}/bom/export/csv")
async def export_bom_csv(
    assembly_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export BOM as CSV file."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()

    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )

    # Get BOM items
    bom_query = (
        select(BOMItem)
        .options(
            selectinload(BOMItem.component),
            selectinload(BOMItem.vendor),
        )
        .where(BOMItem.assembly_id == assembly_id)
        .order_by(BOMItem.category, BOMItem.part_number)
    )
    bom_result = await db.execute(bom_query)
    bom_items = bom_result.scalars().all()

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "Item #",
            "Part Number",
            "Description",
            "Category",
            "Quantity",
            "Unit Cost",
            "Total Cost",
            "Currency",
            "Vendor",
            "Vendor Part Number",
            "Lead Time (Days)",
            "MOQ",
            "In Stock",
            "Notes",
        ]
    )

    # Data rows
    total_cost = Decimal("0")
    for i, item in enumerate(bom_items, 1):
        item_total = ""
        if item.unit_cost is not None:
            item_total_val = item.unit_cost * item.quantity
            total_cost += item_total_val
            item_total = f"{item_total_val:.2f}"

        writer.writerow(
            [
                i,
                item.part_number or "",
                item.description,
                item.category,
                item.quantity,
                f"{item.unit_cost:.4f}" if item.unit_cost else "",
                item_total,
                item.currency,
                item.vendor.display_name if item.vendor else "",
                item.vendor_part_number or "",
                item.lead_time_days or "",
                item.minimum_order_quantity,
                "Yes" if item.in_stock else "No" if item.in_stock is False else "",
                item.notes or "",
            ]
        )

    # Total row
    writer.writerow([])
    writer.writerow(
        ["", "", "", "TOTAL", "", "", f"{total_cost:.2f}", "USD", "", "", "", "", "", ""]
    )

    output.seek(0)

    filename = f"{assembly.name.replace(' ', '_')}_BOM.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/assemblies/{assembly_id}/bom/summary", response_model=BOMSummary)
async def get_bom_summary(
    assembly_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BOMSummary:
    """Get a quick summary of the BOM without full item details."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()

    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )

    # Get aggregated data
    bom_query = select(BOMItem).where(BOMItem.assembly_id == assembly_id)
    bom_result = await db.execute(bom_query)
    bom_items = bom_result.scalars().all()

    categories: dict[str, int] = {}
    total_cost = Decimal("0")
    total_quantity = 0
    longest_lead_time = 0

    for item in bom_items:
        if item.unit_cost is not None:
            total_cost += item.unit_cost * item.quantity
        total_quantity += item.quantity
        if item.lead_time_days and item.lead_time_days > longest_lead_time:
            longest_lead_time = item.lead_time_days

        cat = item.category
        categories[cat] = categories.get(cat, 0) + 1

    return BOMSummary(
        total_items=len(bom_items),
        total_quantity=total_quantity,
        total_cost=total_cost if total_cost > 0 else None,
        currency="USD",
        categories=categories,
        longest_lead_time=longest_lead_time if longest_lead_time > 0 else None,
    )
