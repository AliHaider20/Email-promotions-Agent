import json
import re
from typing import Optional

import ollama

from deal_parser import Deal, _score, _sender_email

MODEL = "qwen3:0.6b"

PROMPT = """\
Extract deal information from this promotional email. Reply with ONLY a JSON object, no explanation.

JSON fields:
- discount_pct: integer or null  (e.g. 20 for "20% off", null if none)
- discount_amt: float or null    (e.g. 10.0 for "$10 off", null if none)
- promo_code: string or null     (the actual code like "SAVE20", null if none)
- free_shipping: boolean
- expiry: string or null         (expiry hint like "tonight", "Dec 31", null if none)

Subject: {subject}
Body: {body}
"""


def extract_via_llm(email: dict) -> Optional[Deal]:
    prompt = PROMPT.format(
        subject=email["subject"],
        body=email["body"][:800],  # keep context short for a 0.6b model
    )

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
            think=False,  # disable chain-of-thought to save tokens
        )
        raw = response["message"]["content"].strip()
    except Exception as e:
        print(f"  [ollama] error: {e}")
        return None

    data = _parse_json(raw)
    if not data:
        return None

    deal = Deal(
        store=_store_name(email["sender"]),
        subject=email["subject"],
        discount_pct=_int(data.get("discount_pct")),
        discount_amt=_float(data.get("discount_amt")),
        promo_code=_str(data.get("promo_code")),
        free_shipping=bool(data.get("free_shipping", False)),
        expiry=_str(data.get("expiry")),
        email_id=email.get("id", ""),
        date=email.get("date", ""),
        sender_email=_sender_email(email["sender"]),
    )

    if not any([deal.discount_pct, deal.discount_amt, deal.free_shipping, deal.promo_code]):
        return None

    deal.score = _score(deal)
    return deal


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> Optional[dict]:
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find a {...} block inside the response
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


def _store_name(sender: str) -> str:
    match = re.match(r"^([^<@\n]+?)(?:\s*<|$)", sender)
    name = match.group(1).strip() if match else sender
    name = re.sub(r"\s*(deals?|offers?|promo(?:tions?)?|newsletter|noreply|no[-\s]reply)\s*$",
                  "", name, flags=re.I)
    return name.strip() or sender


def _int(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _float(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _str(v) -> Optional[str]:
    return str(v).strip() if v and str(v).strip().lower() not in ("null", "none", "") else None
