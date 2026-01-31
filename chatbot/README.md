# GDTA 2026 Chatbot Backend

**Production-ready, logic-controlled AI assistant for conference scheduling**

## 🎯 Architecture Overview

This is a **logic-first system** where:
- ✅ **Backend makes ALL decisions** (scheduling, conflict resolution, filtering)
- ✅ **AI only handles language** (understanding user intent, generating responses)
- ✅ **JSON files are the single source of truth**
- ❌ AI does NOT calculate schedules or invent data
- ❌ AI does NOT decide which sessions to include

```
User Input → Flask Backend → Deterministic Logic → Response
                    ↓
                LLM (language only)
```

---

## 📁 Project Structure

```
gdta-chatbot-backend/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── data/                       # Single source of truth
│   ├── conference.json         # Conference metadata & FAQ
│   └── sessions.json           # All sessions (2 days, parallel sessions)
│
├── logic/                      # Deterministic decision logic
│   ├── planner.py             # Core scheduling algorithm
│   ├── filters.py             # Session filtering rules
│   └── clash_detector.py      # Time conflict detection
│
└── routes/                     # API endpoints
    ├── chat.py                # Conversational interface
    └── plan.py                # Schedule building API
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd chatbot
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python app.py
```

Server starts at: **http://localhost:5000**

### 3. Test the API

#### Get all sessions:
```bash
curl http://localhost:5000/api/sessions
```

#### Build a schedule:
```bash
curl -X POST http://localhost:5000/api/plan \
  -H "Content-Type: application/json" \
  -d '{"interest": "student", "days": 2}'
```

#### Chat interface:
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need a schedule for a student", "state": "planning_mode"}'
```

---

## 🔌 API Endpoints

### `POST /api/chat`
Conversational interface with state management.

**Request:**
```json
{
  "message": "Can you help me build a schedule?",
  "state": "info_mode"
}
```

**Response:**
```json
{
  "message": "I'd be happy to help! Are you a student or industry professional?",
  "state": "planning_mode",
  "action": null,
  "data": null
}
```

**States:**
- `info_mode` - Answering questions about the conference
- `planning_mode` - Building personalized schedules

---

### `POST /api/plan`
Build a personalized 2-day schedule.

**Request:**
```json
{
  "interest": "student",
  "days": 2
}
```

**Response:**
```json
{
  "day1": [
    {
      "id": "keynote-1",
      "title": "Opening Keynote",
      "start": "09:00",
      "end": "10:00",
      ...
    },
    ...
  ],
  "day2": [...],
  "metadata": {
    "total_sessions": 8,
    "clashes_resolved": 4,
    "user_interest": "student",
    "validation": {
      "is_valid": true,
      "errors": []
    }
  }
}
```

**Parameters:**
- `interest` (required): `"student"` or `"industry"`
- `days` (optional): `1` or `2` (default: 2)

---

### `GET /api/sessions`
Get all available sessions.

**Response:**
```json
{
  "sessions": [
    {
      "id": "session-1",
      "title": "...",
      "day": 1,
      "start": "09:00",
      "end": "10:30",
      "tags": ["student"],
      "type": "workshop"
    },
    ...
  ]
}
```

---

### `GET /api/alternatives/<session_id>`
Get alternative sessions at the same time.

**Query params:** `?interest=student`

**Response:**
```json
{
  "session_id": "student-1a",
  "alternatives": [
    {
      "id": "industry-1a",
      "title": "...",
      ...
    }
  ]
}
```

---

### `POST /api/validate`
Validate a custom schedule for time conflicts.

**Request:**
```json
{
  "day1": ["session-1", "session-2"],
  "day2": ["session-3", "session-4"]
}
```

**Response:**
```json
{
  "valid": true,
  "errors": []
}
```

---

## 🧠 How the Logic Works

### 1. Filtering Logic (`logic/filters.py`)
- Filters sessions by user interest (student/industry)
- Automatically includes mandatory sessions (keynotes)
- Excludes breaks automatically
- Sorts chronologically

### 2. Clash Detection (`logic/clash_detector.py`)
- Detects overlapping sessions (same day + overlapping time)
- Ensures only ONE session per time slot
- Validates final schedule for conflicts

### 3. Schedule Planning (`logic/planner.py`)
**Deterministic decision algorithm:**

```python
For each time slot with parallel sessions:
  1. Filter out sessions that clash with already selected ones
  2. Prefer sessions matching user interest
  3. If multiple match, choose first one
  4. If none match, choose first available
