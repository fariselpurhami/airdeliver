from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app import models
from app.schemas.user import UserRead, UserCreate
from app.schemas.msg import Msg
from app.api import deps
from app.crud import crud_user
from app.db.session import get_session
from app.core.security import get_password_hash

router = APIRouter()

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    *,
    session: Session = Depends(get_session),
    user_in: UserCreate,
):
    """
    Create new user.
    """
    user = crud_user.user.get_by_email(db=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )

    hashed_password = get_password_hash(user_in.password)
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
    """
    Get current user details. Returns all fields defined in UserRead schema.
    """
    return current_user

@router.get("/me/export-data", response_model=UserRead)
def export_user_data(
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    GDPR/CCPA: Allow a user to export their data.
    """
    return current_user

@router.delete("/me/delete-account", response_model=Msg, status_code=status.HTTP_200_OK)
def delete_account(
    *,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    GDPR/CCPA: Allow a user to delete their account.
    """
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID not found")

    success = crud_user.user.remove(db=session, id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"msg": "Account deletion process has been initiated."}
