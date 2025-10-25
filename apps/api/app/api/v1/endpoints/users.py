from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlmodel import Session
from pydantic import BaseModel, Field
import shutil
import os
from pathlib import Path

from app import models
from app.schemas.user import UserRead, UserCreate, UserUpdate
from app.schemas.msg import Msg
from app.api import deps
from app.crud import crud_user
from app.db.session import get_session
from app.core import security

router = APIRouter()

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    *,
    session: Session = Depends(get_session),
    user_in: UserCreate,
):
    user = crud_user.user.get_by_email(db=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )

    hashed_password = security.get_password_hash(user_in.password)
    user_create_data = user_in.model_dump(exclude={"password"})
    user_create_data["hashed_password"] = hashed_password

    db_user = models.User(**user_create_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@router.get("/me", response_model=UserRead)
def read_user_me(
    current_user: models.User = Depends(deps.get_current_active_user),
):
    return current_user

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

@router.post("/me/change-password", response_model=Msg, status_code=status.HTTP_200_OK)
def change_user_password(
    *,
    session: Session = Depends(get_session),
    password_data: ChangePasswordRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    if not current_user.hashed_password or not security.verify_password(
        password_data.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password",
        )

    new_hashed_password = security.get_password_hash(password_data.new_password)

    current_user.hashed_password = new_hashed_password
    session.add(current_user)
    session.commit()

    return {"msg": "Password updated successfully"}

STATIC_DIR = Path("static")
AVATARS_DIR = STATIC_DIR / "avatars"
AVATARS_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/me/avatar", response_model=UserRead)
async def upload_user_avatar(
    *,
    request: Request,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(deps.get_current_active_user),
    file: UploadFile = File(...)
):
    if not file.content_type.startswith("image/"):
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image.")

    file_extension = Path(file.filename or "image.jpg").suffix
    safe_filename = f"user_{current_user.id}{file_extension}"
    file_path = AVATARS_DIR / safe_filename

    try:
        with file_path.open("wb") as buffer:
             shutil.copyfileobj(file.file, buffer)
    except Exception as e:
         print(f"Error saving file: {e}")
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save avatar file.")
    finally:
         await file.close()

    base_url = str(request.base_url).rstrip('/')
    avatar_url_path = f"{base_url}/static/avatars/{safe_filename}"

    current_user.avatar_url = avatar_url_path
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return current_user

@router.get("/me/export-data", response_model=UserRead)
def export_user_data(
    current_user: models.User = Depends(deps.get_current_active_user),
):
    return current_user

@router.delete("/me/delete-account", response_model=Msg, status_code=status.HTTP_200_OK)
def delete_account(
    *,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID not found")

    success = crud_user.user.remove(db=session, id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"msg": "Account deletion process has been initiated."}

@router.put("/me", response_model= UserRead)
def update_user_me(
    *,
    session: Session = Depends(get_session),
    user_in: UserUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    update_data = user_in.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        hashed_password = security.get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
    elif "password" in update_data:
         del update_data["password"]

    current_user.sqlmodel_update(update_data)

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user
