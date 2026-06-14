# Gmail Deal Finder

Scans your Gmail promotions tab, extracts discount info (percentage off, dollar savings, promo codes, free shipping, expiry dates), scores each deal, and prints the best ones — one per store.

## How it works

1. Connects to Gmail via OAuth and reads your `CATEGORY_PROMOTIONS` label.
2. Parses each email with regex to extract deal signals.
3. If `--llm` is enabled, emails that produce no regex match are sent to a local [Ollama](https://ollama.com) model (`qwen3:0.6b`) for a second pass.
4. Scores every deal and keeps only the highest-scoring offer per store.
5. Prints the top N results with a direct link back to the email in Gmail.

### Scoring

| Signal | Points |
|---|---|
| Percentage discount | `pct × 1.5` (e.g. 20% → 30 pts) |
| Dollar savings | up to 50 pts |
| Promo code found | +10 pts |
| Free shipping | +8 pts |
| Expiry date present | +5 pts |

## Setup

### 1. Google Cloud credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **Gmail API**.
3. Create an **OAuth 2.0 Client ID** (Desktop app) and download it as `credentials.json`.
4. Place `credentials.json` in the `deal_finder/` directory.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Ollama for LLM fallback

Install [Ollama](https://ollama.com) and pull the model:

```bash
ollama pull qwen3:0.6b
```

## Usage

```bash
# One-shot scan (top 10 deals from last 50 promo emails)
python main.py

# Enable LLM fallback for emails the regex can't parse
python main.py --llm

# Watch mode — re-scans every 30 minutes
python main.py --watch

# Watch mode with custom interval
python main.py --watch --interval 15

# Tune results
python main.py --max-emails 100 --min-score 30 --top 5
```

### All flags

| Flag | Default | Description |
|---|---|---|
| `--llm` | off | Use Ollama (`qwen3:0.6b`) for emails that produce no regex match |
| `--watch` | off | Run continuously instead of once |
| `--interval MINUTES` | 30 | Minutes between checks in watch mode |
| `--max-emails N` | 50 | How many promo emails to fetch per run |
| `--min-score N` | 20 | Minimum score threshold to display a deal |
| `--top N` | 10 | Number of top deals to show |

## First run

The first time you run the script, a browser window will open asking you to authorize Gmail access. After you approve, a token is saved to `email_token.json` so you won't be prompted again.

**Keep `credentials.json` and `email_token.json` out of version control** — both are listed in `.gitignore`.

## Project structure

```
deal_finder/
├── main.py            # CLI entry point and output formatting
├── gmail_client.py    # Gmail OAuth + email fetching
├── deal_parser.py     # Regex extraction, Deal dataclass, scoring
├── ollama_fallback.py # LLM-based extraction via Ollama
└── requirements.txt
```
