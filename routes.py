"""
Flask Routes — all endpoints for the legal intake system.
"""

import os
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, send_from_directory)
from werkzeug.utils import secure_filename
from database import (create_case, get_case, get_all_cases, update_case_ai,
                      save_document, get_case_documents, get_templates)
from ai.logic import (classify_claim, screen_viability,
                      extract_information, populate_template)

# Only these file extensions are accepted on upload
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}


def allowed_file(filename):
    # Check a dot exists AND the extension after the last dot is in the allowed set
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def register_routes(app):
    # All routes are defined inside this function so they attach to whichever
    # app instance is passed in — supports the application factory pattern

    # ─── Dashboard ─────────────────────────────────────────────
    @app.route('/')
    def index():
        cases = get_all_cases()          # Fetch all cases from the database
        return render_template('index.html', cases=cases)

    # ─── Intake Form ────────────────────────────────────────────
    @app.route('/intake', methods=['GET', 'POST'])
    def intake():
        if request.method == 'POST':
            errors = []

            # Server-side validation — required fields must not be blank
            # (browser validation can be bypassed, so this is essential)
            required = ['client_name', 'incident_date', 'incident_type', 'incident_description']
            for field in required:
                if not request.form.get(field, '').strip():
                    errors.append(f"{field.replace('_', ' ').title()} is required.")

            if errors:
                # Re-render the form with error messages and the user's previous input
                for e in errors:
                    flash(e, 'error')
                return render_template('intake.html', form_data=request.form)

            # Collect and strip whitespace from all submitted form fields
            case_data = {
                'client_name': request.form.get('client_name', '').strip(),
                'client_email': request.form.get('client_email', '').strip(),
                'client_phone': request.form.get('client_phone', '').strip(),
                'client_dob': request.form.get('client_dob', '').strip(),
                'incident_date': request.form.get('incident_date', '').strip(),
                'incident_type': request.form.get('incident_type', '').strip(),
                'incident_description': request.form.get('incident_description', '').strip(),
                'incident_location': request.form.get('incident_location', '').strip(),
            }

            # Run AI classification — determines claim type (PI / CN / HD) and confidence
            classification = classify_claim(
                case_data['incident_type'],
                case_data['incident_description']
            )

            # Run viability screening — checks limitation period and completeness
            viability = screen_viability(case_data, classification['claim_type'])

            # Merge AI results into case_data so everything is saved in one DB call
            case_data.update({
                'claim_type': classification['claim_type'],
                'claim_confidence': classification['claim_confidence'],
                'claim_keywords': classification['claim_keywords'],
                'viability_status': viability['viability_status'],
                'viability_explanation': viability['viability_explanation'],
                'limitation_ok': viability['limitation_ok'],
            })

            case_id = create_case(case_data)           # Save to database, get new ID
            flash('Case submitted successfully.', 'success')
            return redirect(url_for('case_detail', case_id=case_id))  # Go to new case page

        # GET request — show blank intake form
        return render_template('intake.html', form_data={})

    # ─── Case Detail ────────────────────────────────────────────
    @app.route('/case/<int:case_id>')
    def case_detail(case_id):
        case = get_case(case_id)
        if not case:
            # Guard against manually typed invalid URLs like /case/9999
            flash('Case not found.', 'error')
            return redirect(url_for('index'))

        documents = get_case_documents(case_id)            # All uploads for this case
        templates = get_templates(case.get('claim_type'))  # Only templates matching claim type
        return render_template('case_detail.html',
                               case=case, documents=documents, templates=templates)

    # ─── Document Upload ─────────────────────────────────────────
    @app.route('/case/<int:case_id>/upload', methods=['POST'])
    def upload_document(case_id):
        case = get_case(case_id)
        if not case:
            flash('Case not found.', 'error')
            return redirect(url_for('index'))

        # Check the form actually included a file field
        if 'document' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('case_detail', case_id=case_id))

        file = request.files['document']

        # Empty filename means the user submitted the form without choosing a file
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('case_detail', case_id=case_id))

        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload a .txt, .pdf, or .doc file.', 'error')
            return redirect(url_for('case_detail', case_id=case_id))

        # secure_filename strips dangerous characters (e.g. path traversal like ../../)
        filename = secure_filename(file.filename)
        # Prefix with case ID so files from different cases never collide
        filename = f"case_{case_id}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Text extraction only works on plain .txt files in this version
        raw_text = ""
        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'txt':
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_text = f.read()
            except Exception:
                raw_text = ""

        # Run NLP extraction if text was found; otherwise store a placeholder message
        extracted = extract_information(raw_text) if raw_text else {
            "raw_text": f"[Binary file: {ext.upper()}. Text extraction not available in demo.]",
            "names": [], "dates": [], "locations": [], "keywords": []
        }

        save_document(case_id, file.filename, file_path, extracted)
        flash('Document uploaded and processed.', 'success')
        return redirect(url_for('case_detail', case_id=case_id))

    # ─── Template Generator ──────────────────────────────────────
    @app.route('/case/<int:case_id>/generate/<int:template_id>')
    def generate_document(case_id, template_id):
        from database import get_db  # Local import avoids circular dependency at module level
        case = get_case(case_id)
        if not case:
            flash('Case not found.', 'error')
            return redirect(url_for('index'))

        # Fetch the requested template directly by ID
        conn = get_db()
        tmpl = conn.execute("SELECT * FROM templates WHERE id=?", (template_id,)).fetchone()
        conn.close()
        if not tmpl:
            flash('Template not found.', 'error')
            return redirect(url_for('case_detail', case_id=case_id))

        # Replace {{PLACEHOLDERS}} in template content with actual case data
        populated = populate_template(tmpl['content'], case)
        return render_template('generated_doc.html',
                               case=case, template=dict(tmpl), content=populated)

    # ─── API: Re-run AI on existing case ────────────────────────
    @app.route('/api/case/<int:case_id>/reanalyse', methods=['POST'])
    def reanalyse_case(case_id):
        case = get_case(case_id)
        if not case:
            return jsonify({'error': 'Not found'}), 404  # JSON response for API callers

        # Re-run both AI steps on the existing case text
        classification = classify_claim(case['incident_type'], case['incident_description'])
        viability = screen_viability(case, classification['claim_type'])

        # Update only the AI columns — client and incident data stays unchanged
        update_case_ai(case_id, {
            'claim_type': classification['claim_type'],
            'claim_confidence': classification['claim_confidence'],
            'claim_keywords': classification['claim_keywords'],
            'viability_status': viability['viability_status'],
            'viability_explanation': viability['viability_explanation'],
            'limitation_ok': viability['limitation_ok'],
        })
        flash('Case re-analysed successfully.', 'success')
        return redirect(url_for('case_detail', case_id=case_id))

    # ─── Templates list ──────────────────────────────────────────
    @app.route('/templates')
    def templates_list():
        all_templates = get_templates()  # No filter — fetch all templates
        return render_template('templates.html', templates=all_templates)