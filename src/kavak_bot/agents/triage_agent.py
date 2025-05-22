from models.agent import Agent
from agents.sales_agent import transfer_to_sales
from agents.marketing_agent import transfer_to_marketing

triage_agent = Agent(
	name="Triage Agent",
    instructions=(
        "You are a customer service bot for Kavak. "
        "Introduce yourself. Always be very brief. "
        "Gather information to direct the customer to the right department. "
        "But make your questions subtle and natural."
    ),
    tools=[transfer_to_sales, transfer_to_marketing],
)