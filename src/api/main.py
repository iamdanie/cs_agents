"""
WhatsApp API integration for the Kavak Bot.
This module provides API endpoints to integrate the Kavak Bot with WhatsApp using Twilio's API.
"""
from agents import Runner
from typing import Dict
from fastapi import FastAPI, Request, Response, Depends, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from src.bot.main import (
    triage_agent
)
from src.api.models import (
    Settings,
    Message,
    WhatsAppOutgoingMessage,
    WhatsAppIncomingMessage
)

load_dotenv()

settings = Settings()

twilio_client = None
if settings.twilio_account_sid and settings.twilio_auth_token:
    twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

app = FastAPI(title="Kavak WhatsApp Bot API")

conversation_sessions: Dict[str, Dict] = {}
    
def validate_twilio_request(request_data, signature, url):
    """Validate that the request is coming from Twilio."""
    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(url, request_data, signature)

def get_or_create_conversation_session(phone_number: str):
    """Get or create a conversation session for a specific phone number."""
    if phone_number not in conversation_sessions:
        conversation_sessions[phone_number] = {
            "conversation_history": [],
            "last_agent": triage_agent,
            "context": {}
        }
    return conversation_sessions[phone_number]

async def process_message(phone_number: str, message_content: str):
    """Process a message using the bot and return a response."""
    session = get_or_create_conversation_session(phone_number)
    
    session["conversation_history"].append({"content": message_content, "role": "user"})
    
    try:
        result = await Runner.run(
            session["last_agent"], 
            input=session["conversation_history"],
            context=session["context"]
        )
        
        if result.final_output.needsTriage:
            print("Transferring to another agent...")
            session["last_agent"] = triage_agent
            result = await Runner.run(
                session["last_agent"],
                input=session["conversation_history"],
                context=session["context"]
            )
        
        session["conversation_history"] = result.to_input_list()
        session["last_agent"] = result.last_agent
        
        print("Current agent:", f"{session["last_agent"].name}")
        
        if hasattr(result.final_output, "message"):
            return result.final_output.message
        return "I'm processing your request but couldn't generate a response."
    
    except Exception as e:
        if "tripwire" in str(e).lower():
            return "Sorry, I can't respond to that, please rephrase."
        return f"An error occurred: {str(e)}"

async def send_whatsapp_message(to: str, message_content: str):
    """Send a WhatsApp message using Twilio."""
    try:
        message = twilio_client.messages.create(
            body=message_content,
            from_=f"whatsapp:{settings.twilio_phone_number}",
            to=f"whatsapp:{to}"
        )
        return {"status": "sent", "sid": message.sid}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
async def handle_message(phone_number: str, message_content: str):
    """Handle a message and send the response back via WhatsApp."""
    
    response_message = await process_message(phone_number, message_content)
    
    await send_whatsapp_message(phone_number, response_message)

"""
Webhook endpoints needed for Twilio integration
"""

@app.post("/webhook/incoming")
async def incoming_message(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Webhook endpoint for incoming WhatsApp messages from Twilio."""
    form_data = await request.form()
    form_dict = dict(form_data)
    
    twilio_signature = request.headers.get("X-Twilio-Signature", "")
    
    scheme = request.headers.get('X-Forwarded-Proto', 'https')
    host = request.headers.get('X-Forwarded-Host', request.url.hostname)
    full_url = f"{scheme}://{host}{request.url.path}"
    
    print('URL', full_url)

    if not validate_twilio_request(form_dict, twilio_signature, full_url):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    
    whatsapp_message = WhatsAppIncomingMessage(
        From=form_dict.get("From", ""),
        Body=form_dict.get("Body", ""),
        SmsMessageSid=form_dict.get("SmsMessageSid", "")
    )
    
    background_tasks.add_task(
        handle_message,
        whatsapp_message.From.replace("whatsapp:", ""),
        whatsapp_message.Body
    )
    
    return Response(status_code=200)

@app.post("/webhook/status")
async def message_status(request: Request):
    """Webhook endpoint for message status updates from Twilio."""
    try:
        form_data = await request.form()
        form_dict = dict(form_data)
        print(f"Status update received: {form_dict}")
        return {"status": "received"}
    except Exception as e:
        print(f"Error in status webhook: {str(e)}")
        return {"status": "error"}

"""
Debugging endpoints ToDo: secure these ones later
"""

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/send")
async def send_message(message: WhatsAppOutgoingMessage):
    """API endpoint to send a WhatsApp message programmatically."""
    result = await send_whatsapp_message(message.to, message.message)
    return result

@app.get("/api/sessions")
async def get_sessions():
    """API endpoint to get all active conversation sessions (for debugging/admin)."""
    return {
        phone: {
            "message_count": len(session["conversation_history"]),
            "last_agent": session["last_agent"].name
        }
        for phone, session in conversation_sessions.items()
    }

@app.delete("/api/sessions/{phone_number}")
async def delete_session(phone_number: str):
    """API endpoint to delete a session"""
    if phone_number in conversation_sessions:
        del conversation_sessions[phone_number]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.post("/api/direct/message")
async def direct_message(message: Message, phone_number: str):
    """API endpoint for direct messaging without going through Twilio (for testing)."""
    response_message = await process_message(phone_number, message.content)
    return {"response": response_message}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)