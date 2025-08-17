import gradio as gr
import asyncio
import tempfile
import os
import random
import string
from langchain_core.messages import HumanMessage, AIMessage

# Import our modules
from src.bot.graph import app
from src.referal_letter.extraction import AsyncReferralLetterExtractor

class SleepConsultationChat:
    def __init__(self):
        self.extractor = AsyncReferralLetterExtractor()
        self.conversation_state = None
        self.referral_data = None
        self.patient_name = ""
        self.conversation_complete = False
        
    async def process_referral_letter(self, pdf_file) -> tuple[str, str]:
        """Process uploaded PDF and extract referral information."""
        if pdf_file is None:
            return "No file uploaded", ""
            
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_file)
                tmp_path = tmp_file.name
            
            # Extract information from PDF
            result = await self.extractor.process_pdf(tmp_path)
            
            # Clean up temporary file
            os.unlink(tmp_path)
            
            if result and result.get("patient_name") != "ERROR":
                self.referral_data = result
                self.patient_name = result.get("patient_name", "")
                
                # Format the extracted information for display
                info_text = f"""
**Referral Letter Processed Successfully**

**Patient:** {result.get('patient_name', 'N/A')}
**Referring Doctor:** {result.get('doctor_name', 'N/A')}
**Date:** {result.get('referral_date', 'N/A')}
**Referred To:** {result.get('referred_to', 'N/A')}
**Reason:** {result.get('referral_reason', 'N/A')}
"""
                return info_text, self.patient_name
            else:
                return "❌ Failed to extract information from PDF. Please check the file format.", ""
                
        except Exception as e:
            return f"❌ Error processing PDF: {str(e)}", ""
    
    def start_conversation(self, patient_name_override: str = "") -> tuple[list, dict, str]:
        """Initialize the conversation with the bot."""
        try:
            # Reset conversation state
            self.conversation_complete = False
            # Use override name if provided, otherwise use extracted name
            final_patient_name = patient_name_override.strip() or self.patient_name
            
            # Prepare referral letter text for the bot - ONLY PATIENT NAME
            referral_text = ""
            if self.referral_data and final_patient_name:
                referral_text = f"Patient Name: {final_patient_name}"
            
            # Generate UNIQUE thread_id to ensure fresh conversation every time
            import time
            if final_patient_name:
                thread_id = f"{final_patient_name.replace(' ', '_').lower()}_{int(time.time())}"
            else:
                thread_id = f"user_{int(time.time())}_{random.randint(1000, 9999)}"
            
            config = {
                "recursion_limit": 150,
                "configurable": {
                    "thread_id": thread_id
                }
            }
            
            # Generate personalized greeting using patient name directly
            if final_patient_name:
                greeting_message = f"Hello {final_patient_name}! I'm Dr. SleepAI, your AI sleep medicine specialist. I'm here to help you with your sleep concerns. Could you please tell me in your own words what's been troubling you with your sleep?"
            else:
                # Default greeting without patient name
                from src.bot.helper import get_greeting_message
                greeting_message = get_greeting_message()
            
            # Initialize conversation state with greeting message and ensure all required fields are set
            initial_state = {
                "messages": [AIMessage(content=greeting_message)],
                "referral_letter": referral_text or "No referral letter provided.",
                "patient_name": final_patient_name,
                "off_topic_counter": 0,
                "last_question": "",
                "questions_answered": 0,
                "summary_confirmed": False,
                "terminate_reason": None,
                "doctor_summary": None,
                "patient_summary": None,
                "urgency_level": None
            }
            
            # Start the conversation - this will trigger the graph flow
            result = app.invoke(initial_state, config)
            
            # Ensure the initial greeting message is preserved in the result
            if result.get('messages') and len(result['messages']) > 0:
                # If the graph generated new messages, make sure the greeting is first
                all_messages = [AIMessage(content=greeting_message)]
                for msg in result['messages']:
                    if not (isinstance(msg, AIMessage) and msg.content == greeting_message):
                        all_messages.append(msg)
                result['messages'] = all_messages
            else:
                # If no messages in result, ensure greeting is there
                result['messages'] = [AIMessage(content=greeting_message)]
            
            self.conversation_state = result
            
            # Use the greeting message for chat history
            chat_history = [[None, greeting_message]]
            
            return chat_history, result, ""
            
        except Exception as e:
            error_msg = f"❌ Error starting conversation: {str(e)}"
            return [["", error_msg]], {}, ""
    
    def chat_with_bot(self, message: str, history: list, state: dict) -> tuple[list, dict, str]:
        """Handle chat interaction with the bot."""
        if not message.strip():
            return history, state, ""
        
        # Check if conversation is complete
        if self.conversation_complete:
            history.append([message, "The consultation has been completed. Please use the Reset button to start a new consultation."])
            return history, state, ""
            
        try:
            # Check if user message is already in history (from send_message_and_clear)
            # If not, add it (for backward compatibility)
            if not history or history[-1][0] != message:
                history.append([message, ""])
            
            # Use the same thread_id for consistency (stored in state)
            thread_id = state.get('thread_id', ''.join(random.choices(string.digits, k=8)))
            
            config = {
                "recursion_limit": 150,
                "configurable": {
                    "thread_id": thread_id
                }
            }
            
            # Pass only the new user message - let LangGraph's checkpointer handle state management
            inputs = {"messages": [HumanMessage(content=message)]}
            result = app.invoke(inputs, config)
            
            # Get the complete updated state from LangGraph's checkpointer
            updated_state = app.get_state(config)
            if updated_state and updated_state.values:
                state.clear()
                state.update(updated_state.values)
                state['thread_id'] = thread_id
            else:
                # Fallback if checkpointer fails
                state.update(result)
                state['thread_id'] = thread_id
            
            # Get bot's response
            if result.get('messages'):
                bot_response = result['messages'][-1].content
            else:
                bot_response = "I'm sorry, I encountered an issue. Could you please repeat your message?"
            
            # Update chat history with bot response
            history[-1][1] = bot_response
            
            # Check if conversation is complete
            self.conversation_complete = (
                result.get('terminate_reason') == 'completed' or
                (result.get('summary_confirmed', False) and result.get('doctor_summary'))
            )
            
            # Only show doctor summary when conversation is complete
            doctor_summary = ""
            if self.conversation_complete and result.get('doctor_summary'):
                doctor_summary = f"""**CLINICAL PRIORITY:** {result.get('urgency_level', 'ROUTINE').upper()}

**DOCTOR SUMMARY:**
{result.get('doctor_summary', '')}"""
            
            return history, state, doctor_summary
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            history[-1][1] = error_msg
            return history, state, ""
    
    def reset_conversation(self):
        """Reset the entire conversation."""
        self.conversation_state = None
        self.referral_data = None
        self.patient_name = ""
        self.conversation_complete = False
        return [], {}, "", "No referral letter uploaded", ""

