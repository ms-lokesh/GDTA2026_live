import requests

prompts = [
    "When and where is GDTA 2026?",
    "What are the registration fees?",
    "What safari routes are available?",
    "How can I contact the organizers?",
    "How do I reach the venue and where can I stay?",
    "Tell me about the hackathon timeline and tracks",
]

for p in prompts:
    r = requests.post("http://127.0.0.1:5000/api/chat", json={"message": p}, timeout=20)
    r.raise_for_status()
    d = r.json()
    print("\n" + "=" * 80)
    print("PROMPT:", p)
    print("STATE:", d.get("state"))
    print("MESSAGE:")
    print(d.get("message"))
