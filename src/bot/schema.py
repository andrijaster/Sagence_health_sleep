"""
Schema definitions for the sleep consultation bot state management.
"""

from typing import List, TypedDict, Annotated
from langchain_core.messages import AnyMessage
import operator


class GraphState(TypedDict):
    """
    Stanje LangGraph agenta.

    Attributes:
        messages: Lista poruka u konverzaciji.
        referral_letter: Tekst uputnog pisma dat na početku.
        patient_name: Ime pacijenta izvučeno iz uputnog pisma.
        off_topic_counter: Brojač uzastopnih odgovora koji nisu na temu.
        last_question: Poslednje pitanje koje je AI postavio, za ponovno postavljanje.
        questions_answered: Brojač odgovorenih pitanja tokom konsultacije.
        summary_confirmed: Zastavica koja prati da li je pacijent već dobio priliku da doda informacije u sažetak.
        terminate_reason: Razlog prekida konverzacije (npr. 'self_harm', 'off_topic_limit', 'completed').
        doctor_summary: Profesionalni sažetak za lekara sa kliničkom terminologijom.
        patient_summary: Sažetak za pacijenta u pristupačnom jeziku.
        urgency_level: Nivo hitnosti - 'high' za suicide/guardrail/urgent medical, 'routine' inače.
    """
    messages: Annotated[List[AnyMessage], operator.add]
    referral_letter: str | None
    patient_name: str | None
    off_topic_counter: int
    last_question: str
    questions_answered: int
    summary_confirmed: bool
    terminate_reason: str | None
    doctor_summary: str | None
    patient_summary: str | None
    urgency_level: str | None