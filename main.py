import argparse
import time

from gmail_client import fetch_promo_emails
from deal_parser import parse_deal, Deal, gmail_link


def _print_deal(rank: int, deal: Deal) -> None:
    print(f"{rank}. {deal.store}  <{deal.sender_email}>")
    print(f"   Date    : {deal.date}")
    print(f"   Subject : {deal.subject[:80]}")
    if deal.discount_pct:
        print(f"   Discount: {deal.discount_pct}% off")
    if deal.discount_amt:
        print(f"   Savings : ${deal.discount_amt:.2f} off")
    if deal.promo_code:
        print(f"   Code    : {deal.promo_code}")
    if deal.free_shipping:
        print(f"   Shipping: Free")
    if deal.expiry:
        print(f"   Expires : {deal.expiry}")
    print(f"   Score   : {deal.score:.0f}")
    if deal.email_id:
        print(f"   Link    : {gmail_link(deal.email_id)}")
    print()


def run(max_emails: int = 50, min_score: float = 20.0, top_n: int = 10, use_llm: bool = False) -> None:
    if use_llm:
        from ollama_fallback import extract_via_llm

    print(f"Fetching up to {max_emails} promotional emails...", flush=True)
    emails = fetch_promo_emails(max_results=max_emails)
    print(f"Fetched {len(emails)} emails. Parsing deals...\n")

    deals: list[Deal] = []
    llm_count = 0

    for email in emails:
        deal = parse_deal(email)

        # Regex found nothing — ask the model if --llm is on
        if deal is None and use_llm:
            deal = extract_via_llm(email)
            if deal:
                llm_count += 1

        if deal and deal.score >= min_score:
            deals.append(deal)

    if use_llm:
        print(f"  (LLM used for {llm_count} ambiguous emails)\n")

    # Keep only the best deal per store
    best: dict[str, Deal] = {}
    for deal in deals:
        key = deal.store.lower()
        if key not in best or deal.score > best[key].score:
            best[key] = deal

    top = sorted(best.values(), key=lambda d: d.score, reverse=True)[:top_n]

    if not top:
        print("No deals found above the minimum score threshold.\n")
        return

    print(f"Top {len(top)} deals\n" + "=" * 60 + "\n")
    for i, deal in enumerate(top, 1):
        _print_deal(i, deal)


def watch(interval_minutes: int = 30, **kwargs) -> None:
    print(f"Watching for deals every {interval_minutes} min — Ctrl+C to stop.\n")
    while True:
        run(**kwargs)
        print(f"Next check in {interval_minutes} minutes...\n")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gmail Deal Finder")
    parser.add_argument("--watch", action="store_true", help="Run continuously")
    parser.add_argument("--llm", action="store_true",
                        help="Use qwen3:0.6b via Ollama for emails the regex can't parse")
    parser.add_argument("--interval", type=int, default=30, metavar="MINUTES",
                        help="Minutes between checks when using --watch (default: 30)")
    parser.add_argument("--max-emails", type=int, default=50,
                        help="Max promo emails to fetch per run (default: 50)")
    parser.add_argument("--min-score", type=float, default=20.0,
                        help="Minimum deal score to display (default: 20)")
    parser.add_argument("--top", type=int, default=10,
                        help="Number of top deals to show (default: 10)")
    args = parser.parse_args()

    kwargs = dict(max_emails=args.max_emails, min_score=args.min_score, top_n=args.top, use_llm=args.llm)
    if args.watch:
        watch(interval_minutes=args.interval, **kwargs)
    else:
        run(**kwargs)
