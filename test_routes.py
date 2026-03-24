"""
test_routes.py — Integration tests for all Flask routes.
Run from the project root:
    python test_routes.py          (no dependencies needed)
    pytest test_routes.py -v       (if pytest is installed)
"""

import sys
import os
import io
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import init_db, create_case


# ─────────────────────────────────────────────────────────────────
# TEST SETUP
# ─────────────────────────────────────────────────────────────────

def get_test_client():
    """
    Create a fresh Flask test client with a temporary database.
    Each call gives an isolated environment — no shared state.
    """
    app = create_app()

    # Use a temp file as the test database so real data is never touched
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    app.config['DATABASE'] = db_path
    app.config['TESTING'] = True

    # Override the DB path used by database.py
    import database
    original_path = database.DB_PATH
    database.DB_PATH = db_path

    with app.app_context():
        init_db()

        # Seed one case and ensure templates exist (init_db seeds them)
        case_id = create_case({
            'client_name':          'Jane Smith',
            'client_email':         'jane@example.com',
            'client_phone':         '07700000000',
            'client_dob':           '1990-01-01',
            'incident_date':        '2024-03-15',
            'incident_type':        'Personal Injury',
            'incident_description': 'I slipped on a wet floor and fractured my wrist.',
            'incident_location':    'Manchester',
            'claim_type':           'Personal Injury',
            'claim_confidence':     0.9,
            'claim_keywords':       'slip, fracture',
            'viability_status':     'Potentially Viable',
            'viability_explanation':'Within limitation period.',
            'limitation_ok':        1,
        })

    client = app.test_client()

    # Return client, app context, and cleanup info
    return client, app, db_fd, db_path, original_path, database


def cleanup(db_fd, db_path, database, original_path):
    """Restore original DB path and remove temp file."""
    database.DB_PATH = original_path
    os.close(db_fd)
    try:
        os.unlink(db_path)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────
# ROUTE TESTS
# ─────────────────────────────────────────────────────────────────

def test_IT01_get_dashboard():
    """IT-01: GET / — dashboard returns 200 and renders cases table."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        with app.app_context():
            response = client.get('/')
        assert response.status_code == 200
        assert b'Jane Smith' in response.data       # seeded case appears
        assert b'Personal Injury' in response.data
    finally:
        cleanup(db_fd, db_path, db, orig)


def test_IT02_get_intake_form():
    """IT-02: GET /intake — intake form returns 200."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        with app.app_context():
            response = client.get('/intake')
        assert response.status_code == 200
        assert b'intake' in response.data.lower() or b'client' in response.data.lower()
    finally:
        cleanup(db_fd, db_path, db, orig)


def test_IT03_post_intake_valid():
    """IT-03: POST /intake with all required fields — redirects to /case/<id>."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        with app.app_context():
            response = client.post('/intake', data={
                'client_name':          'John Doe',
                'client_email':         'john@example.com',
                'client_phone':         '07711111111',
                'client_dob':           '1985-06-14',
                'incident_date':        '2024-06-01',
                'incident_type':        'Personal Injury',
                'incident_description': 'I was involved in a road traffic accident and suffered whiplash.',
                'incident_location':    'London',
            }, follow_redirects=False)

        # Expect a redirect (302) to /case/<id>
        assert response.status_code == 302
        assert b'/case/' in response.data or '/case/' in response.headers.get('Location', '')
    finally:
        cleanup(db_fd, db_path, db, orig)


def test_IT04_post_intake_missing_name():
    """IT-04: POST /intake without client_name — returns 200 with error message."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        with app.app_context():
            response = client.post('/intake', data={
                'client_name':          '',            # missing
                'incident_date':        '2024-06-01',
                'incident_type':        'Personal Injury',
                'incident_description': 'I slipped on a wet floor.',
                'incident_location':    'Manchester',
            }, follow_redirects=True)

        # Should re-render the form with an error — not redirect
        assert response.status_code == 200
        assert b'required' in response.data.lower() or b'error' in response.data.lower()
    finally:
        cleanup(db_fd, db_path, db, orig)


