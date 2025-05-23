import asyncio
from agents import Agent, Runner, InputGuardrail, GuardrailFunctionOutput, FileSearchTool, function_tool
from src.bot.models import (
    FinancialPlan,
    CarData,
    AgentOutput,
    GuardrailCheck,
    Installment
)
from src.bot.util import (
    initialize_bot_stores,
    parse_page_content
)
from openai import OpenAI
from dotenv import load_dotenv

import os
import datetime

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
kb_url = os.getenv("KB_URL")

client = OpenAI(api_key=api_key)

knowledge_base_text = parse_page_content(kb_url)

vector_store, kb_vector_store = initialize_bot_stores(client, knowledge_base_text)

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
    
    current_date = datetime.datetime.now()
    next_month = current_date.replace(day=1) + datetime.timedelta(days=32)
    first_day_next_month = next_month.replace(day=1)
    
    installments = []
    for i in range(1, num_installments + 1):
        payment_date = (first_day_next_month + datetime.timedelta(days=32 * (i-1))).replace(day=1)
        payment_date_str = payment_date.strftime("%d/%m/%Y")
        
        installment = Installment(
            amount=monthly_payment,
            installment_rn=i,
            payment_date=payment_date_str
        )
        installments.append(installment)
    
    return FinancialPlan(
        total_paid=total_paid,
        car_price=car_price,
        installments=installments,
        annual_interest_rate=interest_rate
    )

car_sales_agent = Agent(
    name="Kavak Car Sales Agent",
    handoff_description="Handles car buying intent questions.",
    instructions=(
        "You are a sales agent in Kavak. You understand english and spanish and you're only to help the user guiding them with the process of buying a car, you don't provide customer success information."
        "In all of your communication, make sure you speak as if you're part of the Kavak company"
        "Follow the following routine with the user:"
        "1. Ask them about any preferences on car features based on the properties within the attached file - don't jump into giving them options immediatly without gathering their preferences first"
        "2. Based on their given preferences, look up for options in the attached file and bring them some options based on what they need - if there are no matches, tell the user and start over from 1."
        "3. If the user explicitly ask for more options, provide them more options keeping the original preferences they gave in 1."
        "4. If the user shows buying intent or gives you one of the car models you provided, offer them a financial plan for that car"
        "5. If they confirm they want a financial plan, then gather the plan (installments number) and the deposit they are willing to give"
        "- The user can only ask for 72 installments (6 years) max and a minimum of 36 installments (3 years)"
        "6. If they provided the installments number (plan) and the deposit, pass the full car data, the plan and the deposit to the create financial plan function and give the created financial plan to the customer - show a resume of the list of installments, along with the interest rate and car price"
        "7. If they didn't provide the installments number (plan), failed to provide an allowed installments number, or the deposit amount is missing or wrong (it's wrong if they give you a deposit greater or equal the car price), ask for it two or three more times"
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

customer_success_agent = Agent(
     name="Kavak customer success agent",
     handoff_description="Handles queries about kavak information such as mission, current status, and information related to inspection centres location and schedules, you can't provide information about car stock or sales",
     instructions=(
        "You are a customer success agent in Kavak."
        "In all of your communication, make sure you speak as if you're part of the Kavak company"
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

async def smart_guardrail(ctx, _agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(GuardrailCheck)
    
    if not final_output.is_safe:
        return GuardrailFunctionOutput(output_info=final_output, tripwire_triggered=True)

    if not final_output.is_business:
        print("Off-topic or irrelevant input:", final_output.reason)

    return GuardrailFunctionOutput(output_info=final_output, tripwire_triggered=False)

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

conversation_context = {}

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
                print(f"{last_agent.name}: ", result.final_output.message)
        except Exception as e:
            if "tripwire" in str(e).lower():
                print("Sorry, i can't respond to that, please rephrase.")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(cli_conversation())