"""
Sleep Consultation Agent Testing Framework

This package provides automated testing capabilities for the sleep consultation agent,
including patient simulation, conversation orchestration, and evaluation tools.
"""

__version__ = "1.0.0"
__author__ = "Sleep Consultation Team"

from .patient_simulator import PatientSimulator
from .conversation_orchestrator import ConversationOrchestrator
from .evaluate_conversations import ConversationEvaluator

__all__ = [
    "PatientSimulator",
    "ConversationOrchestrator", 
    "ConversationEvaluator"
]