def test_IT05_get_case_exists():
    """IT-05: GET /case/1 — returns 200 and displays case data."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        with app.app_context():
            response = client.get('/case/1')
        assert response.status_code == 200
        assert b'Jane Smith' in response.data
    finally:
        cleanup(db_fd, db_path, db, orig)


def test_IT06_get_case_not_found():
    """IT-06: GET /case/9999 — case does not exist, redirects with 'Case not found'."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        with app.app_context():
            response = client.get('/case/9999', follow_redirects=True)
        assert response.status_code == 200
        assert b'not found' in response.data.lower() or b'case not found' in response.data.lower()
    finally:
        cleanup(db_fd, db_path, db, orig)


def test_IT07_upload_txt_file():
    """IT-07: POST /case/1/upload with a .txt file — redirects and stores extraction."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        # Create a synthetic text file in memory
        file_content = (
            b"WITNESS STATEMENT\n"
            b"Name: Dr. John Smith\n"
            b"Date of incident: 15th March 2024\n"
            b"Location: Manchester Royal Infirmary\n"
            b"The patient suffered a fracture and whiplash injury.\n"
        )
        data = {
            'document': (io.BytesIO(file_content), 'statement.txt')
        }
        with app.app_context():
            response = client.post(
                '/case/1/upload',
                data=data,
                content_type='multipart/form-data',
                follow_redirects=False
            )
        # Should redirect back to case detail after successful upload
        assert response.status_code == 302
    finally:
        cleanup(db_fd, db_path, db, orig)


def test_IT08_upload_invalid_extension():
    """IT-08: POST /case/1/upload with .exe file — rejected with error message."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        data = {
            'document': (io.BytesIO(b'malicious content'), 'virus.exe')
        }
        with app.app_context():
            response = client.post(
                '/case/1/upload',
                data=data,
                content_type='multipart/form-data',
                follow_redirects=True
            )
        assert response.status_code == 200
        assert b'invalid' in response.data.lower() or b'file type' in response.data.lower()
    finally:
        cleanup(db_fd, db_path, db, orig)


def test_IT09_generate_document():
    """IT-09: GET /case/1/generate/1 — returns 200 with populated document."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        with app.app_context():
            response = client.get('/case/1/generate/1')
        assert response.status_code == 200
        # Generated doc should contain the client's name from the seeded case
        assert b'Jane Smith' in response.data
    finally:
        cleanup(db_fd, db_path, db, orig)


def test_IT10_get_templates_list():
    """IT-10: GET /templates — returns 200 and lists all 3 templates."""
    client, app, db_fd, db_path, orig, db = get_test_client()
    try:
        with app.app_context():
            response = client.get('/templates')
        assert response.status_code == 200
        # All three claim types should appear
        assert b'Personal Injury'    in response.data
        assert b'Clinical Negligence' in response.data
        assert b'Housing Disrepair'  in response.data
    finally:
        cleanup(db_fd, db_path, db, orig)


# ─────────────────────────────────────────────────────────────────
# STANDALONE RUNNER
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        ("IT-01 GET /                     — dashboard renders",        test_IT01_get_dashboard),
        ("IT-02 GET /intake               — form renders",             test_IT02_get_intake_form),
        ("IT-03 POST /intake valid        — redirects to /case/<id>",  test_IT03_post_intake_valid),
        ("IT-04 POST /intake missing name — error shown",              test_IT04_post_intake_missing_name),
        ("IT-05 GET /case/1              — case data displayed",       test_IT05_get_case_exists),
        ("IT-06 GET /case/9999           — case not found redirect",   test_IT06_get_case_not_found),
        ("IT-07 POST upload .txt         — redirects, stored",         test_IT07_upload_txt_file),
        ("IT-08 POST upload .exe         — rejected with error",       test_IT08_upload_invalid_extension),
        ("IT-09 GET /case/1/generate/1  — document rendered",         test_IT09_generate_document),
        ("IT-10 GET /templates           — all 3 templates listed",    test_IT10_get_templates_list),
    ]

    passed = 0
    failed = 0

    print("\nRunning 10 route integration tests...\n")
    print(f"  {'Status':<6}  Test")
    print(f"  {'──────':<6}  {'─' * 55}")

    for name, fn in tests:
        try:
            fn()
            print(f"  PASS    {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL    {name}")
            print(f"          → {e}")
            failed += 1

    print(f"\n{'─' * 63}")
    print(f"  {passed} passed   {failed} failed   {len(tests)} total")

    if failed:
        sys.exit(1)