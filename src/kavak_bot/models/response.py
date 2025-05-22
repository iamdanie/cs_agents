from pydantic import BaseModel
from typing import Optional
from models.agent import Agent

class Response(BaseModel):
	agent: Optional[Agent]
	messages: list = []