import os
import sqlite3
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

# Import our custom modules
from .schema import GraphState
from .models import GuardrailDecision, SuicideCheckDecision, SleepSummary, RouterDecision
from .helper import (
    get_guardrail_prompt, get_suicide_check_prompt, get_ask_question_system_prompt,
    get_initial_question_prompt, get_followup_question_prompt, get_summary_system_prompt,
    get_initial_summary_prompt, get_final_summary_prompt, get_final_summary_input_prompt,
    get_router_system_prompt, get_router_input_prompt, get_greeting_message,
    get_personalized_greeting_prompt
)

# --- Podešavanje API ključa ---
# Postavite vaš OpenAI API ključ kao promenljivu okruženja (environment variable)
# Na primer: os.environ["OPENAI_API_KEY"] = "sk-..."
# Ako nemate ključ, možete ga dobiti na platform.openai.com

os.environ["OPENAI_API_KEY"] = "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"

# --- Inicijalizacija LLM-a ---
# Koristimo gpt-4o jer je dobar u praćenju složenih instrukcija i strukturiranom izlazu.
llm = ChatOpenAI(model="gpt-4o")
# LLM sa povećanim max_tokens za detaljne sažetke za lekare
llm_summary = ChatOpenAI(model="gpt-4o", max_tokens=3000)

# --- Definicija čvorova (Nodes) grafa ---

def guardrail_node(state: GraphState) -> GraphState:
    """
    Čvor Guardrail: Proverava da li je odgovor korisnika na temu (o spavanju).
    Ako nije, upozorava korisnika. Ako se to ponovi 3 puta, prekida konverzaciju.
    """
    print("---NODE: Guardrail---")
    if not state["messages"] or not isinstance(state["messages"][-1], HumanMessage):
        # Preskačemo ako nema ljudske poruke (npr. prvi poziv grafa)
        # Return at least one field to satisfy LangGraph requirements
        return {"off_topic_counter": state.get("off_topic_counter", 0)}

    user_message = state["messages"][-1].content
    
    # Get conversation context for better classification
    conversation_history = "\n".join([f"{msg.type}: {msg.content}" for msg in state["messages"][-5:]])
    last_question = state.get("last_question", "")
    
    # Use structured output for more reliable classification
    structured_llm = llm.with_structured_output(GuardrailDecision)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_guardrail_prompt()),
        ("human", """Recent conversation context: 
            {conversation_history}

            Last question asked by doctor: {last_question}

            User's current message: {user_message}

            Classify this message as sleep-related (on-topic) or not (off-topic), considering the conversation context.""")
    ])
    
    chain = prompt | structured_llm
    
    try:
        response = chain.invoke({
            "user_message": user_message,
            "conversation_history": conversation_history,
            "last_question": last_question
        })
        print(f"Guardrail Classification: {'ON-TOPIC' if response.is_on_topic else 'OFF-TOPIC'} (confidence: {response.confidence})")
        
        if not response.is_on_topic:
            print("Guardrail: User is OFF-TOPIC.")
            counter = state.get("off_topic_counter", 0) + 1
            if counter >= 3:
                print("Guardrail: Off-topic limit reached. Terminating.")
                ai_message = AIMessage(content="I can only discuss topics related to sleep. Since we are not making progress, I have to end this conversation. Goodbye.")
                return {"messages": [ai_message], "off_topic_counter": counter, "terminate_reason": "off_topic_limit", "urgency_level": "high"}
            else:
                # Use the actual last question if available, otherwise use a generic prompt
                last_q = state.get('last_question', 'Please tell me about your sleep concerns.')
                warning_message = f"I can only help with sleep-related issues. Let's get back on track. {last_q}"
                ai_message = AIMessage(content=warning_message)
                return {"messages": [ai_message], "off_topic_counter": counter}
        else:
            print("Guardrail: User is ON-TOPIC.")
            # Increment questions_answered counter when user provides valid answer
            current_count = state.get("questions_answered", 0)
            return {"off_topic_counter": 0, "questions_answered": current_count + 1}
            
    except Exception as e:
        print(f"Guardrail Error: {e}. Defaulting to ON-TOPIC to avoid blocking valid conversations.")
        return {"off_topic_counter": 0}

