# API Testing Guide

Quick reference for testing all endpoints with curl or Postman.

## Start the Server

```bash
python app.py
```

Server runs at: `http://localhost:5000`

---

## Test Commands

### 1. Health Check
```bash
curl http://localhost:5000/
```

### 2. Get All Sessions
```bash
curl http://localhost:5000/api/sessions
```

### 3. Build Student Schedule
```bash
curl -X POST http://localhost:5000/api/plan \
  -H "Content-Type: application/json" \
  -d "{\"interest\": \"student\", \"days\": 2}"
```

### 4. Build Industry Schedule
```bash
curl -X POST http://localhost:5000/api/plan \
  -H "Content-Type: application/json" \
  -d "{\"interest\": \"industry\", \"days\": 2}"
```

### 5. Chat - Request Schedule
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"I need a schedule for a student\"}"
```

### 6. Chat - Conference Info
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"When is the conference?\"}"
```

### 7. Get Alternatives for a Session
```bash
curl "http://localhost:5000/api/alternatives/student-1a?interest=student"
```

### 8. Validate Custom Schedule
```bash
curl -X POST http://localhost:5000/api/validate \
  -H "Content-Type: application/json" \
  -d "{\"day1\": [\"keynote-1\", \"student-1a\"], \"day2\": [\"keynote-2\", \"student-2a\"]}"
```

---

## Expected Behaviors

### ✅ Correct Behavior
- Same request always produces same schedule (deterministic)
- No two sessions overlap in time
- Student schedule includes student-tagged sessions + keynotes
- Industry schedule includes industry-tagged sessions + keynotes
- Breaks are automatically excluded
- Parallel sessions are resolved (only one selected per time slot)

### 🔍 Testing Parallel Session Resolution
Request a student schedule and check that:
- At 10:30-12:00 Day 1, only "Design Thinking for Student Projects" is included
- NOT "Enterprise Design Systems" (that's for industry)

Request an industry schedule and check that:
- At 10:30-12:00 Day 1, only "Enterprise Design Systems at Scale" is included
- NOT "Design Thinking for Student Projects"

---

## PowerShell Commands (Windows)

If curl doesn't work, use PowerShell:

```powershell
# Get sessions
Invoke-RestMethod -Uri http://localhost:5000/api/sessions

# Build schedule
$body = @{
    interest = "student"
    days = 2
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:5000/api/plan `
  -Method POST `
  -ContentType "application/json" `
  -Body $body

# Chat
$body = @{
    message = "I need a schedule for a student"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:5000/api/chat `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

---

## Testing with Python

```python
import requests

# Build schedule
response = requests.post('http://localhost:5000/api/plan', json={
    'interest': 'student',
    'days': 2
})

schedule = response.json()
print(f"Total sessions: {schedule['metadata']['total_sessions']}")
print(f"Valid: {schedule['metadata']['validation']['is_valid']}")

for session in schedule['day1']:
    print(f"{session['start']}: {session['title']}")
```

---

## Common Issues

### Port Already in Use
```bash
# Kill process on port 5000 (Windows)
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Or change port
set PORT=8000
python app.py
```

### CORS Errors
If testing from browser, CORS is enabled for all origins in development.
In production, update CORS config in `app.py`.

### Import Errors
Make sure you're in the chatbot directory and have activated the virtual environment.
