"""
Pydantic models for structured output in the sleep consultation bot.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class RouterDecision(BaseModel):
    """Strukturirani izlaz za ruter."""
    decision: Literal["ask_question", "generate_summary"] = Field(
        description="Decision to either ask another question or generate a summary."
    )


class GuardrailDecision(BaseModel):
    """Strukturirani izlaz za guardrail klasifikaciju."""
    is_on_topic: bool = Field(
        description="True if the message is related to sleep, False if it's off-topic"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence level in the classification"
    )


class SuicideCheckDecision(BaseModel):
    """Strukturirani izlaz za proveru rizika od samopovređivanja."""
    risk_detected: bool = Field(
        description="True if self-harm risk is detected, False if no risk"
    )
    risk_level: Literal["none", "low", "medium", "high", "immediate"] = Field(
        description="Level of detected risk"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence level in the assessment"
    )


class SleepSummary(BaseModel):
    """Strukturirani izlaz za sažetak spavanja."""
    doctor_summary: str = Field(
        description="Professional medical summary for healthcare providers with clinical terminology and diagnostic insights. PROVIDE IT LONG AND IN DETAILS."
    )
    patient_summary: str = Field(
        description="Patient-friendly summary explaining their sleep issues in accessible language"
    )
    urgency_level: Literal["routine", "moderate", "high"] = Field(
        description="Clinical urgency level - 'high' for urgent/critical conditions including safety risks, 'moderate' for moderate concern, 'routine' for standard follow-up"
    )