def suicide_check_node(state: GraphState) -> GraphState:
    """
    Čvor Suicide Check: Proverava da li u poslednjih 5 poruka ima naznaka o samopovređivanju.
    Ako ima, odmah prekida konverzaciju uz bezbednosnu poruku.
    """
    print("---NODE: Suicide Check---")
    last_5_messages_content = "\n".join([msg.content for msg in state["messages"][-5:]])

    # Use structured output for more reliable safety assessment
    structured_llm = llm.with_structured_output(SuicideCheckDecision)

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_suicide_check_prompt()),
        ("human", "Conversation context from last 5 messages:\n\n{conversation_context}\n\nAssess this conversation for any self-harm or suicide risk indicators.")
    ])
    
    chain = prompt | structured_llm
    
    try:
        response = chain.invoke({"conversation_context": last_5_messages_content})
        print(f"Suicide Check: Risk Level = {response.risk_level.upper()}, Confidence = {response.confidence}")
        
        # Trigger safety response for medium, high, or immediate risk
        if response.risk_detected and response.risk_level in ["medium", "high", "immediate"]:
            print("Suicide Check: SELF-HARM RISK DETECTED. Terminating immediately.")
            
            # Customize message based on risk level
            if response.risk_level == "immediate":
                safety_message = "I've detected that you may be in immediate danger. Your safety is my top priority. Please contact emergency services (911/112) or a crisis hotline immediately. I must end this conversation now to encourage you to seek immediate help."
            else:
                safety_message = "I've detected that you might be in distress. My purpose is to discuss sleep, but your safety is most important. Please consider reaching out to a crisis hotline or a mental health professional immediately. I must end this conversation now."
            
            ai_message = AIMessage(content=safety_message)
            return {"messages": [ai_message], "terminate_reason": "self_harm_risk", "urgency_level": "high"}
        
        print("Suicide Check: No significant self-harm risk detected.")
        return {"off_topic_counter": state.get("off_topic_counter", 0)}
        
    except Exception as e:
        print(f"Suicide Check Error: {e}. Defaulting to safe mode - continuing conversation but logging error.")
        # In case of error, continue conversation but log the issue
        return {"off_topic_counter": state.get("off_topic_counter", 0)}

def ask_question_node(state: GraphState) -> GraphState:
    """
    Čvor Ask Question: Postavlja sledeće relevantno pitanje, uzimajući u obzir uputno pismo kao početni kontekst.
    """
    print("---NODE: Ask Question---")
    
    system_prompt = get_ask_question_system_prompt()
    
    # Prilagođavamo prompt u zavisnosti da li je ovo prvo pitanje ili nastavak razgovora.
    print(f"🔍 DEBUG: Messages count: {len(state['messages'])}")
    print(f"🔍 DEBUG: State keys: {list(state.keys())}")
    print(f"🔍 DEBUG: Patient name available: {state.get('patient_name')}")
    print(f"🔍 DEBUG: Referral letter available: {bool(state.get('referral_letter'))}")
    
    if len(state['messages']) <= 1:
        # Prvo pitanje je sada pametnije i može se osloniti na uputno pismo.
        question_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", get_initial_question_prompt()),
        ])
    else:
        question_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", get_followup_question_prompt())
        ])

    chain = question_prompt | llm
    
    conversation_history = "\n".join([f"{msg.type}: {msg.content}" for msg in state["messages"]])
    referral_letter_text = state.get("referral_letter") or "No referral letter provided."
    patient_name = state.get("patient_name")
    
    # Create a modified referral letter text that includes the patient name for context
    if patient_name:
        referral_context = f"Patient Name: {patient_name}"
    else:
        referral_context = "No patient name available."
    
    print(f"🔍 DEBUG: Patient name being used: {patient_name}")
    print(f"🔍 DEBUG: Referral context being sent to LLM: {referral_context}")
    
    response = chain.invoke({
        "conversation_history": conversation_history,
        "referral_letter": referral_letter_text,
        "patient_name": patient_name
    })
    question = response.content

    print(f"🔍 DEBUG: Generated question: {question}")

    ai_message = AIMessage(content=question)
    
    return {"messages": [ai_message], "last_question": question}

