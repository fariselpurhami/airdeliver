# file: apps/api/app/api/v1/endpoints/products.py
from app.core.config import settings
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List
from app import models
from app.models import Product, User
from app import schemas
from app.db.session import get_session
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[schemas.Product])
def read_products(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
):
    
    """
    Retrieve all products from the database.
    """
    products = session.exec(select(models.Product).offset(skip).limit(limit)).all()
    return products


@router.post("/", response_model=schemas.Product, status_code=201)
def create_product(
    *,
    session: Session = Depends(get_session),
    product_in: schemas.ProductCreate,
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    """
    Create a new product (Admin only).
    """
    db_product = models.Product.model_validate(product_in)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product
