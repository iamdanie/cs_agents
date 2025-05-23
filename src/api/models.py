from pydantic_settings import BaseSettings
from pydantic import BaseModel
from typing import Optional

class Settings(BaseSettings):
    openai_api_key: str
    kb_url: str
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    webhook_url: Optional[str] = None

class Message(BaseModel):
    content: str
    role: str = "user"
    
class WhatsAppIncomingMessage(BaseModel):
    From: str  # WhatsApp phone number of the sender
    Body: str  # Message content
    SmsMessageSid: str  # Unique message ID
    
class WhatsAppOutgoingMessage(BaseModel):
    to: str
    message: str