def summary_node(state: GraphState) -> GraphState:
    """
    Čvor Summary: Generiše profesionalni sažetak za lekara i pacijenta koristeći strukturirani izlaz.
    Kreira dva različita sažetka na osnovu konverzacije.
    """
    print("---NODE: Summary---")
    print(f"🔍 DEBUG: Patient name in summary: {state.get('patient_name')}")
    
    # Use structured output for professional summary generation with higher token limit
    structured_llm = llm_summary.with_structured_output(SleepSummary)
    
    if not state.get("summary_confirmed", False):
        prompt = ChatPromptTemplate.from_messages([
            ("system", get_summary_system_prompt()),
            ("human", get_initial_summary_prompt())
        ])
        
        chain = prompt | structured_llm
        conversation_history = "\n".join([f"{msg.type}: {msg.content}" for msg in state["messages"]])
        referral_letter_text = state.get("referral_letter") or "No referral letter provided."
        patient_name = state.get("patient_name")
        
        try:
            summary = chain.invoke({
                "conversation_history": conversation_history,
                "referral_letter": referral_letter_text,
                "patient_name": patient_name
            })
            
            # Format the patient-facing message
            patient_message = f"""Based on our comprehensive consultation, here is your personalized sleep assessment:

                **YOUR SLEEP SITUATION:**
                {summary.patient_summary}

                Is there anything important you would like to add or correct about this summary? You can add information only once.

                ---
                *Note: A detailed medical summary has also been generated for your healthcare provider.*"""

            ai_message = AIMessage(content=patient_message)
            
            # Store the structured summary in state for potential use
            return {
                "messages": [ai_message], 
                "summary_confirmed": True,
                "doctor_summary": summary.doctor_summary,
                "patient_summary": summary.patient_summary,
                "urgency_level": summary.urgency_level
            }
            
        except Exception as e:
            print(f"Summary Error: {e}. Falling back to simple summary.")
            # Fallback to simple summary if structured output fails
            simple_prompt = ChatPromptTemplate.from_messages([
                ("system", "Create a comprehensive sleep consultation summary based on the conversation."),
                ("human", "Conversation: {conversation_history}")
            ])
            simple_chain = simple_prompt | llm
            fallback_summary = simple_chain.invoke({"conversation_history": conversation_history}).content
            
            ai_message = AIMessage(content=f"Based on our conversation, here is your sleep assessment:\n\n{fallback_summary}\n\nIs there anything you'd like to add or correct?")
            return {"messages": [ai_message], "summary_confirmed": True}
    
    else:
        # Final summary after patient additions
        prompt = ChatPromptTemplate.from_messages([
            ("system", get_final_summary_prompt()),
            ("human", get_final_summary_input_prompt())
        ])
        
        # Use high-token LLM for final detailed summary
        structured_llm_final = llm_summary.with_structured_output(SleepSummary)
        chain = prompt | structured_llm_final
        conversation_history = "\n".join([f"{msg.type}: {msg.content}" for msg in state["messages"]])
        referral_letter_text = state.get("referral_letter") or "No referral letter provided."
        patient_name = state.get("patient_name")
        
        try:
            final_summary = chain.invoke({
                "conversation_history": conversation_history,
                "referral_letter": referral_letter_text,
                "patient_name": patient_name
            })
            
            final_message = f"""Thank you for the additional information. Here is your final sleep assessment:

**UPDATED SLEEP SITUATION:**
{final_summary.patient_summary}

This concludes our comprehensive sleep consultation. Both patient and medical summaries are now complete and ready for your healthcare provider.

---
*Dr. SleepAI - AI Sleep Medicine Specialist*"""

            ai_message = AIMessage(content=final_message)
            
            return {
                "messages": [ai_message], 
                "terminate_reason": "completed",
                "doctor_summary": final_summary.doctor_summary,
                "patient_summary": final_summary.patient_summary,
                "urgency_level": final_summary.urgency_level
            }
            
        except Exception as e:
            print(f"Final Summary Error: {e}. Using fallback.")
            ai_message = AIMessage(content="Thank you for the additional information. Your comprehensive sleep consultation is now complete. Both patient and medical summaries have been generated for your healthcare provider.")
            return {"messages": [ai_message], "terminate_reason": "completed"}

# --- Definicija logike za usmeravanje (Routing) ---

