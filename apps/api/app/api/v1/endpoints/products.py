# file: apps/api/app/api/v1/endpoints/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any
from app import models, schemas
from app.db.session import get_session
from app.api import deps
import random

router = APIRouter()

#@router.get("/", response_model=List[Dict[str, Any]])
@router.get("", response_model=List[Dict[str, Any]], include_in_schema=False) 
@router.get("/", response_model=List[Dict[str, Any]])
def read_products(
    db: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve all products, enriched with dynamic data and correct image paths.
    """
    products_from_db = db.exec(select(models.Product).offset(skip).limit(limit)).all()
    
    enriched_products = []
    for p in products_from_db:
        data = p.model_dump()
        
        if not data.get("image_url"):
            data["image_url"] = "/images/default.jpeg"
        
        data["predicted_delivery"] = f"{random.randint(8, 25)} mins near your zone."
        data["trending_status"] = "Trending in your region 🚀" if p.inventory < 80 and random.choice([True, False]) else None
        data["stock_level"] = f"Low stock – {p.inventory} left." if p.inventory < 20 else None
        
        enriched_products.append(data)
        
    return enriched_products

@router.post("/", response_model=schemas.Product, status_code=201)
def create_product(
    *,
    db: Session = Depends(get_session),
    product_in: schemas.ProductCreate,
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    db_product = models.Product.model_validate(product_in)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/suggestions", response_model=List[Dict[str, Any]])
def get_product_suggestions(
    product_id: int,
    user_id: int, 
    db: Session = Depends(get_session),
):
    source_product = db.get(models.Product, product_id)
    if not source_product:
        raise HTTPException(status_code=404, detail="Source product not found")

    suggestions = db.exec(select(models.Product).where(models.Product.id != product_id).limit(3)).all()

    formatted_suggestions = []
    for p in suggestions:
        data = p.model_dump()
        
        if not data.get("image_url"):
            data["image_url"] = "/images/default.jpeg"
            
        data["rating"] = round(random.uniform(4.5, 5.0), 1)
        data["reviews"] = random.randint(500, 2000)
        data["delivery_eta"] = "Instant"
        data["stock_status"] = "In Stock"
        formatted_suggestions.append(data)
        
    return formatted_suggestions
