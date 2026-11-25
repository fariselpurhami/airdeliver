"""Inactive C01 preparation models. No endpoint opts into these tables yet."""
from datetime import datetime
from sqlmodel import SQLModel,Field
from sqlalchemy import Column,DateTime

class AuthSession(SQLModel,table=True):
    __tablename__='auth_sessions'
    id:str=Field(primary_key=True,max_length=64)
    user_id:int=Field(foreign_key='users.id',index=True)
    expires_at:datetime=Field(sa_column=Column(DateTime(timezone=True),nullable=False))
    revoked_at:datetime|None=Field(default=None,sa_column=Column(DateTime(timezone=True)))

class RefreshCredential(SQLModel,table=True):
    __tablename__='refresh_credentials'
    digest:str=Field(primary_key=True,max_length=64)
    session_id:str=Field(foreign_key='auth_sessions.id',index=True)
    used_at:datetime|None=Field(default=None,sa_column=Column(DateTime(timezone=True)))
