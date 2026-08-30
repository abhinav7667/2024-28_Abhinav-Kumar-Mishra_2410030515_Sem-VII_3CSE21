# NetSage AI — AI-Assisted Network Troubleshooting

**NetSage AI** is an academic Flask web application that combines deterministic rule checking with AI-generated diagnoses to help troubleshoot Cisco Packet Tracer network scenarios. Every AI diagnosis requires human review before it can be accepted — demonstrating responsible AI practices.

---

## Features

| Feature | Description |
|---|---|
| **37 Pre-loaded Cases** | VLAN, DHCP, DNS, Routing, ACL, NAT, Gateway, Wireless issues |
| **Rule Checker** | 9 deterministic checks (interface down, gateway mismatch, APIPA, ACL deny, etc.) |
| **AI Diagnosis** | Demo mode (mock) + live mode (OpenAI / Google Gemini / Anthropic) |
| **Human Review** | Accept / Edit / Reject any AI diagnosis |
| **Responsible AI Log** | Full audit trail of human corrections |
| **Custom Troubleshoot** | Enter any symptom + show command output for ad-hoc analysis |
| **Dashboard** | Charts (Chart.js) showing category, severity, and review distributions |
| **REST API** | `/api/stats` and `/api/cases` JSON endpoints |

---

## Tech Stack

- **Backend**: Python 3.10+ · Flask 3 · SQLAlchemy 2 · SQLite
- **Frontend**: Jinja2 · Vanilla CSS (dark mode) · Chart.js (CDN)
- **AI**: Abstracted service supporting OpenAI, Google Gemini, Anthropic, or Demo mode
- **Testing**: pytest

---

## Quick Start

### 1. Clone / Open the project

```bash
cd netsage-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment (optional)

```bash
copy .env.example .env
# Edit .env — set DEMO_MODE=true to run without an API key
```

### 4. Seed the database

```bash
python seed/seed_cases.py
python seed/seed_reviews.py   # optional — seeds sample reviews
```

### 5. Run the app

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## Project Structure

```
netsage-ai/
├── app.py                  # Flask application factory + routes
├── config.py               # Configuration (reads .env)
├── requirements.txt
├── .env.example
│
├── database/
│   ├── database.py         # SQLAlchemy db instance + init_db
│   └── models.py           # Case, Diagnosis, Review, RuleResult models
│
├── checker/
│   └── rule_checker.py     # 9 deterministic network rule checks
│
├── services/
│   ├── ai_service.py       # AI abstraction (demo + live mode)
│   ├── diagnosis_service.py# Orchestrates rule checks + AI + DB save
│   └── review_service.py   # Human review CRUD + stats + RA log
│
├── prompts/
│   └── diagnose_prompt.md  # System prompt used for live AI calls
│
├── data/
│   └── cases.csv           # 37 labelled network troubleshooting cases
│
├── seed/
│   ├── seed_cases.py       # Load cases.csv → database
│   └── seed_reviews.py     # Seed sample diagnoses + reviews
│
├── templates/              # Jinja2 HTML templates (12 pages)
│   ├── base.html
│   ├── dashboard.html
│   ├── cases.html
│   ├── case_detail.html
│   ├── diagnosis.html
│   ├── review.html
│   ├── reviews.html
│   ├── troubleshoot.html
│   ├── troubleshoot_result.html
│   ├── responsible_ai.html
│   ├── about.html
│   └── error.html
│
├── static/
│   ├── css/style.css       # Premium dark-mode CSS
│   └── js/app.js           # Client-side JS (sidebar, loading states, etc.)
│
└── tests/
    └── test_app.py         # 30 pytest tests
```

---

## Running Tests

```bash
pytest tests/ -v
```

Expected: **30 passed**.

---

## AI Mode Configuration

| Setting | Description |
|---|---|
| `DEMO_MODE=true` | Uses expected_fault from CSV as mock AI response. No API key needed. |
| `AI_PROVIDER=openai` | Calls OpenAI API. Set `AI_API_KEY` and `AI_MODEL` (e.g. `gpt-4o`). |
| `AI_PROVIDER=google` | Calls Google Gemini. Set `AI_API_KEY` and `AI_MODEL` (e.g. `gemini-1.5-pro`). |
| `AI_PROVIDER=anthropic` | Calls Anthropic Claude. Set `AI_API_KEY` and `AI_MODEL`. |

---

## Responsible AI Design

NetSage AI is built around the principle that **AI should assist, not replace, human judgement**:

1. **Every AI diagnosis is marked as pending** until a human reviews it.
2. **Human reviewers can Accept, Edit, or Reject** any diagnosis.
3. **The Responsible AI Log** records all edits and rejections for audit.
4. **Rule checker provides independent validation** to detect disagreements.
5. **Confidence scores** are shown to set appropriate expectations.

---

## Case Categories

- **VLAN** — Trunking, access port, allowed-list issues
- **Gateway** — Default gateway misconfiguration
- **DHCP** — Pool exhaustion, missing helper-address, APIPA
- **DNS** — Unreachable DNS, wrong server IP
- **Routing** — Missing routes, OSPF/EIGRP problems
- **ACL** — Implicit deny, wrong direction
- **NAT** — Missing NAT pool, overload misconfiguration
- **Wireless** — SSID mismatch, wrong security key

---

## Academic Use

This project was built as an academic demonstration of:
- Responsible AI + Human-in-the-Loop design
- Hybrid AI + deterministic rule system
- Flask/SQLAlchemy full-stack Python web app
- OSI model troubleshooting methodology

> **Note**: In DEMO mode, the "AI" response is derived from the CSV expected answers — no real LLM inference occurs. Switch `DEMO_MODE=false` and provide an API key to use real AI.
