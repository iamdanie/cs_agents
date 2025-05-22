import asyncio
from agents import Agent, Runner, InputGuardrail, GuardrailFunctionOutput, FileSearchTool, function_tool
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

import os
import datetime

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

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

result = client.vector_stores.files.list(
    vector_store_id=vector_store.id
)
print(result)

class GuardrailCheck(BaseModel):
	is_homework: bool
	is_safe: bool
	is_relevant: bool
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

# Guardrail agent that checks if the user's input is a homework question
guardrail_agent = Agent(
    name="Smart Guardrail",
    instructions="""You are a guardrail agent responsible for validating user input.
				- Be polite if they just want to say hello or something casual, don't engage into irrelevent topics, though
				- Set `is_homework` to True if the input is about school subjects (math, history, science, etc.) or trying to buy a car.
				- Set `is_safe` to False if the input contains offensive, inappropriate, or dangerous content.
				- Set `is_relevant` to True if the input is within the tutoring or educational domain, or cars domain.
				Always explain your reasoning in the `reason` field.
				""",
    output_type=GuardrailCheck,
)

# Math tutor agent
math_tutor_agent = Agent(
    name="Math Tutor",
    handoff_description="Handles math-related questions.",
    instructions="You are a math tutor. Help the user solve math problems. "
                 "Explain your steps clearly and include examples when appropriate.",
)

# History tutor agent
history_tutor_agent = Agent(
    name="History Tutor",
    handoff_description="Handles history-related questions.",
    instructions="You are a history tutor. Help the user understand historical events. "
                 "Provide context and clear explanations.",
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
        "You are a sales agent for Kavak. You understand english and spanish and you're to help the user guiding them with the process of buying a car"
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
	),
	tools=[
        FileSearchTool(
			max_num_results=3,
			vector_store_ids=[vector_store.id],
		),
        create_financial_plan
	]
)

# Guardrail function
async def smart_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(GuardrailCheck)
    
    if not final_output.is_safe:
        return GuardrailFunctionOutput(output_info=final_output, tripwire_triggered=True)

    # 🟡 Warn or redirect if off-topic (optional)
    if not final_output.is_homework or not final_output.is_relevant:
        print("⚠️ Off-topic or irrelevant input:", final_output.reason)

    return GuardrailFunctionOutput(output_info=final_output, tripwire_triggered=False)

# Triage agent that routes to math or history tutors
triage_agent = Agent(
    name="Triage Agent",
    instructions="Determine whether the user's question is about math, history, or if they're showing intent to buy a car"
                 "and route the question to the correct specialist tutor or agent.",
    handoffs=[math_tutor_agent, history_tutor_agent, car_sales_agent],
    input_guardrails=[
        InputGuardrail(guardrail_function=smart_guardrail),
    ],
)

# Shared context for conversation state
conversation_context = {}


# Main conversation loop
async def main():
    conversation_history = []  # <- history across turns
    last_agent = triage_agent
    print("Start chatting with your assistant (type 'exit' to stop):\n")
    
    while True:
        user_input = input("User: ")
        if user_input.strip().lower() in {"exit", "quit"}:
            break

        try:
            runner_input = conversation_history + [{"content": user_input, "role": "user"}]
            result = await Runner.run(last_agent, input=runner_input, context=conversation_context)
            conversation_history = result.to_input_list()
            last_agent = result.last_agent
            print("Assistant:", result.final_output)
        except Exception as e:
            if "tripwire" in str(e).lower():
                print("Sorry, i can't respond to that, please rephrase.")
            else:
                print(f"Error: {e}")

# Entry point
if __name__ == "__main__":
    asyncio.run(main())