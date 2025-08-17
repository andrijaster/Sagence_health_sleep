"""
FastAPI server for Sleep Consultation AI
Database-driven system with auth tokens and complete data persistence.
"""

import asyncio
import tempfile
import os
import time
import shutil
import psutil
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

# Import our modules
from src.bot.graph import app as graph_app, llm
from src.bot.helper import get_personalized_greeting_prompt, get_greeting_message
from src.referal_letter.extraction import AsyncReferralLetterExtractor
from app.database import db_manager
from app.schemas import (
    ChatRequest, ChatResponse, ReferralLetterResponse,
    ConsultationSearchResponse, ConsultationDetailsResponse,
    StatisticsResponse, HealthCheckResponse, ErrorResponse
)

# Initialize FastAPI app
app = FastAPI(title="Sleep Consultation AI API", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize referral letter extractor
extractor = AsyncReferralLetterExtractor()

# Create directory for storing PDF files
PDF_STORAGE_DIR = "stored_pdfs"
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

# In-memory session storage for active conversations
sessions: Dict[str, Dict[str, Any]] = {}

# Application startup time for uptime calculation
app_start_time = time.time()

# In-memory session storage for active conversations
sessions: Dict[str, Dict[str, Any]] = {}

def generate_session_id(patient_name: str, auth_token: str) -> str:
    """Generate unique session ID for consultation."""
    timestamp = int(time.time())
    base_id = patient_name.replace(" ", "_").lower() if patient_name else "patient"
    return f"{base_id}_{timestamp}_{auth_token[:8]}"

@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Comprehensive health check endpoint with system status.
    """
    try:
        # Test database connection
        try:
            stats = db_manager.get_statistics()
            database_status = "healthy"
            total_consultations = stats.get("total_consultations", 0)
        except Exception as e:
            database_status = f"error: {str(e)}"
            total_consultations = 0
        
        # Calculate uptime
        uptime_seconds = time.time() - app_start_time
        
        return HealthCheckResponse(
            status="healthy",
            service="Sleep Consultation AI API",
            version="2.0.0",
            database_status=database_status,
            active_sessions=len(sessions),
            total_consultations=total_consultations,
            uptime_seconds=uptime_seconds
        )
    except Exception as e:
        return HealthCheckResponse(
            status="unhealthy",
            service="Sleep Consultation AI API",
            version="2.0.0",
            database_status="unknown",
            active_sessions=0,
            total_consultations=0,
            uptime_seconds=time.time() - app_start_time
        )

@app.post("/api/referral-letter", response_model=ReferralLetterResponse)
async def upload_referral_letter(file: UploadFile = File(...)):
    """
    Upload referral letter PDF, extract information, save to database, and return auth token.
    """
    # Validate file type first (before try block)
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Validate file size (not empty)
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File cannot be empty")
    
    try:
        # Save uploaded file temporarily for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Extract information from PDF
            result = await extractor.process_pdf(tmp_path)
            
            if result and result.get("patient_name") != "ERROR":
                # Generate permanent file path
                timestamp = int(time.time())
                permanent_filename = f"{timestamp}_{file.filename}"
                permanent_path = os.path.join(PDF_STORAGE_DIR, permanent_filename)
                
                # Move file to permanent storage
                shutil.move(tmp_path, permanent_path)
                
                # Save to database and get auth token
                auth_token = db_manager.save_referral_letter(permanent_path, result)
                
                return ReferralLetterResponse(
                    auth_token=auth_token,
                    patient_name=result.get("patient_name"),
                    doctor_name=result.get("doctor_name"),
                    referral_date=result.get("referral_date"),
                    referred_to=result.get("referred_to"),
                    referral_reason=result.get("referral_reason"),
                    success=True
                )
            else:
                return ReferralLetterResponse(
                    success=False,
                    error="Failed to extract information from PDF"
                )
                
        except Exception as e:
            # Clean up temporary file if it still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise e
            
    except Exception as e:
        return ReferralLetterResponse(
            success=False,
            error=f"PDF processing error: {str(e)}"
        )

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_token(request: ChatRequest):
    """
    Chat endpoint using auth token. Token becomes invalid after consultation completion.
    """
    try:
        # Validate auth token
        if not db_manager.is_token_valid(request.auth_token):
            raise HTTPException(status_code=401, detail="Invalid or expired auth token")
        
        # Get referral letter data
        referral = db_manager.get_referral_by_token(request.auth_token)
        if not referral:
            raise HTTPException(status_code=404, detail="Referral letter not found")
        
        # Check if consultation already exists
        consultation = db_manager.get_consultation_by_token(request.auth_token)
        
        if not consultation:
            # Create new consultation
            session_id = generate_session_id(referral.patient_name, request.auth_token)
            consultation_id = db_manager.create_consultation(request.auth_token, session_id, referral.patient_name)
            
            # Prepare referral letter text - ONLY patient name
            referral_text = f"Patient Name: {referral.patient_name}" if referral.patient_name else ""
            
            # Initialize conversation state
            initial_state = {
                "messages": [],
                "referral_letter": referral_text,
                "patient_name": referral.patient_name,
                "off_topic_counter": 0,
                "last_question": "",
                "questions_answered": 0,
                "summary_confirmed": False,
                "terminate_reason": None,
                "doctor_summary": None,
                "patient_summary": None,
                "urgency_level": None
            }
            
            # Generate greeting message using patient name directly
            if referral.patient_name:
                greeting_message = f"Hello {referral.patient_name}! I'm Dr. SleepAI, your AI sleep medicine specialist. I'm here to help you with your sleep concerns. Could you please tell me in your own words what's been troubling you with your sleep?"
            else:
                greeting_message = get_greeting_message()
            
            # Add greeting to initial state
            initial_state["messages"] = [AIMessage(content=greeting_message)]
            
            # Configure graph with unique thread ID
            config = {
                "recursion_limit": 150,
                "configurable": {"thread_id": session_id}
            }
            
            # Store session with initial state (don't invoke graph yet)
            sessions[request.auth_token] = {
                "state": initial_state,
                "config": config,
                "consultation_id": consultation_id
            }
            
            # Save greeting message to database
            db_manager.save_message(consultation_id, request.auth_token, "ai", greeting_message)
            
            # Update consultation in database
            conversation_history = [{"type": "ai", "content": greeting_message}]
            db_manager.update_consultation(request.auth_token, conversation_history, 0)
            
            return ChatResponse(
                bot_response=greeting_message,
                conversation_complete=False,
                questions_answered=0,
                success=True
            )
        
        else:
            # Continue existing consultation
            if consultation.is_completed:
                return ChatResponse(
                    bot_response="This consultation has been completed. Your auth token is no longer valid.",
                    conversation_complete=True,
                    questions_answered=consultation.questions_answered,
                    success=True
                )
            
            # Get or restore session
            if request.auth_token not in sessions:
                # Restore session from database
                session_id = consultation.session_id
                config = {
                    "recursion_limit": 150,
                    "configurable": {"thread_id": session_id}
                }
                
                # Reconstruct state from conversation history
                messages = []
                for msg_data in consultation.conversation_history:
                    if msg_data["type"] == "ai":
                        messages.append(AIMessage(content=msg_data["content"]))
                    else:
                        messages.append(HumanMessage(content=msg_data["content"]))
                
                current_state = {
                    "messages": messages,
                    "referral_letter": f"Patient Name: {referral.patient_name}" if referral.patient_name else "",
                    "patient_name": referral.patient_name,
                    "off_topic_counter": 0,
                    "last_question": "",
                    "questions_answered": consultation.questions_answered,
                    "summary_confirmed": False,
                    "terminate_reason": None,
                    "doctor_summary": consultation.doctor_summary,
                    "patient_summary": consultation.patient_summary,
                    "urgency_level": consultation.urgency_level
                }
                
                sessions[request.auth_token] = {
                    "state": current_state,
                    "config": config,
                    "consultation_id": consultation.id
                }
            
            session = sessions[request.auth_token]
            
            # Add user message to state
            current_state = session["state"]
            current_state["messages"].append(HumanMessage(content=request.message))
            
            # Save user message to database
            db_manager.save_message(session["consultation_id"], request.auth_token, "human", request.message)
            
            # Get bot response
            result = graph_app.invoke(current_state, session["config"])
            
            # Update session state
            session["state"] = result
            
            # Get bot's response
            if result.get("messages"):
                bot_response = result["messages"][-1].content
            else:
                bot_response = "I'm sorry, I encountered an issue. Could you please repeat your message?"
            
            # Save bot response to database
            db_manager.save_message(session["consultation_id"], request.auth_token, "ai", bot_response)
            
            # Check if conversation is complete
            conversation_complete = (
                result.get("terminate_reason") == "completed" or
                (result.get("summary_confirmed", False) and result.get("doctor_summary"))
            )
            
            # Update conversation history for database
            conversation_history = []
            for msg in result.get("messages", []):
                if hasattr(msg, 'type'):
                    msg_type = "ai" if msg.type == "ai" else "human"
                else:
                    msg_type = "ai" if isinstance(msg, AIMessage) else "human"
                conversation_history.append({"type": msg_type, "content": msg.content})
            
            # Update consultation in database
            db_manager.update_consultation(
                request.auth_token,
                conversation_history,
                result.get("questions_answered", 0),
                result.get("doctor_summary"),
                result.get("patient_summary"),
                result.get("urgency_level"),
                conversation_complete
            )
            
            # Mark token as used if conversation is complete
            if conversation_complete:
                db_manager.mark_token_used(request.auth_token)
                # Remove from active sessions
                if request.auth_token in sessions:
                    del sessions[request.auth_token]
            
            return ChatResponse(
                bot_response=bot_response,
                conversation_complete=conversation_complete,
                doctor_summary=result.get("doctor_summary") if conversation_complete else None,
                patient_summary=result.get("patient_summary") if conversation_complete else None,
                urgency_level=result.get("urgency_level") if conversation_complete else None,
                questions_answered=result.get("questions_answered", 0),
                success=True
            )
            
    except HTTPException:
        raise
    except Exception as e:
        return ChatResponse(
            bot_response="",
            conversation_complete=False,
            questions_answered=0,
            success=False,
            error=f"Chat error: {str(e)}"
        )

@app.get("/api/consultations/search", response_model=ConsultationSearchResponse)
async def search_consultations(
    patient_name: Optional[str] = Query(None, description="Search by patient name"),
    patient_id: Optional[int] = Query(None, description="Search by patient ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    sort_by: str = Query("started_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    Search and filter consultations with sorting options.
    """
    try:
        consultations = db_manager.search_consultations(
            patient_name=patient_name,
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return ConsultationSearchResponse(
            consultations=consultations,
            total_count=len(consultations),
            success=True
        )
    except Exception as e:
        return ConsultationSearchResponse(
            consultations=[],
            total_count=0,
            success=False
        )

@app.get("/api/consultations/{consultation_id}", response_model=ConsultationDetailsResponse)
async def get_consultation_details(consultation_id: int):
    """
    Get complete consultation details including referral letter and all messages.
    """
    try:
        details = db_manager.get_consultation_details(consultation_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        return ConsultationDetailsResponse(
            consultation=details,
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        return ConsultationDetailsResponse(
            consultation=None,
            success=False,
            error=f"Error retrieving consultation: {str(e)}"
        )

@app.get("/api/statistics")
async def get_statistics():
    """
    Get database statistics.
    """
    try:
        stats = db_manager.get_statistics()
        return {"success": True, "data": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)