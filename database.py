"""
Database layer — SQLite with schema for cases, documents, and templates.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'legal_intake.db')


def get_db():
    # Create the /data directory if it doesn't exist yet
    # exist_ok=True prevents an error if the folder is already there
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Open a connection to the SQLite database file at DB_PATH
    # If the file doesn't exist, SQLite creates it automatically
    conn = sqlite3.connect(DB_PATH)

    # Makes each row behave like a dictionary, so columns can be accessed
    # by name (row['client_name']) instead of by index (row[0])
    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

            -- Client info
            client_name     TEXT NOT NULL,
            client_email    TEXT,
            client_phone    TEXT,
            client_dob      TEXT,

            -- Incident info
            incident_date   TEXT NOT NULL,
            incident_type   TEXT NOT NULL,
            incident_description TEXT NOT NULL,
            incident_location TEXT,

            -- AI results
            claim_type      TEXT,
            claim_confidence REAL,
            claim_keywords  TEXT,
            viability_status TEXT,
            viability_explanation TEXT,
            limitation_ok   INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id     INTEGER NOT NULL,
            filename    TEXT NOT NULL,
            file_path   TEXT NOT NULL,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            extracted_text TEXT,
            extracted_names TEXT,
            extracted_dates TEXT,
            extracted_locations TEXT,
            extracted_keywords TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(id)
        );

        CREATE TABLE IF NOT EXISTS templates (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            claim_type  TEXT NOT NULL,
            content     TEXT NOT NULL
        );
    """)

    # Seed templates if empty
    cur.execute("SELECT COUNT(*) as c FROM templates")
    if cur.fetchone()['c'] == 0:
        _seed_templates(cur)

    conn.commit()
    conn.close()


def _seed_templates(cur):
    templates = [
        {
            "name": "Personal Injury — Initial Letter of Claim",
            "claim_type": "Personal Injury",
            "content": """LETTER OF CLAIM — PERSONAL INJURY

Date: {{GENERATED_DATE}}

Our Ref: {{CASE_ID}}

Dear Sir/Madam,

Re: Personal Injury Claim — {{CLIENT_NAME}}

We write on behalf of our client, {{CLIENT_NAME}}, date of birth {{CLIENT_DOB}}, in connection with injuries sustained on {{INCIDENT_DATE}}.

CIRCUMSTANCES OF THE INCIDENT

{{INCIDENT_DESCRIPTION}}

Location: {{INCIDENT_LOCATION}}

INJURIES SUSTAINED

Our client suffered injuries as a result of the above incident. Full details of the injuries and their impact will be provided following medical assessment.

LIABILITY

We contend that you are liable for our client's injuries by reason of negligence and/or breach of statutory duty.

LIMITATION

Please note that the relevant limitation period under the Limitation Act 1980 applies to this matter.

We invite you to respond within 21 days of receipt of this letter, confirming whether liability is admitted or denied.

Yours faithfully,

[Solicitor Name]
[Firm Name]

---
NOTE: This is a draft document generated for review purposes only. It does not constitute legal advice.
"""
        },
        {
            "name": "Clinical Negligence — Pre-Action Protocol Letter",
            "claim_type": "Clinical Negligence",
            "content": """PRE-ACTION PROTOCOL LETTER — CLINICAL NEGLIGENCE

Date: {{GENERATED_DATE}}

Our Ref: {{CASE_ID}}

Dear Sir/Madam,

Re: Clinical Negligence Claim — {{CLIENT_NAME}}

We act on behalf of {{CLIENT_NAME}}, date of birth {{CLIENT_DOB}}.

NATURE OF THE CLAIM

Our client received treatment on or around {{INCIDENT_DATE}}.

{{INCIDENT_DESCRIPTION}}

BREACH OF DUTY

We allege that the treatment provided fell below the standard expected of a reasonably competent practitioner in breach of the duty of care owed to our client.

CAUSATION

As a direct result of the alleged breach(es) of duty, our client has suffered loss and damage, particulars of which will be provided in due course.

RECORDS REQUEST

We request copies of all medical records relating to our client's treatment.

Please acknowledge receipt of this letter within 14 days and confirm the identity of your insurers.

Yours faithfully,

[Solicitor Name]
[Firm Name]

---
NOTE: This is a draft document generated for review purposes only. It does not constitute legal advice.
"""
        },
        {
            "name": "Housing Disrepair — Letter Before Action",
            "claim_type": "Housing Disrepair",
            "content": """LETTER BEFORE ACTION — HOUSING DISREPAIR

Date: {{GENERATED_DATE}}

Our Ref: {{CASE_ID}}

Dear Sir/Madam,

Re: Housing Disrepair — {{CLIENT_NAME}} — {{INCIDENT_LOCATION}}

We act for {{CLIENT_NAME}} who is a tenant at the above property.

DISREPAIR

{{INCIDENT_DESCRIPTION}}

Date disrepair first reported: {{INCIDENT_DATE}}

OBLIGATIONS

As landlord, you are obliged pursuant to Section 11 of the Landlord and Tenant Act 1985 and/or the terms of the tenancy agreement to keep the structure and exterior of the property in repair.

NOTICE

Please be advised that unless the disrepair is remedied within 21 days of the date of this letter, our client will issue proceedings without further notice for:

1. Damages for breach of repairing obligation
2. An order requiring you to carry out the necessary repairs
3. Costs

Yours faithfully,

[Solicitor Name]
[Firm Name]

---
NOTE: This is a draft document generated for review purposes only. It does not constitute legal advice.
"""
        }
    ]
    for t in templates:
        cur.execute(
            "INSERT INTO templates (name, claim_type, content) VALUES (?, ?, ?)",
            (t['name'], t['claim_type'], t['content'])
        )


