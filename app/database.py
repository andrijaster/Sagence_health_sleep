"""
Database models and operations for Sleep Consultation AI
Uses SQLite for simplicity with SQLAlchemy ORM
"""

import sqlite3
import json
import secrets
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, or_, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database setup
DATABASE_URL = "sqlite:///sleep_consultation.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ReferralLetter(Base):
    __tablename__ = "referral_letters"
    
    id = Column(Integer, primary_key=True, index=True)
    auth_token = Column(String(64), unique=True, index=True)
    patient_name = Column(String(255))
    doctor_name = Column(String(255))
    referral_date = Column(String(50))
    referred_to = Column(String(255))
    referral_reason = Column(Text)
    pdf_path = Column(String(500))  # Path to saved PDF file
    extracted_data = Column(JSON)  # Full extracted data as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    is_used = Column(Boolean, default=False)  # Token used flag

class Consultation(Base):
    __tablename__ = "consultations"
    
    id = Column(Integer, primary_key=True, index=True)
    auth_token = Column(String(64), index=True)
    session_id = Column(String(100))
    patient_name = Column(String(255))
    conversation_history = Column(JSON)  # All messages
    doctor_summary = Column(Text)
    patient_summary = Column(Text)
    urgency_level = Column(String(20))
    questions_answered = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer)
    auth_token = Column(String(64), index=True)
    message_type = Column(String(10))  # 'human' or 'ai'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

