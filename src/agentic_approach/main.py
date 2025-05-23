import asyncio
from agents import Agent, Runner, InputGuardrail, GuardrailFunctionOutput, FileSearchTool, function_tool
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests

import os
import datetime

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
kb_url = os.getenv("KB_URL")

client = OpenAI(api_key=api_key)

# Initialize vector stores and knowledge base
def initialize_bot_services():
    """Initialize the vector stores and other resources needed by the bot."""
    # Create car stock vector store
    file = client.files.create(
        file=open("resources/car_stock.json", "rb"),
        purpose="assistants"
    )
    file_id = file.id
    
    vector_store = client.vector_stores.create(name="Car Stock Search")
    
    client.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=file_id,
    )
    
    # Get webpage from the web, scrape it and save in a text file
    response = requests.get(kb_url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    content = soup.body
    
    for post_header in content.find_all('div', class_='single-post-header'):
        post_header.decompose()
        
    for sidebar in content.find_all('div', class_='sidebar'):
        sidebar.decompose()
        
    for header in content.find_all('header'):
        header.decompose()
        
    for nav in content.find_all('nav'):
        nav.decompose()
        
    for footer in content.find_all('footer'):
        footer.decompose()
        
    for h3 in content.find_all('h3'):
        if h3.string: 
            h3.string.replace_with(f"- {h3.string.upper()}")
        else:
            inner_text = h3.get_text(separator=' ', strip=True)
            h3.clear()
            h3.append(f"- {inner_text.upper()}\n")
              
    for li in content.find_all('li'):
        if li.string: 
            li.string.replace_with(f"-- {li.string.upper()}")
        else:
            inner_text = li.get_text(separator=' ', strip=True)
            li.clear()
            li.append(f"-- {inner_text.upper()}\n")
              
    for h2 in content.find_all('h2'):
        if h2.string: 
            h2.string.replace_with(f"{h3.string.upper()}\n")
        else:
            inner_text = h2.get_text(separator=' ', strip=True)
            h2.clear()
            h2.append(f"{inner_text.upper()}\n")
    
    text = content.get_text(separator='\n', strip=True)
    
    with open("resources/kavak_knowledge_base.txt", "w", encoding="utf-8") as file:
        file.write(text)
        
    # Create knowledge base vector store
    kb_file = client.files.create(
        file=open("resources/kavak_knowledge_base.txt", "rb"),
        purpose="assistants"
    )
    kb_file_id = kb_file.id
    
    kb_vector_store = client.vector_stores.create(name="Kavak knowledge base")
    
    client.vector_stores.files.create(
        vector_store_id=kb_vector_store.id,
        file_id=kb_file_id,
    )
    
    return vector_store, kb_vector_store

# Run initialization if this is the first run
# Initialize services
vector_store = None
kb_vector_store = None

# Run initialization once
def get_bot_services():
    global vector_store, kb_vector_store
    if vector_store is None or kb_vector_store is None:
        vector_store, kb_vector_store = initialize_bot_services()
    return vector_store, kb_vector_store

# Initialize the services
vector_store, kb_vector_store = get_bot_services()

# Model classes
class GuardrailCheck(BaseModel):
    is_business: bool
    is_safe: bool
    reason: str
    
class Installment(BaseModel):
    amount: float
    installment_rn: int
    payment_date: str
    
class FinancialPlan(BaseModel):
    car_price: float
    installments: list[Installment]
    annual_interest_rate: float
    
class CarData(BaseModel):
    stock_id: int
    price: float
    make: str
    model: str
    year: str
    version: str

class AgentOutput(BaseModel):
    message: str
    needsTriage: bool

# Guardrail agent that checks if the user's input is a homework question
guardrail_agent = Agent(
    name="Smart Guardrail",
    instructions="""You are a guardrail agent responsible for validating user input.
                - Be polite if they just want to say hello or something casual, but don't engage into irrelevent topics
                - Set `is_business` to True if the input is about kavak company or if the input is about the user trying to buy a car.
                - Set `is_safe` to False if the input contains offensive, inappropriate, or dangerous content.
                Always explain your reasoning in the `reason` field.
                """,
    output_type=GuardrailCheck,
)

@function_tool
async def create_financial_plan(car: CarData, plan: int, deposit: float) -> FinancialPlan:
    """Create a financial plan given car information

    Args:
        car: The full car data from the one they selected.
        plan: The number of installments the user chose for creating their financial plan.
        deposit: The amount of deposit the user pretends to invest to start their financial plan. 
    """
    
    interest_rate = 0.10
    car_price = car.price
    monthly_interest_rate = interest_rate / 12
    
    num_installments = int(plan)
    monthly_payment = (car_price-deposit) * (monthly_interest_rate * (1 + monthly_interest_rate) ** num_installments) / ((1 + monthly_interest_rate) ** num_installments - 1)
    
    total_paid = monthly_payment * num_installments
    
    # Calculate installment dates starting from next month
    current_date = datetime.datetime.now()
    next_month = current_date.replace(day=1) + datetime.timedelta(days=32)  # Move to next month
    first_day_next_month = next_month.replace(day=1)  # First day of next month
    
    # Create installment list
    installments = []
    for i in range(1, num_installments + 1):
        # Calculate payment date (first day of each month)
        payment_date = (first_day_next_month + datetime.timedelta(days=32 * (i-1))).replace(day=1)
        payment_date_str = payment_date.strftime("%d/%m/%Y")
        
        # Create installment object
        installment = Installment(
            amount=monthly_payment,
            installment_rn=i,
            payment_date=payment_date_str
        )
        installments.append(installment)
    
    return FinancialPlan(
        car_price=car_price,
        installments=installments,
        annual_interest_rate=interest_rate
    )


# Car sales agent
car_sales_agent = Agent(
    name="Car Sales Agent",
    handoff_description="Handles car buying intent questions.",
    instructions=(
        "You are a sales agent for Kavak. You understand english and spanish and you're only to help the user guiding them with the process of buying a car, you don't provide customer success information"
        "Follow the following routine with the user:"
        "1. Ask them about any preferences on car features based on the properties within the attached file - don't jump into giving them options immediatly without gathering their preferences first"
        "2. Based on their given preferences, look up for options in the attached file and bring them some options based on what they need - if there are no matches, tell the user and start over from 1."
        "3. If the user explicitly ask for more options, provide them more options keeping the original preferences they gave in 1."
        "4. If the user shows buying intent or gives you one of the car models you provided, offer them a financial plan for that car"
        "5. If they confirm they want a financial plan, then gather the plan (installments number) and the deposit they are willing to give"
        "6. If they provided the installments number (plan) and the deposit, pass the full car data, the plan and the deposit to the create financial plan function and give the created financial plan to the customer - show a resume of the list of installments, along with the interest rate and car price"
        "7. If they didn't provide the installments number (plan) or the deposit amount, ask for it two or three more times"
        "8. Help the user with precise answers if they ask any clarifying questions on the financial plan info you provided"
        "9. Ask them if you can help them with something else related cars information"
        "- If the user brings up a topic outside of car sales and car stock information, you will ask for triage support, you never offer information you don't have in your possesion"
    ),
    tools=[
        FileSearchTool(
            max_num_results=3,
            vector_store_ids=[vector_store.id],
        ),
        create_financial_plan
    ],
    output_type=AgentOutput
)

# Customer success agent
customer_success_agent = Agent(
     name="Kavak customer success agent",
     handoff_description="Handles queries about kavak information such as mission, current status, and information related to inspection centres location and schedules, you can't provide information about car stock or sales",
     instructions=(
        "You are a customer success agent for Kavak."
        "Follow the following routine with the user:"
        "1. Ask them what do they want to know about kavak and let them know you can help with information regarding the company like current company status and info related to inspection centres location and schedules"
        "- If they are asking for nearest inspection centres to their location, don't jump into providing options instantly; instead, collect user location references such as the state or city they're located, country, etc"
        "2. Based on their answer, look up for the requested data by querying the attached file"
        "- Don't let them know where you're getting the information from"
        "3. If found, provide the requested information in a very structured, brief and understandable way to the user"
        "- If the information they requested is not found within the attached file, don't invent one, just let them know unfortunately you don't have that information with you"
        "- If the user brings up a topic outside of your purview, for instance, showing buying intent, you will ask for triage support, you never offer information about car models to the user"
    ),
    tools=[
        FileSearchTool(
            vector_store_ids=[kb_vector_store.id],
        )
    ],
    output_type=AgentOutput
)

# Guardrail function
async def smart_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(GuardrailCheck)
    
    if not final_output.is_safe:
        return GuardrailFunctionOutput(output_info=final_output, tripwire_triggered=True)

    # 🟡 Warn or redirect if off-topic (optional)
    if not final_output.is_business:
        print("⚠️ Off-topic or irrelevant input:", final_output.reason)

    return GuardrailFunctionOutput(output_info=final_output, tripwire_triggered=False)

# Triage agent that routes to cs or sales
triage_agent = Agent(
    name="Triage Agent",
    instructions="Determine whether the user's question is about kavak company, or if they're showing intent to buy a car"
                 "and route the question to the correct agent.",
    handoffs=[customer_success_agent, car_sales_agent],
    input_guardrails=[
        InputGuardrail(guardrail_function=smart_guardrail),
    ],
    output_type=AgentOutput
)

# Shared context for conversation state
conversation_context = {}

# CLI conversation loop
async def cli_conversation():
    conversation_history = []
    last_agent = triage_agent
    print("Start chatting with your assistant (type 'exit', 'quit'. or 'bye' to stop):\n")
    
    while True:
        user_input = input("User: ")
        if user_input.strip().lower() in {"exit", "quit", "bye"}:
            break
        
        try:
            runner_input = conversation_history + [{"content": user_input, "role": "user"}]
            result = await Runner.run(last_agent, input=runner_input, context=conversation_context)
            
            if result.final_output.needsTriage:
                print("Transferring to another agent:")
                last_agent = triage_agent
                result = await Runner.run(last_agent, input=runner_input, context=conversation_context)
                
            print("result:", result.last_agent.name)
            conversation_history = result.to_input_list()
            last_agent = result.last_agent
            
            if hasattr(result.final_output, "message"):
                print("Assistant:", result.final_output.message)
        except Exception as e:
            if "tripwire" in str(e).lower():
                print("Sorry, i can't respond to that, please rephrase.")
            else:
                print(f"Error: {e}")

# Entry point
if __name__ == "__main__":
    asyncio.run(cli_conversation())