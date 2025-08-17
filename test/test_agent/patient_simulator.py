"""
Patient Simulator LLM for testing sleep consultation agent.
This module creates realistic patient personas with various sleep disorders.
"""

import random
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

class PatientSimulator:
    """Simulates a patient with sleep problems for testing the consultation agent."""
    
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0.7)
        self.patient_profiles = self._create_patient_profiles()
        self.current_profile = None
        self.conversation_history = []
        
    def _create_patient_profiles(self) -> List[Dict[str, Any]]:
        """Create diverse patient profiles with different sleep disorders."""
        return [
            {
                "name": "Sarah Johnson",
                "age": 34,
                "occupation": "Software Engineer",
                "primary_complaint": "insomnia",
                "symptoms": [
                    "difficulty falling asleep (takes 45-60 minutes)",
                    "waking up multiple times during night",
                    "feeling tired during the day",
                    "anxiety about sleep"
                ],
                "lifestyle": {
                    "caffeine": "3-4 cups coffee daily, last one at 4 PM",
                    "exercise": "irregular, mostly weekends",
                    "screen_time": "works on computer until 10 PM",
                    "stress_level": "high due to work deadlines"
                },
                "medical_history": "no significant medical conditions",
                "sleep_schedule": "tries to sleep at 11 PM, wakes at 7 AM",
                "epworth_responses": [1, 2, 1, 2, 3, 1, 2, 1],  # Total: 13 (moderate)
                "personality": "anxious, detail-oriented, cooperative"
            },
            {
                "name": "Michael Chen",
                "age": 45,
                "occupation": "Truck Driver",
                "primary_complaint": "excessive daytime sleepiness",
                "symptoms": [
                    "falling asleep while driving",
                    "loud snoring reported by wife",
                    "morning headaches",
                    "feeling unrefreshed after sleep"
                ],
                "lifestyle": {
                    "caffeine": "energy drinks throughout the day",
                    "exercise": "minimal due to long driving hours",
                    "alcohol": "2-3 beers most evenings",
                    "weight": "overweight (BMI ~32)"
                },
                "medical_history": "high blood pressure, pre-diabetes",
                "sleep_schedule": "irregular due to work shifts",
                "epworth_responses": [3, 3, 2, 3, 3, 2, 3, 3],  # Total: 22 (severe - HIGH RISK)
                "personality": "straightforward, concerned about job safety"
            },
            {
                "name": "Emma Rodriguez",
                "age": 28,
                "occupation": "Nurse (Night Shifts)",
                "primary_complaint": "shift work sleep disorder",
                "symptoms": [
                    "difficulty sleeping during the day",
                    "extreme fatigue during night shifts",
                    "mood changes and irritability",
                    "digestive issues"
                ],
                "lifestyle": {
                    "caffeine": "multiple cups during night shifts",
                    "exercise": "yoga when possible",
                    "light_exposure": "struggles with bedroom darkness during day"
                },
                "medical_history": "no significant conditions",
                "sleep_schedule": "works 3 night shifts per week, 7 PM - 7 AM",
                "epworth_responses": [2, 1, 3, 2, 3, 1, 2, 2],  # Total: 16 (severe)
                "personality": "dedicated healthcare worker, tired but motivated"
            },
            {
                "name": "Robert Williams",
                "age": 52,
                "occupation": "Pilot",
                "primary_complaint": "sudden muscle weakness episodes",
                "symptoms": [
                    "sudden loss of muscle control when laughing",
                    "vivid dreams and sleep paralysis",
                    "excessive daytime sleepiness",
                    "automatic behaviors"
                ],
                "lifestyle": {
                    "caffeine": "controlled due to job requirements",
                    "exercise": "regular gym routine",
                    "stress": "job-related stress about safety"
                },
                "medical_history": "family history of narcolepsy",
                "sleep_schedule": "irregular due to flight schedules",
                "epworth_responses": [3, 3, 3, 3, 2, 2, 3, 3],  # Total: 22 (severe - HIGH RISK)
                "personality": "professional, concerned about career impact"
            },
            {
                "name": "Lisa Thompson",
                "age": 38,
                "occupation": "Teacher",
                "primary_complaint": "restless legs and poor sleep",
                "symptoms": [
                    "uncomfortable sensations in legs at bedtime",
                    "urge to move legs that disrupts sleep",
                    "symptoms worse in evening",
                    "partner reports leg movements during sleep"
                ],
                "lifestyle": {
                    "caffeine": "morning coffee only",
                    "exercise": "regular walking",
                    "iron_levels": "low-normal"
                },
                "medical_history": "iron deficiency in the past",
                "sleep_schedule": "regular 10:30 PM - 6:30 AM",
                "epworth_responses": [1, 1, 0, 1, 2, 0, 1, 1],  # Total: 7 (normal)
                "personality": "patient, descriptive, health-conscious"
            }
        ]
    
    def select_random_profile(self) -> Dict[str, Any]:
        """Select a random patient profile for the conversation."""
        self.current_profile = random.choice(self.patient_profiles)
        return self.current_profile
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the patient simulator."""
        if not self.current_profile:
            raise ValueError("No patient profile selected. Call select_random_profile() first.")
            
        profile = self.current_profile
        
        return f"""You are roleplaying as {profile['name']}, a {profile['age']}-year-old {profile['occupation']} with sleep problems.

