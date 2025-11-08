# apps/api/app/api/v1/endpoints/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any
from app import models, schemas
from app.db.session import get_session
from app.api import deps
import random

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]], include_in_schema=False) 
@router.get("/", response_model=List[Dict[str, Any]])
def read_products(
    db: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
):

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
    db: Session = Depends(get_session),
    # 🚩 **الإصلاح: شيلنا user_id من هنا واستخدمنا current_user من الـ token**
    current_user: models.User = Depends(deps.get_current_active_user),
):
    source_product = db.get(models.Product, product_id)
    if not source_product:
        raise HTTPException(status_code=404, detail="Source product not found")

    # (user_id) دلوقتي بقى موجود جوه (current_user.id)
    # --- بداية اللوجيك الجديد ---
    
    # 1. هنجيب كل الـ IDs بتاعة المنتجات اللي اليوزر ده اشتراها قبل كده
    purchased_product_ids = set()
    try:
        # بنلف على أوردرات اليوزر الحالي
        # (ده بيفترض إن علاقة "orders" في موديل "User" بتتحمل صح)
        for order in current_user.orders:
            for item in order.items:
                purchased_product_ids.add(item.product_id)
    except Exception as e:
        # لو فيه مشكلة في تحميل الأوردرات (زي lazy loading)
        print(f"Could not preload user orders for suggestions: {e}")
            
    # ضيف المنتج الحالي عشان منقترحوش
    purchased_product_ids.add(product_id)

    # 2. اللوجيك الجديد: هنجيب منتجات من "نفس الفئة"
    #    وبشرط إن اليوزر "مش" يكون اشتراها قبل كده
    suggestions = []
    if source_product.category:
        suggestions = db.exec(
            select(models.Product)
            .where(
                models.Product.category == source_product.category, # نفس الفئة
                models.Product.id.notin_(purchased_product_ids)    # مش في المنتجات المشتراة
            )
            .limit(3)
        ).all()
    
    # 3. لو ملقناش حاجة (أو الفئة مفيهاش غيره)، هات أي 3 منتجات تانية وخلاص
    if not suggestions or len(suggestions) < 3:
        needed = 3 - len(suggestions)
        fallback_suggestions = db.exec(
            select(models.Product)
            .where(models.Product.id.notin_(purchased_product_ids)) # برضه من غير اللي اشتراه
            .limit(needed)
        ).all()
        suggestions.extend(fallback_suggestions)
        
    # --- نهاية اللوجيك الجديد ---

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
