# Kavak Bot WebSocket Implementation

This README explains how to use the WebSocket-enabled Kavak Bot that allows for real-time communication between the backend agent system and a frontend client.

## Project Structure

```
kavak_bot/
├── frontend/
│   ├── index.html       # Simple WebSocket client
│   └── serve.py         # Simple HTTP server for frontend
├── src/
│   └── agentic_approach/
│       └── main.py      # Main app with WebSocket support
└── resources/
    ├── car_stock.json   # Car inventory data
    └── kavak_knowledge_base.txt  # Knowledge base content
```

## Running the Application

### Backend (WebSocket Server)

To run the backend WebSocket server:

```bash
cd /path/to/kavak_bot
poetry run python src/agentic_approach/main.py
```

This will start the WebSocket server at http://localhost:8000

### Frontend (WebSocket Client)

To run the frontend client:

```bash
cd /path/to/kavak_bot
poetry run python frontend/serve.py
```

Then open http://localhost:8080/index.html in your web browser.

### CLI Mode

You can still run the bot in CLI mode:

```bash
cd /path/to/kavak_bot
poetry run python src/agentic_approach/main.py --cli
```

## WebSocket API

### Endpoints

- WebSocket: `ws://localhost:8000/ws/{client_id}`
  - `client_id`: A unique identifier for the client session

### Communication Protocol

**Client to Server:**
- Send text messages as strings

**Server to Client:**
- Receives JSON objects with the following structure:
```json
{
  "message": "The response message",
  "agent": "Name of the responding agent"
}
```

## Integrating with Other Frontend Frameworks

To integrate with frontend frameworks like React, Angular, or Vue:

1. Replace the WebSocket handling code in your framework
2. Connect to `ws://localhost:8000/ws/{client_id}`
3. Send text messages and parse the JSON responses

Example for React:
```jsx
import { useEffect, useState } from 'react';

function ChatComponent() {
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const clientId = Date.now().toString();

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`);
    
    ws.onopen = () => {
      console.log('Connected to server');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, {
        text: data.message,
        agent: data.agent,
        type: data.agent.toLowerCase().includes('system') ? 'system' : 'assistant'
      }]);
    };
    
    setSocket(ws);
    
    return () => {
      ws.close();
    };
  }, []);

  const sendMessage = () => {
    if (input.trim() && socket && socket.readyState === WebSocket.OPEN) {
      socket.send(input);
      setMessages(prev => [...prev, { text: input, type: 'user' }]);
      setInput('');
    }
  };

  return (
    <div>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.type}`}>
            {msg.agent && <div className="agent">{msg.agent}</div>}
            {msg.text}
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}
```

## Security Considerations

- The CORS configuration is currently set to allow all origins (`*`). In production, specify your frontend domain.
- Implement authentication to secure your WebSocket connections.
- Consider rate limiting and other security measures in a production environment.