# Initialize the chat system
chat_system = SleepConsultationChat()

# Async wrapper for PDF processing
def process_pdf_sync(pdf_file):
    if pdf_file is None:
        return "No file uploaded", ""
    return asyncio.run(chat_system.process_referral_letter(pdf_file))

# Create Gradio interface
with gr.Blocks(title="Sleep Consultation AI", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🌙 Sleep Consultation AI")
    gr.Markdown("Upload a referral letter (optional) and chat with Dr. SleepAI about your sleep concerns.")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📄 Referral Letter (Optional)")
            pdf_upload = gr.File(
                label="Upload PDF Referral Letter",
                file_types=[".pdf"],
                type="binary"
            )
            referral_info = gr.Markdown("No referral letter uploaded")
            patient_name_display = gr.Textbox(
                label="Patient Name (from referral or enter manually)",
                placeholder="Enter patient name if not extracted from PDF",
                interactive=True
            )
            start_btn = gr.Button("Start Consultation", variant="primary")
            reset_btn = gr.Button("Reset Consultation", variant="secondary")
        
        with gr.Column(scale=2):
            gr.Markdown("### 💬 Chat with Dr. SleepAI")
            chatbot = gr.Chatbot(
                label="Conversation",
                height=400,
                show_label=False
            )
            with gr.Row():
                msg = gr.Textbox(
                    label="Your message",
                    placeholder="Type your message here...",
                    lines=2,
                    scale=4
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)
            
            gr.Markdown("### 📋 Doctor Summary")
            doctor_summary_display = gr.Textbox(
                label="Medical Summary for Healthcare Provider",
                placeholder="Doctor summary will appear here after consultation...",
                lines=8,
                interactive=False,
                visible=True
            )
            
    # Hidden state to store conversation
    conversation_state = gr.State({})
    
    # Event handlers
    pdf_upload.change(
        fn=process_pdf_sync,
        inputs=[pdf_upload],
        outputs=[referral_info, patient_name_display]
    )
    
    start_btn.click(
        fn=chat_system.start_conversation,
        inputs=[patient_name_display],
        outputs=[chatbot, conversation_state, doctor_summary_display]
    )
    
    reset_btn.click(
        fn=chat_system.reset_conversation,
        inputs=[],
        outputs=[chatbot, conversation_state, doctor_summary_display, referral_info, patient_name_display]
    )
    
    def send_message_and_clear(message, history, state):
        # First clear the input and show user message immediately
        if not message.strip():
            return "", history, state, ""
        
        # Add user message to history immediately
        new_history = history + [[message, ""]]
        
        # Get bot response
        final_history, final_state, doctor_summary = chat_system.chat_with_bot(message, new_history, state)
        
        return "", final_history, final_state, doctor_summary
    
    # Handle both button click and Enter key
    msg.submit(
        fn=send_message_and_clear,
        inputs=[msg, chatbot, conversation_state],
        outputs=[msg, chatbot, conversation_state, doctor_summary_display]
    )
    
    send_btn.click(
        fn=send_message_and_clear,
        inputs=[msg, chatbot, conversation_state],
        outputs=[msg, chatbot, conversation_state, doctor_summary_display]
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7086,
        share=False
    )