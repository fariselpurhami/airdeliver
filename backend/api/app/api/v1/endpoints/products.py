# backend/api/app/api/v1/endpoints/products.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Annotated, List, Dict, Any, Optional
from app import models, schemas
from app.db.session import get_async_session
from app.api import deps

from app.services.product_serialization import serialize_product
from app.services.catalog_visibility import is_catalog_hidden,real_catalog_predicates

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]], include_in_schema=False)
@router.get("/", response_model=List[Dict[str, Any]])
async def read_products(
    db: AsyncSession = Depends(get_async_session),
    skip: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    page: Annotated[Optional[int], Query(ge=1, le=100001)] = None,
    category: Optional[str] = None,
):
    # The storefront sends page/limit/category; honor page (1-based) as an
    # alias for skip and apply the category filter when provided.
    if page is not None:
        skip = (page - 1) * limit
    if skip > 100000:
        raise HTTPException(status_code=422, detail="Pagination offset exceeds the supported window")

    stmt = select(models.Product).where(models.Product.is_active.is_(True),*real_catalog_predicates(models.Product))
    if category:
        stmt = stmt.where(models.Product.category == category)

    products_from_db = (
        await db.execute(stmt.offset(skip).limit(limit))
    ).scalars().all()

    enriched_products = []
    for p in products_from_db:
        if is_catalog_hidden(p):continue
        data = serialize_product(p)


        data["stock_level"] = (
            f"Low stock – {p.inventory} left." if p.inventory < 20 else None
        )

        enriched_products.append(data)

    return enriched_products


@router.post("/", response_model=schemas.Product, status_code=201)
async def create_product(
    *,
    db: AsyncSession = Depends(get_async_session),
    product_in: schemas.ProductCreate,
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    db_product = models.Product.model_validate(product_in)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.get("/suggestions", response_model=List[Dict[str, Any]])
async def get_product_suggestions(
    product_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    source_product = await db.get(models.Product, product_id)
    if not source_product or is_catalog_hidden(source_product):
        raise HTTPException(status_code=404, detail="Source product not found")

    purchased_product_ids = set()
    try:
        for order in current_user.orders:
            for item in order.items:
                purchased_product_ids.add(item.product_id)
    except Exception as e:
        print(f"Could not preload user orders for suggestions: {e}")

    purchased_product_ids.add(product_id)

    suggestions = []
    if source_product.category:
        # 🚀 التعديل هنا: إضافة .scalars()
        suggestions = (
            await db.execute(
                select(models.Product)
                .where(models.Product.is_active.is_(True),*real_catalog_predicates(models.Product))
                .where(
                    models.Product.category == source_product.category,
                    models.Product.id.notin_(purchased_product_ids),
                )
                .limit(3)
            )
        ).scalars().all()

    if not suggestions or len(suggestions) < 3:
        needed = 3 - len(suggestions)
        # 🚀 التعديل هنا: إضافة .scalars()
        fallback_suggestions = (
            await db.execute(
                select(models.Product)
                .where(models.Product.is_active.is_(True),*real_catalog_predicates(models.Product))
                .where(models.Product.id.notin_(purchased_product_ids))
                .limit(needed)
            )
        ).scalars().all()
        suggestions.extend(fallback_suggestions)

    formatted_suggestions = []
    for p in suggestions:
        if is_catalog_hidden(p):continue
        data = serialize_product(p)


        data["stock_status"] = "In Stock" if p.inventory > 0 else "Out of Stock"
        formatted_suggestions.append(data)

    return formatted_suggestions


@router.get("/featured-recommendation", response_model=Dict[str, Any])
async def get_featured_recommendation(
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        select(models.Product).where(models.Product.is_active.is_(True),*real_catalog_predicates(models.Product)).order_by(models.Product.inventory.asc()).limit(1)
    )
    # 🚀 التعديل هنا: إضافة .scalars() قبل .first()
    featured_product = result.scalars().first()

    if not featured_product or is_catalog_hidden(featured_product):
        raise HTTPException(
            status_code=404, detail="No products available to feature"
        )

    data = serialize_product(featured_product)


    data["stock_level"] = f"Low stock – {featured_product.inventory} left."

    return data

