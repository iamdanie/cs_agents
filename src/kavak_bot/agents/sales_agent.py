from models.agent import Agent
from agents.common import transfer_back_to_triage

def provide_financial_plan(stock_id):
    print(f"Item ID: {stock_id}")
    print("=================\n")
    print("ToDo: generate financial plan and send it to user!")
    return "success"

sales_agent = Agent(
	name="Sales Agent",
	instructions=(
        "You are a sales agent for Kavak."
        "Always answer in a sentence or less."
        "Follow the following routine with the user:"
        "1. Ask them about any preferences for cars regarding size, model, brand, price, or equipment.\n"
        "2. Based on their preferences, look up for options in the sources/car_stock.csv file and bring three of the most similar options based on their requirements\n"
        "3. Once user chooses one of the options, provide them with a financial plan of the selected car by the stock_id of the chosen option\n"
        ""
    ),
    tools=[provide_financial_plan, transfer_back_to_triage],
)

def transfer_to_sales():
    """User for anything sales or buying related."""
    return sales_agent