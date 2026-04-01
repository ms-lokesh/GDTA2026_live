import traceback
from llm.rag_engine import RAGEngine
import json
from pathlib import Path

base = Path(__file__).parent
conference = json.loads((base / "data" / "conference.json").read_text(encoding="utf-8"))
sessions = json.loads((base / "data" / "sessions.json").read_text(encoding="utf-8"))

engine = RAGEngine(conference, sessions)
queries = [
    "What safari routes are available?",
    "How can I contact the organizers?",
    "Tell me about the hackathon timeline and tracks",
]

for q in queries:
    print("\n===", q)
    try:
        print(engine.answer_question(q))
    except Exception:
        traceback.print_exc()
