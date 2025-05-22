from models.agent import Agent
from agents.common import transfer_back_to_triage

marketing_agent = Agent(
	name="Marketing Agent",
	instructions=(
        "You are a marketing agent for Kavak."
        "Follow the following routine with the user:"
        "1. Ask them what do they want to know about kavak and let them know you can help with information regarding the company like current company status and info related to inspection centres location and schedules.\n"
        "2. Based on their answer, look up for the requested data by visiting https://www.kavak.com/mx/blog/sedes-de-kavak-en-mexico,\n"
        "- Don't let them know where you're getting the information from\n"
        "3. If found, provide the requested information in a very structured, brief and understandable way to the user, otherwise, let them know that data is not available\n"
    ),
    tools=[transfer_back_to_triage],
)

def transfer_to_marketing():
    """User for anything kavak's company information and-or inspection centres related."""
    return marketing_agent