def router_logic(state: GraphState) -> str:
    """
    Ruter: Odlučuje da li treba postaviti još pitanja ili generisati sažetak.
    Mora da se postavi minimum 5 pitanja pre generisanja sažetka.
    """
    print("---ROUTER LOGIC---")
    
    if state.get("summary_confirmed", False):
        return "generate_summary"
    
    # Check if we have at least 5 answered questions
    questions_answered = state.get("questions_answered", 0)
    print(f"Questions answered so far: {questions_answered}")
    
    if questions_answered < 5:
        print("Less than 5 questions answered, continuing with questions...")
        return "ask_question"

    # If we have 5+ questions answered, use AI to decide
    structured_llm = llm.with_structured_output(RouterDecision)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_router_system_prompt()),
        ("human", get_router_input_prompt())
    ])
    
    chain = prompt | structured_llm
    conversation_history = "\n".join([f"{msg.type}: {msg.content}" for msg in state["messages"]])
    referral_letter_text = state.get("referral_letter") or "No referral letter provided."
    
    try:
        response = chain.invoke({
            "conversation_history": conversation_history,
            "referral_letter": referral_letter_text,
            "patient_name": state.get("patient_name")
        })
        print(f"Router Decision: {response.decision}")
        return response.decision
    except Exception as e:
        print(f"Router Error: {e}. Defaulting to 'ask_question'.")
        return "ask_question"

def should_terminate(state: GraphState) -> Literal["__end__", "continue"]:
    """Proverava da li postoji razlog za prekid grafa (npr. detektovan rizik, dostignut limit...)."""
    if state.get("terminate_reason"):
        return END
    return "continue"

# --- Kreiranje grafa i podešavanje memorije ---

