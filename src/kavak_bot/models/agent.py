from pydantic import BaseModel

class Agent(BaseModel):
	name: str = "Agent"
	model: str = "gpt-4o"
	instructions: str = "You are a helpful agent"
	tools: list = []