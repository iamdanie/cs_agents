import json
from openai import OpenAI
from dotenv import load_dotenv
from util import func_to_schema
from agents.triage_agent import triage_agent
from models.agent import Agent
from models.response import Response
import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

file = client.files.create(
  file=open("resources/car-stock.csv", "rb"),
  purpose='assistants'
)

def execute_tool_call(tool_call, tools, agent_name):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    print(f"{agent_name}:", f"{name}({args})")

    return tools[name](**args)


def run_full_turn(agent, messages):
	current_agent=agent
	num_init_messages=len(messages)
	messages = messages.copy()

	while True:

		tool_schemas = [func_to_schema(tool) for tool in current_agent.tools]
		tools = {tool.__name__: tool for tool in current_agent.tools}

		response = client.chat.completions.create(
			model=agent.model,
			messages=[{"role": "system", "content": current_agent.instructions}]
            + messages,
            tools=tool_schemas or None,
		)
		message = response.choices[0].message
		messages.append(message)

		if message.content:
			print(f"{current_agent.name}:", message.content)
		if not message.tool_calls:
			break

		for tool_call in message.tool_calls:
			result = execute_tool_call(tool_call, tools, current_agent.name)

			if type(result) is Agent:
				current_agent = result
				result = (
					f"Transferred to {current_agent.name}."
				)
			
			result_message = {
				"role": "tool",
				"tool_call_id": tool_call.id,
				"content": result,
			}

			messages.append(result_message)
	
	return Response(agent=current_agent, messages=messages[num_init_messages:])


agent = triage_agent
messages = []

while True:
    user = input("User: " + "\033[90m")
    messages.append({"role": "user", "content": user})

    response = run_full_turn(agent, messages)
    agent = response.agent
    messages.extend(response.messages)