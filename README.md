# NuSca

A Python scraper for extracting CBSE result data and storing it in a normalized SQLite database.

The scraper:
- generates admit card IDs
- submits requests automatically
- parses result pages
- stores structured data in SQLite
- tracks scrape status per roll number
- supports safe restart without losing progress

Because manually checking thousands of result pages is a magnificent waste of human lifespan.

---

# Features

- SQLite database storage
- Automatic subject discovery
- Normalized database schema
- Duplicate-safe inserts
- Resume support using database state
- Failed roll tracking
- Ctrl + C safe termination
- WAL mode enabled for better SQLite performance

---

# Project Structure

```bash
.
├── .env
├── .env.example
├── .gitignore
├── nusca.py
├── README.md
└── requirements.txt
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/biranchikulesika/nusca.git
cd nusca
```

---

## Create Virtual Environment

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

---

## Install Requirements

```bash
pip install -r requirements.txt
```

---

# Environment Setup
Make a `.env` file from `.env.example`

```
cp .env.example .env
```

Open `.env` file and changes the values accordingly

Important:
- `HEADERS` must stay in a single line
- JSON format must be valid

One missing quote and Python immediately enters its dramatic phase.

---

# Run

```bash
python nusca.py
```

---

# Database Tables

The scraper creates:

| Table | Purpose |
|---|---|
| students | student details |
| subjects | subject registry |
| student_marks | marks and grades |
| scrape_status | roll processing status |

---

# Scrape Status System

Each roll number is tracked independently per school.

Possible statuses:

| Status | Meaning |
|---|---|
| success | valid result found |
| failed | all admit IDs exhausted |
| blocked | request temporarily blocked |
| error | unexpected runtime error |

This allows:
- safe restart
- retry support
- duplicate prevention
- partial reruns

---

# Capabilities

- Handles variable subject counts
- Detects additional subjects
- Avoids duplicate student insertion
- Automatically resumes previously incomplete datasets
- Supports large scraping runs
- Stores structured relational data for later analysis

---

# Limitations

- Depends on current HTML structure of target website
- Website layout changes can break parser
- Aggressive request rates may trigger blocking
- SQLite is not ideal for massive distributed workloads
- Does not use concurrency or proxy rotation

Government websites are fragile ecosystems held together by table tags and optimism.

---

# Disclaimer

This project is for educational and research purposes only.

You are responsible for:
- complying with website terms
- respecting rate limits
- following applicable laws and regulations

Do not use this irresponsibly.

---

# License

MIT License