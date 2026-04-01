from llm.intent_resolver import resolve_intent

queries = [
    "What safari routes are available?",
    "How can I contact the organizers?",
    "Tell me about the hackathon timeline and tracks",
    "What are the registration fees?",
]

for q in queries:
    r = resolve_intent(q, use_llm=False)
    print(f"{q} => intent={r.intent.value}, confidence={r.confidence}, fallback={r.fallback_used}")