class DatabaseManager:
    def __init__(self):
        self.engine = engine
    
    def get_db(self) -> Session:
        """Get database session"""
        db = SessionLocal()
        try:
            return db
        finally:
            pass  # Don't close here, let caller handle it
    
    def generate_auth_token(self) -> str:
        """Generate secure auth token"""
        return secrets.token_urlsafe(48)
    
    def save_referral_letter(self, pdf_path: str, extracted_data: Dict[str, Any]) -> str:
        """Save referral letter and return auth token"""
        db = self.get_db()
        try:
            auth_token = self.generate_auth_token()
            
            referral = ReferralLetter(
                auth_token=auth_token,
                patient_name=extracted_data.get("patient_name"),
                doctor_name=extracted_data.get("doctor_name"),
                referral_date=extracted_data.get("referral_date"),
                referred_to=extracted_data.get("referred_to"),
                referral_reason=extracted_data.get("referral_reason"),
                pdf_path=pdf_path,
                extracted_data=extracted_data,
                is_used=False
            )
            
            db.add(referral)
            db.commit()
            db.refresh(referral)
            
            return auth_token
        finally:
            db.close()
    
    def get_referral_by_token(self, auth_token: str) -> Optional[ReferralLetter]:
        """Get referral letter by auth token"""
        db = self.get_db()
        try:
            return db.query(ReferralLetter).filter(ReferralLetter.auth_token == auth_token).first()
        finally:
            db.close()
    
    def is_token_valid(self, auth_token: str) -> bool:
        """Check if auth token is valid and not used"""
        db = self.get_db()
        try:
            referral = db.query(ReferralLetter).filter(
                ReferralLetter.auth_token == auth_token,
                ReferralLetter.is_used == False
            ).first()
            return referral is not None
        finally:
            db.close()
    
    def mark_token_used(self, auth_token: str):
        """Mark auth token as used"""
        db = self.get_db()
        try:
            referral = db.query(ReferralLetter).filter(ReferralLetter.auth_token == auth_token).first()
            if referral:
                referral.is_used = True
                db.commit()
        finally:
            db.close()
    
    def create_consultation(self, auth_token: str, session_id: str, patient_name: str) -> int:
        """Create new consultation record"""
        db = self.get_db()
        try:
            consultation = Consultation(
                auth_token=auth_token,
                session_id=session_id,
                patient_name=patient_name,
                conversation_history=[],
                is_completed=False
            )
            
            db.add(consultation)
            db.commit()
            db.refresh(consultation)
            
            return consultation.id
        finally:
            db.close()
    
    def get_consultation_by_token(self, auth_token: str) -> Optional[Consultation]:
        """Get consultation by auth token"""
        db = self.get_db()
        try:
            return db.query(Consultation).filter(Consultation.auth_token == auth_token).first()
        finally:
            db.close()
    
    def save_message(self, consultation_id: int, auth_token: str, message_type: str, content: str):
        """Save individual message"""
        db = self.get_db()
        try:
            message = Message(
                consultation_id=consultation_id,
                auth_token=auth_token,
                message_type=message_type,
                content=content
            )
            
            db.add(message)
            db.commit()
        finally:
            db.close()
    
    def update_consultation(self, auth_token: str, conversation_history: List[Dict], 
                          questions_answered: int, doctor_summary: str = None, 
                          patient_summary: str = None, urgency_level: str = None, 
                          is_completed: bool = False):
        """Update consultation with latest data"""
        db = self.get_db()
        try:
            consultation = db.query(Consultation).filter(Consultation.auth_token == auth_token).first()
            if consultation:
                consultation.conversation_history = conversation_history
                consultation.questions_answered = questions_answered
                
                if doctor_summary:
                    consultation.doctor_summary = doctor_summary
                if patient_summary:
                    consultation.patient_summary = patient_summary
                if urgency_level:
                    consultation.urgency_level = urgency_level
                if is_completed:
                    consultation.is_completed = True
                    consultation.completed_at = datetime.utcnow()
                
                db.commit()
        finally:
            db.close()
    
    def get_consultation_history(self, auth_token: str) -> List[Dict]:
        """Get all messages for a consultation"""
        db = self.get_db()
        try:
            messages = db.query(Message).filter(Message.auth_token == auth_token).order_by(Message.timestamp).all()
            return [
                {
                    "type": msg.message_type,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        finally:
            db.close()
    
    def search_consultations(self, patient_name: str = None, patient_id: int = None, 
                           start_date: str = None, end_date: str = None, 
                           sort_by: str = "created_at", sort_order: str = "desc") -> List[Dict]:
        """Search and filter consultations with sorting"""
        db = self.get_db()
        try:
            query = db.query(Consultation)
            
            # Apply filters
            if patient_name:
                query = query.filter(Consultation.patient_name.ilike(f"%{patient_name}%"))
            
            if patient_id:
                query = query.filter(Consultation.id == patient_id)
            
            if start_date:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(Consultation.started_at >= start_dt)
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date)
                query = query.filter(Consultation.started_at <= end_dt)
            
            # Apply sorting
            if sort_by == "patient_name":
                order_col = Consultation.patient_name
            elif sort_by == "completed_at":
                order_col = Consultation.completed_at
            elif sort_by == "urgency_level":
                order_col = Consultation.urgency_level
            else:
                order_col = Consultation.started_at
            
            if sort_order.lower() == "asc":
                query = query.order_by(order_col.asc())
            else:
                query = query.order_by(order_col.desc())
            
            consultations = query.all()
            
            return [
                {
                    "id": c.id,
                    "auth_token": c.auth_token,
                    "patient_name": c.patient_name,
                    "is_completed": c.is_completed,
                    "questions_answered": c.questions_answered,
                    "urgency_level": c.urgency_level,
                    "doctor_summary": c.doctor_summary,
                    "patient_summary": c.patient_summary,
                    "started_at": c.started_at.isoformat() if c.started_at else None,
                    "completed_at": c.completed_at.isoformat() if c.completed_at else None
                }
                for c in consultations
            ]
        finally:
            db.close()
    
    def get_consultation_details(self, consultation_id: int) -> Optional[Dict]:
        """Get complete consultation details including referral letter and messages"""
        db = self.get_db()
        try:
            consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
            if not consultation:
                return None
            
            # Get referral letter
            referral = db.query(ReferralLetter).filter(ReferralLetter.auth_token == consultation.auth_token).first()
            
            # Get all messages
            messages = db.query(Message).filter(Message.auth_token == consultation.auth_token).order_by(Message.timestamp).all()
            
            return {
                "consultation": {
                    "id": consultation.id,
                    "auth_token": consultation.auth_token,
                    "session_id": consultation.session_id,
                    "patient_name": consultation.patient_name,
                    "doctor_summary": consultation.doctor_summary,
                    "patient_summary": consultation.patient_summary,
                    "urgency_level": consultation.urgency_level,
                    "questions_answered": consultation.questions_answered,
                    "is_completed": consultation.is_completed,
                    "started_at": consultation.started_at.isoformat() if consultation.started_at else None,
                    "completed_at": consultation.completed_at.isoformat() if consultation.completed_at else None
                },
                "referral_letter": {
                    "patient_name": referral.patient_name if referral else None,
                    "doctor_name": referral.doctor_name if referral else None,
                    "referral_date": referral.referral_date if referral else None,
                    "referred_to": referral.referred_to if referral else None,
                    "referral_reason": referral.referral_reason if referral else None,
                    "pdf_path": referral.pdf_path if referral else None,
                    "created_at": referral.created_at.isoformat() if referral and referral.created_at else None
                },
                "messages": [
                    {
                        "id": msg.id,
                        "type": msg.message_type,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in messages
                ]
            }
        finally:
            db.close()
    
    def get_all_consultations(self) -> List[Dict]:
        """Get all consultations (admin function)"""
        return self.search_consultations()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        db = self.get_db()
        try:
            total_consultations = db.query(Consultation).count()
            completed_consultations = db.query(Consultation).filter(Consultation.is_completed == True).count()
            pending_consultations = total_consultations - completed_consultations
            
            # Urgency level breakdown
            high_urgency = db.query(Consultation).filter(Consultation.urgency_level == "high").count()
            moderate_urgency = db.query(Consultation).filter(Consultation.urgency_level == "moderate").count()
            routine_urgency = db.query(Consultation).filter(Consultation.urgency_level == "routine").count()
            
            return {
                "total_consultations": total_consultations,
                "completed_consultations": completed_consultations,
                "pending_consultations": pending_consultations,
                "urgency_breakdown": {
                    "high": high_urgency,
                    "moderate": moderate_urgency,
                    "routine": routine_urgency
                }
            }
        finally:
            db.close()

# Global database manager instance
db_manager = DatabaseManager()