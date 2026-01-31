# LLM Integration Setup - GDTA 2026 Chatbot

## 🎯 What This Does

Your chatbot now has **RAG (Retrieval-Augmented Generation)** capabilities:

✅ **Understands any phrasing** - "What time is the design workshop?" not just "when"  
✅ **Searches your data** - Automatically finds info in conference.json and sessions.json  
✅ **Natural responses** - Conversational answers instead of templates  
✅ **Smart fallback** - Works without API key (uses keyword matching)  

**Registration and Planning stay deterministic** - Backend controlled, no AI decisions.

---

## 🔑 Get Your API Key (Gemini - FREE)

### Option 1: Google Gemini (Recommended - Free tier)

1. Go to: https://makersuite.google.com/app/apikey
2. Click **"Get API Key"**
3. Click **"Create API Key"**
4. Copy the key (starts with `AIza...`)

### Option 2: OpenAI (Backup - Paid)

1. Go to: https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Copy the key (starts with `sk-...`)

---

## 📝 Setup Instructions

### Step 1: Create `.env` file

In your chatbot folder (`C:\Python310\GDTA2026\chatbot\`), create a file named `.env` (no extension):

```bash
# Copy .env.example to .env
copy .env.example .env
```

### Step 2: Add your API key

Open `.env` and paste your key:

**For Gemini:**
```
GOOGLE_API_KEY=AIzaSyC_your_actual_key_here
```

**For OpenAI (backup):**
```
OPENAI_API_KEY=sk-your_actual_key_here
```

### Step 3: Restart the server

```powershell
# Stop current server
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force

# Start server
.\.venv\Scripts\python.exe app.py
```

---

## ✅ Test It

Open the chatbot and try these questions:

**Natural language queries:**
- "What time does the design thinking workshop start?"
- "Who's speaking on Day 2?"
- "Tell me about sessions for students"
- "What's happening in the afternoon on March 15?"

**These still work without keywords!**
- When asked about dates → LLM searches conference.json
- When asked about sessions → LLM searches sessions.json
- Natural conversation → LLM understands intent

---

## 🔒 Security

✅ API key is in `.env` file (gitignored, never committed)  
✅ System works without API key (fallback to keywords)  
✅ LLM doesn't make decisions (backend stays in control)  
✅ All data grounded in your JSON files (no hallucination)  

---

## 💡 How It Works

```
User: "What sessions are about design?"
  ↓
Intent Resolver: conference_info (LLM detects intent)
  ↓
RAG Engine:
  1. Loads sessions.json
  2. Finds sessions with "design" in title/description
  3. Passes relevant data to Gemini
  4. Gemini generates natural response
  ↓
Response: "There are 3 design-focused sessions:
• 9:00-10:00 - Design Thinking in 2026
• 10:30-12:00 - Design Thinking for Student Projects
• 13:30-15:00 - Design Thinking for Social Impact"
```

**Without API key:**
- Uses keyword matching (original system)
- Basic templated responses
- Still fully functional

---

## 🚀 Ready to Use

Once you add the API key and restart, your chatbot will:
- Answer ANY question about GDTA 2026
- Search through all your conference data
- Respond naturally and conversationally
- Keep registration/planning deterministic

**No API key? No problem!** System works with keyword fallback.
