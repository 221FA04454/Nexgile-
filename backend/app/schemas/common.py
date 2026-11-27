from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class Lineage(BaseModel):
    source: str = "book_of_record"
    provider: str = "internal"
    as_of: str = "2026-09-07"
    updated_at: str
    version: int = 1


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str
    phone: str = ""
    accept_terms: bool = False


class EmailRequest(BaseModel):
    email: str


class VerifyEmailRequest(BaseModel):
    token: str = ""
    otp: str = ""


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    confirm_password: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class RebalanceRequest(BaseModel):
    portfolio_id: int = 1


class ApprovalCreate(BaseModel):
    action: str
    entity_type: str
    entity_id: str = ""
    notes: str = ""
    new_value: dict = Field(default_factory=dict)


class ApprovalDecide(BaseModel):
    status: str
    notes: str = ""


class DocumentUploadMeta(BaseModel):
    name: str
    category: str = "Other"
    owner: str = "Alex Morgan"