# 1. Inicijalizacija Checkpointer-a sa SQLite bazom.
# Ovo će kreirati fajl 'conversations.sqlite' za čuvanje stanja.
conn = sqlite3.connect("conversations.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)

# 2. Kreiranje grafa (StateGraph)
graph_builder = StateGraph(GraphState)

# 3. Dodavanje čvorova u graf
graph_builder.add_node("guardrail", guardrail_node)
graph_builder.add_node("suicide_check", suicide_check_node)
graph_builder.add_node("ask_question", ask_question_node)
graph_builder.add_node("summary", summary_node)

# Router node - uses router_logic function to decide next step
def router_node(state: GraphState) -> GraphState:
    """Router node that decides whether to ask more questions or generate summary."""
    return {"off_topic_counter": state.get("off_topic_counter", 0)}  # Router logic is handled by conditional edges

graph_builder.add_node("router", router_node)

# 4. Definisanje veza (Edges) između čvorova
graph_builder.set_entry_point("guardrail")

# Od Guardrail-a, ili se prekida ili se ide na Suicide Check
graph_builder.add_conditional_edges("guardrail", should_terminate, {END: END, "continue": "suicide_check"})

# Od Suicide Check-a, ili se prekida ili se ide na Ruter
graph_builder.add_conditional_edges("suicide_check", should_terminate, {END: END, "continue": "router"})

# Ruter je uslovna grana koja odlučuje sledeći korak
graph_builder.add_conditional_edges("router", router_logic, {
    "ask_question": "ask_question",
    "generate_summary": "summary"
})

# Nakon postavljanja pitanja, krug se završava i čeka se novi unos korisnika
graph_builder.add_edge("ask_question", END)

# Nakon generisanja sažetka, ili se prekida (finalni sažetak) ili se čeka unos (dodatak u sažetak)
graph_builder.add_conditional_edges("summary", should_terminate, {END: END, "continue": END})

# 5. Kompilacija grafa sa checkpointer-om za memoriju
app = graph_builder.compile(checkpointer=memory)


# --- Glavna petlja za pokretanje konverzacije ---
def main_loop():
    while True:
        user_id = input("\nEnter your User ID (e.g., 'user1', 'ana') or 'exit' to close: ")
        if user_id.lower() == 'exit':
            break
        if not user_id:
            continue

        config = {"configurable": {"thread_id": user_id}}
        
        print(f"\n--- Starting conversation for user: {user_id} ---")
        print("Type 'quit' to end this session, or 'switch' to change user.")
        
        # Always ask for referral letter - if provided, start fresh conversation
        print("\nStarting new consultation.")
        referral_letter_text = input("Please paste the referral letter text (or press Enter to skip):\n")
        
        # If referral letter is provided, always start a completely new conversation
        if referral_letter_text and referral_letter_text.strip():
            print("Referral letter provided - starting fresh consultation.")
            # Generate a unique thread ID to ensure fresh conversation
            import time
            fresh_thread_id = f"{user_id}_{int(time.time())}"
            config = {"configurable": {"thread_id": fresh_thread_id}}
            
            # Extract patient name from referral letter text if available
            patient_name = None
            if referral_letter_text and "Patient Name:" in referral_letter_text:
                # Extract name from format "Patient Name: John Doe"
                patient_name = referral_letter_text.replace("Patient Name:", "").strip()
            
            print(f"🔍 DEBUG: Extracted patient name: {patient_name}")
            
            # Generate personalized greeting using the patient name directly
            if patient_name:
                greeting_message = f"Hello {patient_name}! I'm Dr. SleepAI, your AI sleep medicine specialist. I'm here to help you with your sleep concerns. Could you please tell me in your own words what's been troubling you with your sleep?"
            else:
                greeting_message = get_greeting_message()
            
            print(f"🔍 DEBUG: Generated greeting: {greeting_message}")
            print(f"🔍 DEBUG: Referral letter text: {referral_letter_text[:200]}...")
            
            print(f"AI: {greeting_message}")
            
            # Initialize the conversation with the greeting and patient name
            initial_inputs = {
                "messages": [AIMessage(content=greeting_message)],
                "referral_letter": referral_letter_text,
                "patient_name": patient_name
            }
            
            # Run the graph once to initialize the state
            for event in app.stream(initial_inputs, config, stream_mode="values"):
                pass  # Just initialize the state, don't print anything
                
        else:
            # No referral letter - check if there's an existing conversation to resume
            past_state = app.get_state(config)
            is_new_conversation = not (past_state and past_state.values.get("messages"))
            
            if is_new_conversation:
                print("No referral letter provided - starting basic consultation.")
                # Use default greeting if no referral letter
                greeting_message = get_greeting_message()
                print(f"AI: {greeting_message}")
                
                # Initialize the conversation with the greeting
                initial_inputs = {
                    "messages": [AIMessage(content=greeting_message)],
                    "referral_letter": "No referral letter provided.",
                    "patient_name": None
                }
                
                # Run the graph once to initialize the state
                for event in app.stream(initial_inputs, config, stream_mode="values"):
                    pass  # Just initialize the state, don't print anything
            else:
                print("\n--- Previous messages found. Resuming conversation. ---")
                for msg in past_state.values['messages']:
                    if isinstance(msg, AIMessage): print(f"AI: {msg.content}")
                    elif isinstance(msg, HumanMessage): print(f"You ({user_id}): {msg.content}")
                print("---")
        
        while True:
            user_input = input(f"You ({user_id}): ")
            if user_input.lower() == "quit": exit(0)
            if user_input.lower() == "switch": break

            inputs = {"messages": [HumanMessage(content=user_input)]}
            # Referral letter is already added during initialization for new conversations

            # Pokrećemo graf sa ulazom i konfiguracijom za trenutnog korisnika
            for event in app.stream(inputs, config, stream_mode="values"):
                last_message = event["messages"][-1]
                if isinstance(last_message, AIMessage):
                    print(f"AI: {last_message.content}")

                if event.get("terminate_reason"):
                    print(f"\n--- Conversation for {user_id} finished. Reason: {event['terminate_reason']} ---")
                    break

            # Ako je konverzacija završena, izlazimo iz unutrašnje petlje
            if app.get_state(config).values.get("terminate_reason"):
                break

if __name__ == "__main__":
    # Generate and save the graph visualization before starting the main loop
    try:
        import os
        from pathlib import Path
        graph_image_path = Path(__file__).parent / "conversation_graph.png"
        print(f"Generating conversation graph visualization at: {graph_image_path}")
        app.get_graph().draw_png(str(graph_image_path))
    except Exception as e:
        print(f"Could not generate graph visualization: {e}")

    main_loop()