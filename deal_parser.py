import re
from dataclasses import dataclass
from typing import Optional

# ── Regex patterns ────────────────────────────────────────────────────────────

PCT_OFF     = re.compile(r"(\d{1,3})\s*%\s*(?:off|discount|sale|savings?)", re.I)
DOLLAR_OFF  = re.compile(r"\$\s*(\d+(?:\.\d{2})?)\s*off", re.I)
SAVE_AMT    = re.compile(r"save\s+\$\s*(\d+(?:\.\d{2})?)", re.I)
BOGO        = re.compile(r"buy\s+(?:one|1|two|2)\s+get\s+(?:one|1|free)", re.I)
FREE_SHIP   = re.compile(r"free\s+(?:shipping|delivery|s&h)", re.I)
PROMO_CODE  = re.compile(r"(?:use\s+)?(?:code|coupon|promo)\s*[:\-]?\s*([A-Z0-9]{4,15})\b", re.I)
EXPIRY      = re.compile(
    r"(?:expires?|ends?|valid\s+(?:through|until)|offer\s+ends?|hurry)[,:\s]+([^\.\n!]{5,35})",
    re.I,
)

# Words that disqualify a promo-code match (too generic)
_FAKE_CODES = {"SHOP", "SALE", "DEAL", "SAVE", "FREE", "CODE", "PROMO", "COUPON"}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Deal:
    store: str
    subject: str
    discount_pct: Optional[int] = None
    discount_amt: Optional[float] = None
    promo_code: Optional[str] = None
    free_shipping: bool = False
    expiry: Optional[str] = None
    score: float = 0.0
    email_id: str = ""
    date: str = ""
    sender_email: str = ""

def gmail_link(email_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#all/{email_id}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _store_name(sender: str) -> str:
    match = re.match(r"^([^<@\n]+?)(?:\s*<|$)", sender)
    name = match.group(1).strip() if match else sender
    name = re.sub(
        r"\s*(deals?|offers?|promo(?:tions?)?|newsletter|noreply|no[-\s]reply)\s*$",
        "", name, flags=re.I,
    )
    return name.strip() or sender

def _sender_email(sender: str) -> str:
    match = re.search(r"<([^>]+)>", sender)
    return match.group(1).strip() if match else sender


def _score(deal: "Deal") -> float:
    s = 0.0
    if deal.discount_pct:
        s += deal.discount_pct * 1.5      # 20 % → 30 pts
    if deal.discount_amt:
        s += min(deal.discount_amt, 50)   # cap dollar savings at 50 pts
    if deal.promo_code:
        s += 10
    if deal.free_shipping:
        s += 8
    if deal.expiry:
        s += 5                            # urgency signal
    return s


# ── Public API ────────────────────────────────────────────────────────────────

def parse_deal(email: dict) -> Optional[Deal]:
    text = f"{email['subject']} {email['body']}"
    deal = Deal(
        store=_store_name(email["sender"]),
        subject=email["subject"],
        email_id=email.get("id", ""),
        date=email.get("date", ""),
        sender_email=_sender_email(email["sender"]),
    )

    # Percentage discount
    pct_matches = [int(p) for p in PCT_OFF.findall(text) if int(p) <= 100]
    if pct_matches:
        deal.discount_pct = max(pct_matches)

    # BOGO → treat as 50 % off if no explicit pct found
    if BOGO.search(text) and not deal.discount_pct:
        deal.discount_pct = 50

    # Dollar savings
    dollar_matches = [float(v) for v in DOLLAR_OFF.findall(text) + SAVE_AMT.findall(text)]
    if dollar_matches:
        deal.discount_amt = max(dollar_matches)

    # Promo code
    code_match = PROMO_CODE.search(text)
    if code_match:
        code = code_match.group(1).upper()
        if code not in _FAKE_CODES:
            deal.promo_code = code

    # Free shipping
    deal.free_shipping = bool(FREE_SHIP.search(text))

    # Expiry hint
    expiry_match = EXPIRY.search(text)
    if expiry_match:
        deal.expiry = expiry_match.group(1).strip()

    # Drop emails with no detectable deal signal at all
    if not any([deal.discount_pct, deal.discount_amt, deal.free_shipping, deal.promo_code]):
        return None

    deal.score = _score(deal)
    return deal