# ─────────────────────── CRUD helpers ───────────────────────

def create_case(data: dict) -> int:
    """Insert a new case into the database and return its auto-generated ID."""
    conn = get_db()
    cur = conn.cursor()

    # INSERT all case fields; ? placeholders prevent SQL injection
    # data.get(..., '') uses an empty string default for optional fields
    cur.execute("""
        INSERT INTO cases (
            client_name, client_email, client_phone, client_dob,
            incident_date, incident_type, incident_description, incident_location,
            claim_type, claim_confidence, claim_keywords,
            viability_status, viability_explanation, limitation_ok
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data['client_name'], data.get('client_email', ''), data.get('client_phone', ''),
        data.get('client_dob', ''), data['incident_date'], data['incident_type'],
        data['incident_description'], data.get('incident_location', ''),
        data.get('claim_type'), data.get('claim_confidence', 0.0),
        data.get('claim_keywords', ''), data.get('viability_status'),
        data.get('viability_explanation'), data.get('limitation_ok', 1)
    ))

    case_id = cur.lastrowid  # ID assigned by SQLite to the row just inserted
    conn.commit()            # Persist the change to disk
    conn.close()
    return case_id           # Returned so the caller can redirect to /case/<id>


def get_case(case_id: int):
    """Fetch a single case by ID. Returns a dict, or None if not found."""
    conn = get_db()
    row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    conn.close()
    # Convert Row object to plain dict for easier use in templates;
    # return None if no matching case exists
    return dict(row) if row else None


def get_all_cases():
    """Fetch every case, newest first, for the dashboard table."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
    conn.close()
    # Convert each Row object to a dict so Jinja2 templates can access fields by name
    return [dict(r) for r in rows]


def update_case_ai(case_id: int, ai_data: dict):
    """Overwrite the AI-generated fields on an existing case (used by re-analyse)."""
    conn = get_db()
    # Only the six AI columns are updated; client/incident data is left untouched
    conn.execute("""
        UPDATE cases SET
            claim_type=?, claim_confidence=?, claim_keywords=?,
            viability_status=?, viability_explanation=?, limitation_ok=?
        WHERE id=?
    """, (
        ai_data['claim_type'], ai_data['claim_confidence'], ai_data['claim_keywords'],
        ai_data['viability_status'], ai_data['viability_explanation'],
        ai_data['limitation_ok'], case_id  # case_id goes last to match WHERE id=?
    ))
    conn.commit()
    conn.close()


def save_document(case_id, filename, file_path, extracted: dict) -> int:
    """Save an uploaded document record and its extracted entities. Returns the new doc ID."""
    conn = get_db()
    cur = conn.cursor()

    # Lists from the extractor (e.g. ['John Smith', 'Dr. Lee']) are joined into
    # comma-separated strings for simple storage in a single TEXT column
    cur.execute("""
        INSERT INTO documents (case_id, filename, file_path, extracted_text,
            extracted_names, extracted_dates, extracted_locations, extracted_keywords)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        case_id, filename, file_path,
        extracted.get('raw_text', ''),
        ', '.join(extracted.get('names', [])),      # e.g. "Mr John Smith, Dr. Lee"
        ', '.join(extracted.get('dates', [])),      # e.g. "15 March 2023, 2024-01-10"
        ', '.join(extracted.get('locations', [])),  # e.g. "St. Thomas Hospital, London"
        ', '.join(extracted.get('keywords', []))    # e.g. "fracture, whiplash"
    ))

    doc_id = cur.lastrowid  # ID of the newly inserted document row
    conn.commit()
    conn.close()
    return doc_id


def get_case_documents(case_id: int):
    """Fetch all documents uploaded for a given case, newest first."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM documents WHERE case_id=? ORDER BY uploaded_at DESC",
        (case_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_templates(claim_type: str = None):
    """
    Fetch document templates from the database.
    If claim_type is provided, return only templates for that category.
    If omitted, return all templates (used on the /templates page).
    """
    conn = get_db()
    if claim_type:
        # Filter to matching templates, e.g. only 'Personal Injury' templates
        rows = conn.execute(
            "SELECT * FROM templates WHERE claim_type=?", (claim_type,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM templates").fetchall()
    conn.close()
    return [dict(r) for r in rows]