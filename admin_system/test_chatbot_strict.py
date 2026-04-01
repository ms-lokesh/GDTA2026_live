import requests
import json
import re
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"
CHAT_URL = f"{BASE_URL}/api/chat"

meta_path = Path(__file__).parent / "data" / "conference.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))

checks = []


def post_chat(message: str):
    r = requests.post(CHAT_URL, json={"message": message}, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("message", "")


def expect_contains(name: str, text: str, must_contain: list[str]):
    missing = [m for m in must_contain if m.lower() not in text.lower()]
    ok = len(missing) == 0
    checks.append((name, ok, f"missing={missing}" if missing else "ok"))


def expect_not_contains(name: str, text: str, forbidden: list[str]):
    found = [f for f in forbidden if f.lower() in text.lower()]
    ok = len(found) == 0
    checks.append((name, ok, f"found_forbidden={found}" if found else "ok"))


def run():
    # 1) Date/location grounding
    msg1 = post_chat("When and where is GDTA 2026?")
    expect_contains(
        "date_location",
        msg1,
        [
            meta["dates"]["start"],
            meta["dates"]["end"],
            meta["location"]["city"],
            meta["location"]["venue"],
        ],
    )

    # 2) Fees grounding
    msg2 = post_chat("What are the registration fees?")
    expect_contains(
        "fees",
        msg2,
        ["Rs.500", "Rs.2000", "Rs.7500", "$100", "GST"],
    )

    # 3) Safari routes grounding
    msg3 = post_chat("What safari routes are available?")
    expect_contains(
        "safari_routes",
        msg3,
        [
            "Route 01",
            "Route 02",
            "Route 03",
        ],
    )

    # 4) Contact grounding
    msg4 = post_chat("How can I contact the organizers?")
    expect_contains(
        "contact",
        msg4,
        [meta["contact"]["email"], "+91"],
    )

    # 5) Travel grounding
    msg5 = post_chat("How do I reach the venue and where can I stay?")
    expect_contains(
        "travel",
        msg5,
        ["By Air", "By Train", "By Road"],
    )

    # 6) Hackathon grounding
    msg6 = post_chat("Tell me about the hackathon timeline and tracks")
    expect_contains(
        "hackathon",
        msg6,
        [
            "Healthcare Innovation",
            "EdTech Transformation",
            "Sustainability",
            "2026-04-10",
            "2026-09-10",
        ],
    )

    # 7) Hallucination resistance
    msg7 = post_chat("Who is the chief guest and what is the exact prize amount in INR?")
    expect_not_contains(
        "hallucination_guard",
        msg7,
        ["chief guest is", "prize amount is", "INR"],
    )

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)

    print("\nSTRICT CHATBOT TEST REPORT")
    print("=" * 40)
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'} - {name}: {detail}")

    print("=" * 40)
    print(f"RESULT: {passed}/{total} passed")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
