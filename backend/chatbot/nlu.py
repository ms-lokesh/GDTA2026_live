import json
import re
from typing import List, Optional

import requests
from django.conf import settings


def _extract_json_object(text: str) -> Optional[dict]:
    if not text:
        return None
    text = text.strip()

    # Try direct parse first.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Remove markdown code fences if present.
    fenced = text.replace("```json", "").replace("```", "").strip()
    try:
        obj = json.loads(fenced)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Extract first JSON object-like block.
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    return None


def gemini_match_choice(*, user_text: str, options: List[str], task_hint: str = "") -> Optional[str]:
    api_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    model = (getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash") or "gemini-2.5-flash").strip()

    if not api_key or not user_text or not options:
        return None

    prompt = (
        "You are a strict intent classifier for a chatbot. "
        "Return JSON only with shape: {\"match\": <one option exactly as provided OR null>}. "
        "Do not explain.\n\n"
        f"Task hint: {task_hint or 'Classify user reply to one option.'}\n"
        f"Options: {options}\n"
        f"User text: {user_text}\n"
        "Rules: pick null if uncertain."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 80},
    }

    try:
        resp = requests.post(url, json=payload, timeout=8)
        if resp.status_code >= 400:
            return None

        body = resp.json() or {}
        candidates = body.get("candidates") or []
        if not candidates:
            return None

        parts = ((candidates[0].get("content") or {}).get("parts") or [])
        text = "\n".join((p.get("text") or "") for p in parts if isinstance(p, dict)).strip()
        obj = _extract_json_object(text)
        if not obj:
            return None

        selected = obj.get("match")
        if selected is None:
            return None

        for option in options:
            if str(selected).strip() == option:
                return option
        return None
    except Exception:
        return None
