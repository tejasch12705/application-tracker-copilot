"""
Pydantic models for Application Tracker Copilot.
Keep this schema intentionally minimal — resist the urge to add fields
until a real use case demands them.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    OA_TAKEHOME = "oa_takehome"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationCreate(BaseModel):
    company: str
    role: str
    jd_text: Optional[str] = None
    deadline: Optional[datetime] = None
    status: ApplicationStatus = ApplicationStatus.APPLIED
    notes: Optional[str] = None
    key_requirements: Optional[List[str]] = None


class ApplicationUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    deadline: Optional[datetime] = None
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None
    key_requirements: Optional[List[str]] = None


class ApplicationOut(BaseModel):
    id: str = Field(alias="_id")
    company: str
    role: str
    jd_text: Optional[str] = None
    deadline: Optional[datetime] = None
    status: ApplicationStatus
    notes: Optional[str] = None
    key_requirements: Optional[List[str]] = None
    created_at: datetime

    class Config:
        populate_by_name = True


class ParseJDRequest(BaseModel):
    jd_text: str


class ParseJDResponse(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    deadline: Optional[str] = None  # raw string; we don't trust the LLM to always emit valid ISO
    key_requirements: List[str] = []


class GenerateAnswerRequest(BaseModel):
    question: str
    application_id: Optional[str] = None  # if provided, use that JD's context too


class GenerateAnswerResponse(BaseModel):
    answer: str
    sources_used: List[str]
