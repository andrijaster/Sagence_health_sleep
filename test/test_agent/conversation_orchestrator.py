"""
Conversation Orchestrator for testing sleep consultation agent.
Manages conversations between patient simulator and the sleep consultation graph.
"""

import os
import sys
import json
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the src directory to the path to import the graph
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from langchain_core.messages import HumanMessage, AIMessage
from patient_simulator import PatientSimulator
from bot.graph import app as sleep_agent  # Import the compiled graph

class ConversationOrchestrator:
    """Orchestrates conversations between patient simulator and sleep consultation agent."""
    
    def __init__(self, api_key: str, results_db_path: str = "test/test_agent/conversation_results.db"):
        self.api_key = api_key
        self.patient_simulator = PatientSimulator(api_key)
        self.results_db_path = results_db_path
        self.setup_database()
        
    def setup_database(self):
        """Setup SQLite database to store conversation results."""
        os.makedirs(os.path.dirname(self.results_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.results_db_path)
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT UNIQUE,
                patient_name TEXT,
                patient_profile TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_messages INTEGER,
                conversation_data TEXT,
                doctor_summary TEXT,
                patient_summary TEXT,
                urgency_level TEXT,
                epworth_score INTEGER,
                high_risk_flags TEXT,
                completion_status TEXT,
                notes TEXT
            )
        ''')
        
        # Create messages table for detailed conversation tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                message_order INTEGER,
                sender TEXT,
                message_content TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def run_single_conversation(self, max_turns: int = 50) -> Dict[str, Any]:
        """Run a single conversation between patient simulator and sleep agent."""
        
        # Select random patient profile
        patient_profile = self.patient_simulator.select_random_profile()
        conversation_id = f"conv_{int(time.time())}_{patient_profile['name'].replace(' ', '_')}"
        
        print(f"\n🏥 Starting conversation with {patient_profile['name']} ({patient_profile['primary_complaint']})")
        print(f"📋 Conversation ID: {conversation_id}")
        
        # Initialize conversation tracking
        start_time = datetime.now()
        messages = []
        turn_count = 0
        
        # Create agent configuration with unique thread ID
        config = {"configurable": {"thread_id": conversation_id}}
        
        # Generate referral letter for the patient
        referral_letter = self._generate_referral_letter(patient_profile)
        
        # Initialize the sleep agent with referral letter
        initial_inputs = {
            "messages": [AIMessage(content=f"Hello {patient_profile['name']}! I'm Dr. SleepAI, your AI sleep medicine specialist. I'm here to help you with your sleep concerns. Could you please tell me in your own words what's been troubling you with your sleep?")],
            "referral_letter": referral_letter
        }
        
        # Run initial setup
        for event in sleep_agent.stream(initial_inputs, config, stream_mode="values"):
            pass
            
        # Start conversation loop
        try:
            while turn_count < max_turns:
                # Get current state
                current_state = sleep_agent.get_state(config)
                
                if current_state.values.get("terminate_reason"):
                    print(f"✅ Conversation completed: {current_state.values.get('terminate_reason')}")
                    break
                    
                # Get last AI message
                last_ai_message = None
                for msg in reversed(current_state.values.get("messages", [])):
                    if isinstance(msg, AIMessage):
                        last_ai_message = msg.content
                        break
                        
                if not last_ai_message:
                    break
                    
                print(f"\n🤖 Doctor: {last_ai_message}")
                
                # Log doctor message
                messages.append({
                    "sender": "doctor",
                    "content": last_ai_message,
                    "timestamp": datetime.now(),
                    "turn": turn_count
                })
                
                # Generate patient response
                patient_response = self.patient_simulator.respond_to_doctor(last_ai_message)
                print(f"👤 Patient: {patient_response}")
                
                # Log patient message
                messages.append({
                    "sender": "patient", 
                    "content": patient_response,
                    "timestamp": datetime.now(),
                    "turn": turn_count
                })
                
                # Send patient response to agent
                patient_input = {"messages": [HumanMessage(content=patient_response)]}
                
                for event in sleep_agent.stream(patient_input, config, stream_mode="values"):
                    pass
                    
                turn_count += 1
                time.sleep(1)  # Small delay to prevent overwhelming
                
        except Exception as e:
            print(f"❌ Error during conversation: {e}")
            return {"error": str(e), "conversation_id": conversation_id}
            
        # Get final state and summaries
        final_state = sleep_agent.get_state(config)
        end_time = datetime.now()
        
        # Extract results
        conversation_result = {
            "conversation_id": conversation_id,
            "patient_profile": patient_profile,
            "start_time": start_time,
            "end_time": end_time,
            "duration_minutes": (end_time - start_time).total_seconds() / 60,
            "total_turns": turn_count,
            "messages": messages,
            "doctor_summary": final_state.values.get("doctor_summary", ""),
            "patient_summary": final_state.values.get("patient_summary", ""),
            "urgency_level": final_state.values.get("urgency_level", "routine"),
            "completion_status": final_state.values.get("terminate_reason", "incomplete"),
            "final_state": final_state.values
        }
        
        # Calculate Epworth score from patient responses
        epworth_score = sum(patient_profile.get("epworth_responses", []))
        conversation_result["epworth_score"] = epworth_score
        
        # Identify high-risk flags
        high_risk_flags = []
        if epworth_score > 20:
            high_risk_flags.append("Epworth score >20")
        if patient_profile.get("occupation") in ["Truck Driver", "Pilot"]:
            high_risk_flags.append("Safety-sensitive occupation")
        if "falling asleep while driving" in str(patient_profile.get("symptoms", [])):
            high_risk_flags.append("Driving safety concern")
            
        conversation_result["high_risk_flags"] = high_risk_flags
        
        # Save to database
        self._save_conversation_to_db(conversation_result)
        
        print(f"\n📊 Conversation Summary:")
        print(f"   Duration: {conversation_result['duration_minutes']:.1f} minutes")
        print(f"   Total turns: {turn_count}")
        print(f"   Epworth score: {epworth_score}")
        print(f"   Urgency level: {conversation_result['urgency_level']}")
        print(f"   High-risk flags: {', '.join(high_risk_flags) if high_risk_flags else 'None'}")
        
        return conversation_result
        
    def _generate_referral_letter(self, patient_profile: Dict[str, Any]) -> str:
        """Generate a realistic referral letter for the patient."""
        return f"""SLEEP CLINIC REFERRAL LETTER

Patient: {patient_profile['name']}
Age: {patient_profile['age']}
Occupation: {patient_profile['occupation']}

Dear Sleep Medicine Team,

I am referring {patient_profile['name']} for evaluation of sleep-related concerns. 

Chief Complaint: {patient_profile['primary_complaint']}

The patient reports: {', '.join(patient_profile['symptoms'][:2])}

Medical History: {patient_profile['medical_history']}

Please evaluate and provide recommendations for management.

Thank you for your assistance.

Dr. Primary Care
General Practice"""

    def _save_conversation_to_db(self, conversation_result: Dict[str, Any]):
        """Save conversation results to database."""
        conn = sqlite3.connect(self.results_db_path)
        cursor = conn.cursor()
        
        # Insert conversation record
        cursor.execute('''
            INSERT OR REPLACE INTO conversations 
            (conversation_id, patient_name, patient_profile, start_time, end_time, 
             total_messages, conversation_data, doctor_summary, patient_summary, 
             urgency_level, epworth_score, high_risk_flags, completion_status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            conversation_result["conversation_id"],
            conversation_result["patient_profile"]["name"],
            json.dumps(conversation_result["patient_profile"]),
            conversation_result["start_time"],
            conversation_result["end_time"],
            len(conversation_result["messages"]),
            json.dumps(conversation_result["messages"]),
            conversation_result["doctor_summary"],
            conversation_result["patient_summary"],
            conversation_result["urgency_level"],
            conversation_result["epworth_score"],
            json.dumps(conversation_result["high_risk_flags"]),
            conversation_result["completion_status"],
            f"Duration: {conversation_result['duration_minutes']:.1f} min, Turns: {conversation_result['total_turns']}"
        ))
        
        # Insert individual messages
        for i, message in enumerate(conversation_result["messages"]):
            cursor.execute('''
                INSERT INTO messages 
                (conversation_id, message_order, sender, message_content, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                conversation_result["conversation_id"],
                i,
                message["sender"],
                message["content"],
                message["timestamp"]
            ))
        
        conn.commit()
        conn.close()
        
    def run_multiple_conversations(self, num_conversations: int, max_turns_per_conversation: int = 50) -> List[Dict[str, Any]]:
        """Run multiple conversations for testing."""
        print(f"\n🚀 Starting {num_conversations} test conversations...")
        print(f"📝 Results will be saved to: {self.results_db_path}")
        
        results = []
        
        for i in range(num_conversations):
            print(f"\n{'='*60}")
            print(f"🔄 Conversation {i+1}/{num_conversations}")
            print(f"{'='*60}")
            
            # Reset patient simulator for new conversation
            self.patient_simulator.reset_conversation()
            
            try:
                result = self.run_single_conversation(max_turns_per_conversation)
                results.append(result)
                
                # Brief pause between conversations
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Failed conversation {i+1}: {e}")
                results.append({"error": str(e), "conversation_number": i+1})
                
        print(f"\n🎉 Completed {num_conversations} conversations!")
        self._print_summary_statistics(results)
        
        return results
        
    def _print_summary_statistics(self, results: List[Dict[str, Any]]):
        """Print summary statistics of all conversations."""
        successful_conversations = [r for r in results if "error" not in r]
        
        if not successful_conversations:
            print("❌ No successful conversations to analyze.")
            return
            
        print(f"\n📈 SUMMARY STATISTICS:")
        print(f"   Total conversations: {len(results)}")
        print(f"   Successful: {len(successful_conversations)}")
        print(f"   Failed: {len(results) - len(successful_conversations)}")
        
        # Calculate averages
        avg_duration = sum(r.get("duration_minutes", 0) for r in successful_conversations) / len(successful_conversations)
        avg_turns = sum(r.get("total_turns", 0) for r in successful_conversations) / len(successful_conversations)
        
        print(f"   Average duration: {avg_duration:.1f} minutes")
        print(f"   Average turns: {avg_turns:.1f}")
        
        # Urgency levels
        urgency_counts = {}
        for r in successful_conversations:
            urgency = r.get("urgency_level", "unknown")
            urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
            
        print(f"   Urgency levels: {urgency_counts}")
        
        # High-risk patients
        high_risk_count = sum(1 for r in successful_conversations if r.get("high_risk_flags"))
        print(f"   High-risk patients: {high_risk_count}/{len(successful_conversations)}")
        
        # Completion status
        completion_counts = {}
        for r in successful_conversations:
            status = r.get("completion_status", "unknown")
            completion_counts[status] = completion_counts.get(status, 0) + 1
            
        print(f"   Completion status: {completion_counts}")

    def get_conversation_analysis(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed analysis of a specific conversation."""
        conn = sqlite3.connect(self.results_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM conversations WHERE conversation_id = ?
        ''', (conversation_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        # Convert to dictionary (assuming column order matches)
        columns = ['id', 'conversation_id', 'patient_name', 'patient_profile', 'start_time', 
                  'end_time', 'total_messages', 'conversation_data', 'doctor_summary', 
                  'patient_summary', 'urgency_level', 'epworth_score', 'high_risk_flags', 
                  'completion_status', 'notes']
        
        conversation_data = dict(zip(columns, result))
        
        # Parse JSON fields
        conversation_data['patient_profile'] = json.loads(conversation_data['patient_profile'])
        conversation_data['conversation_data'] = json.loads(conversation_data['conversation_data'])
        conversation_data['high_risk_flags'] = json.loads(conversation_data['high_risk_flags'])
        
        return conversation_data