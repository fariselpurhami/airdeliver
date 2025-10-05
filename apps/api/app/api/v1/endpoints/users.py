from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session  

from app import schemas
from app.api import deps
from app.crud import crud_user
from app.db.session import get_session
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=schemas.User, status_code=201)
def create_user(
    *,
    session: Session = Depends(get_session),
    user_in: schemas.UserCreate,
):
    """
    Create new user.
    """
    user = crud_user.user.get_by_email(db=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
       
       )
    new_user = crud_user.user.create(db=session, obj_in=user_in)
    return new_user


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
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    GDPR/CCPA: Allow a user to delete their account.
    """
    crud_user.user.remove(db, id=current_user.id)
    return {"msg": "Account deletion process has been initiated."}