```

**No randomness. No AI decisions. Fully auditable.**

---

## 📊 Dummy Data

`data/sessions.json` includes:
- ✅ 2 days of sessions
- ✅ Parallel sessions at same times
- ✅ Student and industry tracks
- ✅ Various types: keynote, workshop, talk, panel
- ✅ Realistic timing with breaks

Example parallel sessions:
```
Day 1, 10:30-12:00:
  - "Design Thinking for Student Projects" (student)
  - "Enterprise Design Systems at Scale" (industry)
```

---

## 🔧 Configuration

### Environment Variables
Create a `.env` file:

```env
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here
PORT=5000

# When ready for LLM integration:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

### Production Deployment
1. Set `FLASK_DEBUG=False`
2. Use a production WSGI server (gunicorn, waitress)
3. Configure proper CORS origins
4. Use environment secrets for API keys

---

## 🤖 LLM Integration (Future)

The placeholder function `call_llm_for_response()` in `routes/chat.py` is where you'd integrate OpenAI, Claude, or another LLM.

**Example integration:**

```python
import openai

def call_llm_for_response(user_message, context, state):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a conference assistant. Explain scheduling decisions made by the backend. Do NOT calculate schedules."},
            {"role": "user", "content": f"Context: {context}\n\nUser: {user_message}"}
        ]
    )
    return response.choices[0].message.content
```

**Critical rules for LLM:**
- ❌ Do NOT let LLM decide which sessions to include
- ❌ Do NOT let LLM calculate schedules
- ✅ Only use LLM to explain backend decisions
- ✅ Only use LLM to ask clarifying questions

---

## ✅ Testing the System

### Test 1: Build a student schedule
```bash
curl -X POST http://localhost:5000/api/plan \
  -H "Content-Type: application/json" \
  -d '{"interest": "student", "days": 2}'
```

**Expected:** 
- Sessions tagged "student" are included
- Keynotes are included
- No time conflicts
- Parallel sessions are resolved

### Test 2: Build an industry schedule
```bash
curl -X POST http://localhost:5000/api/plan \
  -H "Content-Type: application/json" \
  -d '{"interest": "industry", "days": 2}'
```

**Expected:** Different sessions (industry track)

### Test 3: Chat interaction
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "create a schedule for a student"}'
```

**Expected:** Backend detects intent, calls planner, returns schedule

---

## 📋 Key Features

✅ **Deterministic scheduling** - Same input always produces same output  
✅ **Parallel session handling** - Automatically resolves conflicts  
✅ **Interest-based filtering** - Student vs industry tracks  
✅ **Schedule validation** - Checks for time conflicts  
✅ **Extensible architecture** - Easy to add more logic  
✅ **No AI decision-making** - AI only for language  
✅ **Production-ready** - Error handling, CORS, logging  

---

## 🛠️ Extending the System

### Add new filtering rules:
Edit `logic/filters.py` and add functions like:
```python
def filter_by_topic(sessions, topics):
    # Your logic here
    pass
```

### Add new endpoints:
Create new routes in `routes/` and register in `app.py`:
```python
from routes.new_route import new_bp
app.register_blueprint(new_bp)
```

### Add more session metadata:
Update `data/sessions.json` and adjust logic accordingly.

---

## 📝 Notes

- **No database yet**: Uses JSON files. Add DB when needed.
- **No authentication**: Add when building registration flow.
- **No frontend**: This is backend only. Build React/Vue frontend separately.
- **Mock LLM**: Replace `call_llm_for_response()` with real integration.

---

## 🎓 Architecture Principles

1. **Logic-first, AI-enhanced**
   - Backend controls all decisions
   - AI only interprets and explains

2. **Deterministic and auditable**
   - Same input → same output
   - All decisions have clear rules

3. **JSON as single source of truth**
   - No data invention by AI
   - Easy to update and version

4. **Separation of concerns**
   - Routes handle HTTP
   - Logic modules handle decisions
   - Data files store facts

---

## 📞 Support

For questions or issues:
1. Check the code comments (extensively documented)
2. Review the logic modules to understand decisions
3. Test with provided curl commands

---

**Built with ❤️ for GDTA 2026**