PATIENT BACKGROUND:
- Primary complaint: {profile['primary_complaint']}
- Symptoms: {', '.join(profile['symptoms'])}
- Lifestyle factors: {profile['lifestyle']}
- Medical history: {profile['medical_history']}
- Sleep schedule: {profile['sleep_schedule']}
- Personality: {profile['personality']}

EPWORTH SLEEPINESS SCALE RESPONSES:
When asked about likelihood of dozing in situations (0=never, 1=slight, 2=moderate, 3=high chance):
1. Sitting and reading: {profile['epworth_responses'][0]}
2. Watching TV: {profile['epworth_responses'][1]}
3. Sitting inactive in public: {profile['epworth_responses'][2]}
4. As passenger in car for 1 hour: {profile['epworth_responses'][3]}
5. Lying down to rest in afternoon: {profile['epworth_responses'][4]}
6. Sitting and talking to someone: {profile['epworth_responses'][5]}
7. Sitting quietly after lunch: {profile['epworth_responses'][6]}
8. In car stopped in traffic: {profile['epworth_responses'][7]}

ROLEPLAY INSTRUCTIONS:
- Answer questions as this specific patient would
- Be consistent with the background information
- Show appropriate concern for your symptoms
- Respond naturally and conversationally
- Don't volunteer all information at once - answer what's asked
- Show realistic patient behavior (some uncertainty, asking questions back occasionally)
- If asked about specific numbers/scales, use the provided responses
- Stay in character throughout the entire conversation
- Express emotions and concerns that match your profile

IMPORTANT: Only provide information when specifically asked. Don't give long speeches or volunteer everything at once. Respond like a real patient would - sometimes brief, sometimes more detailed depending on the question."""

    def respond_to_doctor(self, doctor_message: str) -> str:
        """Generate a patient response to the doctor's message."""
        if not self.current_profile:
            raise ValueError("No patient profile selected.")
            
        # Create the conversation prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", f"Doctor says: {doctor_message}\n\nRespond as the patient:")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({"doctor_message": doctor_message})
        
        # Store in conversation history
        self.conversation_history.append({
            "doctor": doctor_message,
            "patient": response.content
        })
        
        return response.content
    
    def get_patient_info(self) -> Dict[str, Any]:
        """Get current patient profile information."""
        return self.current_profile
    
    def reset_conversation(self):
        """Reset conversation history for a new conversation."""
        self.conversation_history = []
        self.current_profile = None