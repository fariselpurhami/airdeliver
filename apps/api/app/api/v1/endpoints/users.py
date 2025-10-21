# file: apps/api/app/api/v1/endpoints/users.py (النسخة النهائية الكاملة والآمنة)

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

# --- تم تصحيح الـ imports هنا ---
from app import schemas
from app.api import deps
from app.models import User             # User model is in app.models
from app.schemas import UserCreate    # UserCreate schema is in app.schemas
from app.core.security import get_password_hash

router = APIRouter()

@router.post("", response_model=User, status_code=201)
def create_user(
    *,
    db: Session = Depends(deps.get_session),
    user_in: UserCreate, # This now correctly uses the imported UserCreate schema
):
    """
    Create a new user securely with a hashed password.
    """
    user = db.exec(select(User).where(User.email == user_in.email)).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    hashed_password = get_password_hash(user_in.password)
    
    user = User.model_validate(user_in, update={"hashed_password": hashed_password})
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/export-data", response_model=User)
def export_user_data(
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    GDPR/CCPA: Allow a user to export their data.
    """
    return current_user

@router.delete("/me/delete-account", response_model=schemas.Msg)
def delete_account(
    *,
    db: Session = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    GDPR/CCPA: Allow a user to delete their account.
    """
    db.delete(current_user)
    db.commit()
    return {"msg": "Account deletion process has been initiated."}
