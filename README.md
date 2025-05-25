# Kavak Bot

An intelligent chatbot for Kavak that helps users find cars and provides customer support information using AI agents.

## Overview

This project implements a conversational bot for Kavak with two main agents:
- **Car Sales Agent**: Helps users find cars based on their preferences and create financial plans
- **Customer Success Agent**: Provides information about Kavak as a company and their services

The bot is built using:
- OpenAI's Agents API for natural language understanding and generation
- Vector stores for efficient knowledge retrieval (knowledge base)
- A triage system that routes queries to the appropriate agent

## Architecture overview

![Image](https://github.com/user-attachments/assets/758d3711-ac3a-4237-a908-db49d6d2baa1)

## Features

- Multi-agent architecture for specialized handling of different query types
- Guardrails to ensure safe and relevant responses
- Financial plan calculation for cars
- Vector-based search for car inventory and company knowledge
- Supports both CLI and WhatsApp (Twilio) modes

## Setup

### Prerequisites

- Python 3.9+
- Poetry for dependency management
- OpenAI API key
- Twilio account (for WhatsApp integration)

### Installation

1. Clone the repository
2. Install dependencies:
```bash
cd kavak_bot
poetry install
```

3. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

4. Edit the `.env` file with your API keys and configuration:
```
OPENAI_API_KEY=your_openai_api_key
KB_URL=your_knowledge_base_url
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number
```

### Running the CLI Version

```bash
poetry run python src/bot/main.py
```

### Running the WhatsApp API Version

1. Start the API server:
```bash
./start_api.sh
```

2. The server will start at http://localhost:8000

3. For development/testing, you can use the `/api/direct/message` endpoint without requiring a Twilio setup.

## WhatsApp Integration

### Setting up Twilio WhatsApp Sandbox

1. Sign up for a Twilio account at https://www.twilio.com/
2. Navigate to the Messaging > Try it out > Send a WhatsApp Message
3. Follow the instructions to connect to the Twilio WhatsApp Sandbox
4. Set up a webhook for incoming messages:
   - In the Twilio console, go to Messaging > Settings > WhatsApp Sandbox Settings
   - Set the "WHEN A MESSAGE COMES IN" webhook to your server's URL + `/webhook/incoming`
   - Example: `https://your-server.com/webhook/incoming`
   - For local testing, use a tool like ngrok to expose your local server

### Setting up for Production

1. Apply for a Twilio WhatsApp Business Profile
2. Set up production webhooks in the Twilio console
3. Update your `.env` file with production credentials
4. Deploy the API server to a cloud provider - (Optional) Install an ngrok server from your local machine and deploy it by using
   
```bash
brew install ngrok
ngrok http http://localhost:8000
```

## API Endpoints

The WhatsApp API exposes the following endpoints:

- **POST /webhook/incoming**: Webhook for incoming WhatsApp messages
- **POST /webhook/status**: Webhook for message status updates
- **POST /api/direct/message**: Test endpoint for sending messages without WhatsApp
- **POST /api/send**: Send a WhatsApp message programmatically (debug)
- **GET /api/sessions**: List active conversation sessions (debug)
- **DELETE /api/sessions/{phone_number}**: Delete a conversation session (debug)

## Development

### Project Structure

- `src/bot/main.py`: Core bot implementation
- `src/api/main.py`: WhatsApp API integration
- `resources/`: Contains car inventory and knowledge base files
