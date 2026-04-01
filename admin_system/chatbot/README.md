# GDTA Chatbot

Event-specific chatbot for GDTA 2026 conference.

## Overview

This folder contains the chatbot functionality that is specific to the GDTA 2026 event. Unlike the reusable `event_manager`, this chatbot is tailored to GDTA's specific needs and integrates with the GDTA conference data.

## Files

- `routes/chat.py` - Backend chat API endpoint
- `chatbot-widget.js` - Frontend chat widget
- `chatbot-widget.html` - Standalone chat interface

## Integration

### With Admin System

The chatbot can be integrated with the admin system by:

1. **Add chat blueprint to app.py**:
   ```python
   from gdta_chatbot.routes.chat import chat_bp
   app.register_blueprint(chat_bp)
   ```

2. **Include widget in website**:
   ```html
   <!-- Add to your HTML pages -->
   <script src="gdta_chatbot/chatbot-widget.js"></script>
   ```

### Standalone Usage

Run just the chatbot:
```bash
# In admin_system/app.py, uncomment chat_bp registration
python app.py
```

Access at: `http://localhost:5001/chatbot`

## Features

- AI-powered conversation about GDTA 2026
- Session management
- Conference information queries
- Schedule planning assistance
- Registration initiation through chat

## Configuration

The chatbot uses:
- Google Gemini AI for language understanding
- Firebase for conversation storage
- Conference data from `data/conference.json` and `data/sessions.json`

## API Endpoint

```
POST /api/chat
Body: {
  "message": "User message",
  "session_id": "optional-session-id"
}

Response: {
  "response": "Bot response",
  "session_id": "session-identifier"
}
```

## Notes

- This chatbot is **event-specific** and not part of the reusable event_manager
- It contains GDTA 2026 specific logic and data
- For other events, you would need to create a similar event-specific chatbot
- The AI model and prompts are tailored to GDTA conference context

## Separation Rationale

The chatbot is kept separate from the reusable event_manager because:

1. **Event-Specific Context**: Contains GDTA-specific data and logic
2. **AI Dependencies**: May not be needed for all events
3. **Custom Integration**: Each event may want different chatbot behavior
4. **Modularity**: Easy to enable/disable without affecting core admin functions

---

To use this chatbot with your event, you would need to:
1. Update conference data files
2. Modify AI prompts for your event context
3. Adjust conversation flows
4. Update branding and styling
