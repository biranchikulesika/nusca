# cendrive

Python script to iterate through roll numbers, generate admit card ID candidates, submit them to the configured CBSE result endpoint, and save successful matches.

## Requirements

- Python 3.9+
- Packages:
  - `requests`
  - `python-dotenv`

Install dependencies:

```bash
pip install requests python-dotenv
```

## Configuration

1. Copy `.env.example` to `.env`.
2. Fill in all values:

```env
SCHOOL_NO=12345
START_ROLL=1000001
END_ROLL=1000100

RESULTS_CSV=valid_results.csv
PROGRESS_FILE=progress.txt

URL=https://cbseresults.nic.in/your-current-endpoint.asp
HEADERS='{"User-Agent":"Mozilla/5.0","Referer":"https://cbseresults.nic.in/your-current-page.asp","Origin":"https://cbseresults.nic.in"}'
```

Notes:
- `HEADERS` must be a JSON string value.
- Update `URL`/`Referer` to the latest active results page before running.

## Run

```bash
python cbse.py
```

## How it works

- Loads config from `.env`.
- Generates admit IDs from `A-Z` combinations and numeric suffixes.
- Sends POST requests for each roll number from `START_ROLL` to `END_ROLL`.
- Stores successful entries in `RESULTS_CSV`.
- Saves progress in `PROGRESS_FILE` so interrupted runs can resume.
- Deletes `PROGRESS_FILE` after completion.

## Output

`RESULTS_CSV` contains:

- Roll Number
- School Number
- Admit ID
