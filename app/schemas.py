"""
Pydantic schemas for Sleep Consultation AI API
Separate schemas for better organization and maintainability.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel

# Request schemas
class ChatRequest(BaseModel):
    auth_token: str
    message: str

class HealthCheckResponse(BaseModel):
    status: str
    service: str
    version: str
    database_status: str
    active_sessions: int
    total_consultations: int
    uptime_seconds: Optional[float] = None

# Response schemas
class ChatResponse(BaseModel):
    bot_response: str
    conversation_complete: bool
    doctor_summary: Optional[str] = None
    patient_summary: Optional[str] = None
    urgency_level: Optional[str] = None
    questions_answered: int
    success: bool
    error: Optional[str] = None

class ReferralLetterResponse(BaseModel):
    auth_token: Optional[str] = None
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    referral_date: Optional[str] = None
    referred_to: Optional[str] = None
    referral_reason: Optional[str] = None
    success: bool
    error: Optional[str] = None

class ConsultationSearchResponse(BaseModel):
    consultations: List[Dict[str, Any]]
    total_count: int
    success: bool

class ConsultationDetailsResponse(BaseModel):
    consultation: Optional[Dict[str, Any]] = None
    success: bool
    error: Optional[str] = None

class StatisticsResponse(BaseModel):
    total_consultations: int
    completed_consultations: int
    pending_consultations: int
    urgency_breakdown: Dict[str, int]
    success: bool
    error: Optional[str] = None

# Error schemas
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_code: Optional[str] = None