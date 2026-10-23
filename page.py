import os
from datetime import date
from dotenv import load_dotenv

from contextlib import contextmanager
from functools import wraps

import mysql.connector
from flask import (Flask, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

HASH_PREFIXES = ("pbkdf2:", "scrypt:")


# ----------------------------------------------------------------
# Database
# ----------------------------------------------------------------

load_dotenv()
def get_db_connection():
    ssl_ca = os.getenv(
        "DB_SSL_CA",
        os.path.join(os.path.dirname(__file__), "ca.pem")
    )

    if not os.path.isfile(ssl_ca):
        raise FileNotFoundError(
            f"TiDB SSL certificate not found: {ssl_ca}"
        )

    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.getenv("DB_NAME", "brightstonelms_db"),
        port=int(os.getenv("DB_PORT", "4000")),
        ssl_ca=ssl_ca,
        ssl_verify_cert=True,
        ssl_verify_identity=True,
        use_pure=True,
    )




@contextmanager
def get_cursor(commit=False):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            conn.commit()
    finally:
        cursor.close()
        conn.close()



def log_action(user_id, action):
    """Write an audit log and report database failures in Render logs."""
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO audit_logs (user_id, action, created_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                """,
                (user_id, action),
            )
    except Exception:
        app.logger.exception("Failed to insert audit log: %s", action)



def verify_password(stored, supplied):
    """Check a password. Old plain-text rows still work (and get upgraded)."""
    if stored.startswith(HASH_PREFIXES):
        return check_password_hash(stored, supplied)
    return stored == supplied


# ----------------------------------------------------------------
# App
# ----------------------------------------------------------------
def create_app():
    app = Flask(__name__, template_folder='.')
    app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

    # ---- "Welcome, <name>" support --------------------------------
    # Makes `user` available in EVERY template:
    #   {{ user.firstname }}  {{ user.lastname }}  {{ user.role }}
    @app.context_processor
    def inject_user():
        if 'user_id' not in session:
            return {'user': None}
        return {'user': {
            'id': session.get('user_id'),
            'firstname': session.get('firstname'),
            'lastname': session.get('lastname'),
            'middlename': session.get('middlename'),
            'role': session.get('role'),
        }}

    def role_required(role):
        def decorator(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                if 'user_id' not in session:
                    return redirect(url_for('index'))
                if session.get('role') != role:
                    return redirect(url_for('index'))
                return view(*args, **kwargs)
            return wrapped
        return decorator

    # ---- Public pages -----------------------------------------------
    @app.route('/')
    @app.route('/index')
    @app.route('/index.html')
    def index():
        return render_template('index.html')

    @app.route('/login', methods=['POST', 'GET'])
    def login():
        if request.method == 'GET':
            return render_template('index.html')

        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''

        with get_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            found = cur.fetchone()

        if not found or not verify_password(found['password'], password):  # type: ignore
            flash("Invalid email or password.")
            return redirect(url_for('index'))

        if not found.get('is_active', 1):  # type: ignore
            flash("This account has been disabled. Please contact the administrator.")
            return redirect(url_for('index'))

        # upgrade legacy plain-text password to a hash
        if not found['password'].startswith(HASH_PREFIXES):  # type: ignore
            with get_cursor(commit=True) as cur:
                cur.execute("UPDATE users SET password = %s WHERE id = %s",
                            (generate_password_hash(password), found['id']))  # type: ignore

        session.clear()
        session['user_id'] = found['id']  # type: ignore
        session['lastname'] = found['lastname']  # type: ignore
        session['firstname'] = found['firstname']  # type: ignore
        session['middlename'] = found['middlename'] or ''  # type: ignore
        session['role'] = found['role']  # type: ignore
        log_action(found['id'], "Logged in")  # type: ignore

        destination = {
            'Student': 'studentdashboard',
            'Teacher': 'teacherdashboard',
            'Admin': 'admindashboard',
        }.get(found['role'], 'index')  # type: ignore
        return redirect(url_for(destination))

    @app.route('/register', methods=['POST', 'GET'])
    @app.route('/register.html', methods=['POST', 'GET'])
    def register():
        if request.method == 'GET':
            return render_template('register.html')

        lastname = (request.form.get('lastname') or '').strip()
        firstname = (request.form.get('firstname') or '').strip()
        middlename = (request.form.get('middlename') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm_password') or ''

        if not (lastname and firstname and email and password):
            flash("Please fill in all required fields.")
            return redirect(url_for('register'))
        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return redirect(url_for('register'))
        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for('register'))

        try:
            with get_cursor(commit=True) as cur:
                cur.execute(
                    """INSERT INTO users (lastname, firstname, middlename, email, password, role)
                       VALUES (%s, %s, %s, %s, %s, 'Student')""",
                    (lastname, firstname, middlename, email,
                     generate_password_hash(password)),
                )
                new_id = cur.lastrowid
        except mysql.connector.IntegrityError:
            flash("That email is already registered.")
            return redirect(url_for('register'))

        log_action(new_id, "Registered a new student account")
        flash("Account created! You can log in now.")
        return redirect(url_for('index'))

    @app.route('/logout')
    def logout():
        log_action(session.get('user_id'), "Logged out")
        session.clear()
        return redirect(url_for('index'))

    # ---- Dashboards -------------------------------------------------
    @app.route('/studentdashboard')
    @app.route('/studentdashboard.html')
    @role_required('Student')
    def studentdashboard():
        student_id = session['user_id']
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.name
                FROM users AS u
                LEFT JOIN programs AS p ON p.id = u.program_id
                WHERE u.id = %s
                """,
                (student_id,),
            )
            student_program = cur.fetchone()
            cur.execute(
                """
                SELECT s.name AS subject, t.firstname, t.lastname
                FROM users AS u
                JOIN program_subjects AS s ON s.program_id = u.program_id
                LEFT JOIN users AS t ON t.id = s.teacher_id
                WHERE u.id = %s
                ORDER BY s.name
                """,
                (student_id,),
            )
            student_subjects = cur.fetchall()
            cur.execute(
                """
                SELECT a.attendance_date AS date, s.name AS subject, a.status
                FROM teacher_attendance AS a
                JOIN program_subjects AS s ON s.id = a.subject_id
                WHERE a.student_id = %s
                ORDER BY a.attendance_date DESC
                LIMIT 100
                """,
                (student_id,),
            )
            student_attendance = cur.fetchall()
            cur.execute(
                """
                SELECT g.grade, g.assessment, s.name AS subject
                FROM teacher_gradebook AS g
                JOIN program_subjects AS s ON s.id = g.subject_id
                WHERE g.student_id = %s
                ORDER BY g.updated_at DESC
                LIMIT 100
                """,
                (student_id,),
            )
            student_grades = cur.fetchall()

            cur.execute(
                "SELECT AVG(grade) AS average_grade FROM teacher_gradebook WHERE student_id = %s",
                (student_id,),
            )
            average_grade = cur.fetchone()['average_grade']

            cur.execute(
                """
                SELECT
                    SUM(CASE WHEN status IN ('Present', 'Late') THEN 1 ELSE 0 END) AS attended,
                    SUM(CASE WHEN status IN ('Present', 'Late', 'Absent') THEN 1 ELSE 0 END) AS eligible
                FROM teacher_attendance
                WHERE student_id = %s
                """,
                (student_id,),
            )
            attendance_summary = cur.fetchone()
            eligible_attendance = attendance_summary['eligible'] or 0
            attendance_rate = (
                round(attendance_summary['attended'] * 100 / eligible_attendance, 1)
                if eligible_attendance else None
            )

            cur.execute(
                """
                SELECT lp.id, lp.title, s.name AS subject,
                       CONCAT_WS(' ', NULLIF(lp.objectives, ''), NULLIF(lp.content, '')) AS description,
                       lp.lesson_date
                FROM lesson_plans AS lp
                JOIN program_subjects AS s ON s.id = lp.subject_id
                WHERE s.program_id = (
                    SELECT program_id FROM users WHERE id = %s
                )
                ORDER BY lp.lesson_date DESC, lp.id DESC
                LIMIT 100
                """,
                (student_id,),
            )
            learning_materials = cur.fetchall()

            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM lesson_plans AS lp
                JOIN program_subjects AS s ON s.id = lp.subject_id
                WHERE s.program_id = (SELECT program_id FROM users WHERE id = %s)
                """,
                (student_id,),
            )
            new_materials = cur.fetchone()['n']
        return render_template(
            'studentdashboard.html',
            student_program=student_program,
            student_subjects=student_subjects,
            student_attendance=student_attendance,
            student_grades=student_grades,
            my_subject_count=len(student_subjects),
            average_grade=round(float(average_grade), 1) if average_grade is not None else None,
            attendance_rate=attendance_rate,
            learning_materials=learning_materials,
            new_materials=new_materials,
        )


    @app.route('/teacherdashboard')
    @app.route('/teacherdashboard.html')
    @role_required('Teacher')
    def teacherdashboard():
        teacher_id = session['user_id']

        with get_cursor() as cur:
            cur.execute(
                """
                SELECT id, title, subject, due_date, status
                FROM assignments
                WHERE teacher_id = %s
                ORDER BY due_date ASC
                """,
                (teacher_id,)
            )
            teacher_assignments = cur.fetchall()

            cur.execute(
                """
                SELECT id, subject, title, objectives, content, lesson_date
                FROM lesson_plans
                WHERE teacher_id = %s
                ORDER BY lesson_date DESC
                """,
                (teacher_id,)
            )
            lesson_plans = cur.fetchall()

            cur.execute(
                """
                SELECT s.id, s.name, s.program_id, p.name AS program_name
                FROM program_subjects AS s
                JOIN programs AS p ON p.id = s.program_id
                WHERE s.teacher_id = %s
                ORDER BY p.name, s.name
                """,
                (teacher_id,),
            )
            teacher_subjects = cur.fetchall()

            cur.execute(
                """
                SELECT DISTINCT u.id, u.firstname, u.lastname, p.name AS program_name
                FROM users AS u
                JOIN program_subjects AS s ON s.program_id = u.program_id
                JOIN programs AS p ON p.id = u.program_id
                WHERE u.role = 'Student' AND s.teacher_id = %s
                ORDER BY u.lastname, u.firstname
                """,
                (teacher_id,),
            )
            teacher_students = cur.fetchall()

            cur.execute(
                """
                SELECT a.id, a.student_id, a.subject_id, a.attendance_date AS date,
                       a.status, u.firstname, u.lastname, s.name AS subject
                FROM teacher_attendance AS a
                JOIN users AS u ON u.id = a.student_id
                JOIN program_subjects AS s ON s.id = a.subject_id
                WHERE a.teacher_id = %s
                ORDER BY a.attendance_date DESC, u.lastname, u.firstname
                LIMIT 100
                """,
                (teacher_id,),
            )
            attendance_records = cur.fetchall()

            cur.execute(
                """
                SELECT g.id, g.grade, g.assessment, u.firstname, u.lastname,
                       s.name AS subject, g.updated_at
                FROM teacher_gradebook AS g
                JOIN users AS u ON u.id = g.student_id
                JOIN program_subjects AS s ON s.id = g.subject_id
                WHERE g.teacher_id = %s
                ORDER BY g.updated_at DESC, u.lastname, u.firstname
                LIMIT 100
                """,
                (teacher_id,),
            )
            gradebook = cur.fetchall()

            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM teacher_attendance
                WHERE teacher_id = %s AND attendance_date = CURRENT_DATE()
                """,
                (teacher_id,),
            )
            attendance_today = cur.fetchone()['n']

            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM teacher_attendance
                WHERE teacher_id = %s AND attendance_date = CURRENT_DATE() AND status = 'Absent'
                """,
                (teacher_id,),
            )
            absent_today = cur.fetchone()['n']

            cur.execute(
                "SELECT COUNT(*) AS n FROM teacher_gradebook WHERE teacher_id = %s",
                (teacher_id,),
            )
            grades_recorded = cur.fetchone()['n']

        return render_template(
            'teacherdashboard.html',
            teacher_assignments=teacher_assignments,
            lesson_plans=lesson_plans,
            teacher_subjects=teacher_subjects,
            teacher_students=teacher_students,
            attendance_records=attendance_records,
            gradebook=gradebook,
            total_students=len(teacher_students),
            assigned_subjects=len(teacher_subjects),
            attendance_today=attendance_today,
            absent_today=absent_today,
            grades_recorded=grades_recorded,
            today_date=date.today().isoformat(),
        )

    @app.route('/record_attendance', methods=['POST'])
    @role_required('Teacher')
    def record_attendance():
        subject_id = request.form.get('subject_id', type=int)
        student_id = request.form.get('student_id', type=int)
        attendance_date = (request.form.get('attendance_date') or '').strip()
        status = request.form.get('status')
        if not all([subject_id, student_id, attendance_date]) or status not in ('Present', 'Absent', 'Late', 'Excused'):
            flash('Complete all attendance fields with a valid status.')
            return redirect(url_for('teacherdashboard'))
        try:
            with get_cursor(commit=True) as cur:
                cur.execute(
                    """
                    SELECT s.name
                    FROM program_subjects AS s
                    JOIN users AS u ON u.program_id = s.program_id AND u.role = 'Student'
                    WHERE s.id = %s AND s.teacher_id = %s AND u.id = %s
                    """,
                    (subject_id, session['user_id'], student_id),
                )
                if not cur.fetchone():
                    flash('Choose a student and subject assigned to your program.')
                    return redirect(url_for('teacherdashboard'))
                cur.execute(
                    """
                    INSERT INTO teacher_attendance
                        (teacher_id, student_id, subject_id, attendance_date, status)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        teacher_id = VALUES(teacher_id),
                        status = VALUES(status)
                    """,
                    (session['user_id'], student_id, subject_id, attendance_date, status),
                )
            log_action(session['user_id'], f'Recorded {status.lower()} attendance for student {student_id}')
            flash('Attendance saved.')
        except mysql.connector.Error:
            app.logger.exception('Failed to save attendance.')
            flash('Unable to save attendance. Check that the dashboard migration has been applied.')
        return redirect(url_for('teacherdashboard'))

    @app.route('/save_grade', methods=['POST'])
    @role_required('Teacher')
    def save_grade():
        subject_id = request.form.get('subject_id', type=int)
        student_id = request.form.get('student_id', type=int)
        assessment = (request.form.get('assessment') or '').strip()
        grade = request.form.get('grade', type=float)
        if (not all([subject_id, student_id, assessment]) or len(assessment) > 120
                or grade is None or not 0 <= grade <= 100):
            flash('Enter a student, subject, assessment, and grade from 0 to 100.')
            return redirect(url_for('teacherdashboard'))
        try:
            with get_cursor(commit=True) as cur:
                cur.execute(
                    """
                    SELECT s.name
                    FROM program_subjects AS s
                    JOIN users AS u ON u.program_id = s.program_id AND u.role = 'Student'
                    WHERE s.id = %s AND s.teacher_id = %s AND u.id = %s
                    """,
                    (subject_id, session['user_id'], student_id),
                )
                if not cur.fetchone():
                    flash('Choose a student and subject assigned to your program.')
                    return redirect(url_for('teacherdashboard'))
                cur.execute(
                    """
                    INSERT INTO teacher_gradebook
                        (teacher_id, student_id, subject_id, assessment, grade)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE grade = VALUES(grade), updated_at = CURRENT_TIMESTAMP
                    """,
                    (session['user_id'], student_id, subject_id, assessment, grade),
                )
            log_action(session['user_id'], f'Saved grade for student {student_id}: {assessment}')
            flash('Grade saved.')
        except mysql.connector.Error:
            app.logger.exception('Failed to save grade.')
            flash('Unable to save the grade. Check that the dashboard migration has been applied.')
        return redirect(url_for('teacherdashboard'))

    @app.route('/add_assignment', methods=['POST'])
    @role_required('Teacher')
    def add_assignment():
        title = (request.form.get('title') or '').strip()
        subject_id = request.form.get('subject_id', type=int)
        description = (request.form.get('description') or '').strip()
        due_date = (request.form.get('due_date') or '').strip()

        if not all([title, subject_id, description, due_date]):
            flash('Please complete all assignment fields.')
            return redirect(url_for('teacherdashboard'))

        try:
            with get_cursor(commit=True) as cur:
                cur.execute(
                    "SELECT name FROM program_subjects WHERE id = %s AND teacher_id = %s",
                    (subject_id, session['user_id']),
                )
                subject_row = cur.fetchone()
                if not subject_row:
                    flash('Choose a subject assigned to your account.')
                    return redirect(url_for('teacherdashboard'))
                subject = subject_row['name']
                cur.execute(
                    """
                    INSERT INTO assignments
                        (teacher_id, title, subject, subject_id, description, due_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session['user_id'],
                        title,
                        subject,
                        subject_id,
                        description,
                        due_date
                    )
                )

            log_action(
                session['user_id'],
                f'Created assignment: {title}'
            )
            flash('Assignment added successfully.')

        except mysql.connector.Error:
            app.logger.exception('Failed to save assignment.')
            flash('Unable to save the assignment. Check the database tables.')

        return redirect(url_for('teacherdashboard'))


    @app.route('/add_lesson_plan', methods=['POST'])
    @role_required('Teacher')
    def add_lesson_plan():
        subject_id = request.form.get('subject_id', type=int)
        title = (request.form.get('title') or '').strip()
        objectives = (request.form.get('objectives') or '').strip()
        content = (request.form.get('content') or '').strip()
        lesson_date = (request.form.get('lesson_date') or '').strip()

        if not all([subject_id, title, objectives, content, lesson_date]):
            flash('Please complete all lesson plan fields.')
            return redirect(url_for('teacherdashboard'))

        try:
            with get_cursor(commit=True) as cur:
                cur.execute(
                    "SELECT name FROM program_subjects WHERE id = %s AND teacher_id = %s",
                    (subject_id, session['user_id']),
                )
                subject_row = cur.fetchone()
                if not subject_row:
                    flash('Choose a subject assigned to your account.')
                    return redirect(url_for('teacherdashboard'))
                subject = subject_row['name']
                cur.execute(
                    """
                    INSERT INTO lesson_plans
                        (teacher_id, subject, subject_id, title, objectives, content, lesson_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session['user_id'],
                        subject,
                        subject_id,
                        title,
                        objectives,
                        content,
                        lesson_date
                    )
                )

            log_action(
                session['user_id'],
                f'Created lesson plan: {title}'
            )
            flash('Lesson plan added successfully.')

        except mysql.connector.Error:
            app.logger.exception('Failed to save lesson plan.')
            flash('Unable to save the lesson plan. Check the database tables.')

        return redirect(url_for('teacherdashboard'))



    @app.route('/admindashboard')
    @app.route('/admindashboard.html')
    @role_required('Admin')
    def admindashboard():
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'Student'")
            total_students = cur.fetchone()['n']  # type: ignore
            cur.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'Teacher'")
            total_teachers = cur.fetchone()['n']  # type: ignore
            cur.execute("SELECT COUNT(*) AS n FROM program_subjects")
            total_courses = cur.fetchone()['n']  # type: ignore
            cur.execute(
                """
                SELECT
                    a.id,
                    a.created_at,
                    COALESCE(
                        CONCAT(u.lastname, ', ', u.firstname),
                        'Unknown'
                    ) AS username,
                    a.action
                FROM audit_logs AS a
                LEFT JOIN users AS u ON u.id = a.user_id
                ORDER BY a.created_at DESC, a.id DESC
                LIMIT 50
                """
            )
            audit_logs = cur.fetchall()

            cur.execute(
                """
                SELECT u.id, u.lastname, u.firstname, u.middlename, u.email,
                       u.role, u.is_active, u.program_id, p.name AS program_name
                FROM users AS u
                LEFT JOIN programs AS p ON p.id = u.program_id
                ORDER BY u.lastname, u.firstname
                """
            )
            users = cur.fetchall()

            cur.execute("SELECT id, name FROM programs ORDER BY name")
            programs = cur.fetchall()

            cur.execute(
                """
                SELECT u.id, u.firstname, u.lastname, u.program_id,
                       p.name AS program_name
                FROM users AS u
                LEFT JOIN programs AS p ON p.id = u.program_id
                WHERE u.role = 'Teacher' AND u.is_active = 1
                ORDER BY u.lastname, u.firstname
                """
            )
            teachers = cur.fetchall()

            cur.execute(
                """
                SELECT s.id, s.name, s.program_id, s.teacher_id,
                       p.name AS program_name,
                       CONCAT(t.lastname, ', ', t.firstname) AS teacher_name
                FROM program_subjects AS s
                JOIN programs AS p ON p.id = s.program_id
                LEFT JOIN users AS t ON t.id = s.teacher_id
                ORDER BY p.name, s.name
                """
            )
            subjects = cur.fetchall()

        return render_template(
            'admindashboard.html',
            total_students=total_students,
            total_teachers=total_teachers,
            total_courses=total_courses,
            users=users,
            programs=programs,
            teachers=teachers,
            subjects=subjects,
            audit_logs=audit_logs,
        )

    @app.route('/adduser', methods=['POST'])
    @role_required('Admin')          # only a logged-in Admin may create users
    def add_user():
        lastname = (request.form.get('lastname') or '').strip()
        firstname = (request.form.get('firstname') or '').strip()
        middlename = (request.form.get('middlename') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        role = request.form.get('role')
        program_id = request.form.get('program_id', type=int)

        if not (lastname and firstname and email and password) or role not in ('Student', 'Teacher'):
            flash("Please fill in all required fields.")
            return redirect(url_for('admindashboard'))
        if not program_id:
            flash("Choose a program for the user.")
            return redirect(url_for('admindashboard'))

        try:
            with get_cursor(commit=True) as cur:
                cur.execute("SELECT id FROM programs WHERE id = %s", (program_id,))
                if not cur.fetchone():
                    flash("Choose a valid program.")
                    return redirect(url_for('admindashboard'))
                cur.execute(
                    """INSERT INTO users
                           (lastname, firstname, middlename, email, password, role, program_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (lastname, firstname, middlename, email,
                     generate_password_hash(password), role,
                     program_id),
                )
        except mysql.connector.IntegrityError:
            flash("That email is already registered.")
            return redirect(url_for('admindashboard'))

        log_action(session['user_id'], f"Added {role.lower()} account: {email}")
        flash(f"{role} account created for {firstname} {lastname}.")
        return redirect(url_for('admindashboard'))

    @app.route('/add_program', methods=['POST'])
    @role_required('Admin')
    def add_program():
        name = (request.form.get('name') or '').strip()
        if not name:
            flash('Enter a program name.')
            return redirect(url_for('admindashboard'))
        try:
            with get_cursor(commit=True) as cur:
                cur.execute("INSERT INTO programs (name) VALUES (%s)", (name,))
        except mysql.connector.IntegrityError:
            flash('That program already exists.')
            return redirect(url_for('admindashboard'))
        log_action(session['user_id'], f'Added program: {name}')
        flash(f'Program added: {name}.')
        return redirect(url_for('admindashboard'))

    @app.route('/add_subject', methods=['POST'])
    @role_required('Admin')
    def add_subject():
        name = (request.form.get('name') or '').strip()
        program_id = request.form.get('program_id', type=int)
        teacher_id = request.form.get('teacher_id', type=int)
        if not all([name, program_id, teacher_id]):
            flash('Choose a program and teacher, and enter a subject name.')
            return redirect(url_for('admindashboard'))
        try:
            with get_cursor(commit=True) as cur:
                cur.execute("SELECT id FROM programs WHERE id = %s", (program_id,))
                if not cur.fetchone():
                    flash('Choose a valid program.')
                    return redirect(url_for('admindashboard'))
                cur.execute(
                    """
                    SELECT id FROM users
                    WHERE id = %s AND role = 'Teacher' AND is_active = 1
                      AND program_id = %s
                    """,
                    (teacher_id, program_id),
                )
                if not cur.fetchone():
                    flash('Choose an active teacher assigned to the selected program.')
                    return redirect(url_for('admindashboard'))
                cur.execute(
                    "INSERT INTO program_subjects (name, program_id, teacher_id) VALUES (%s, %s, %s)",
                    (name, program_id, teacher_id),
                )
        except mysql.connector.IntegrityError:
            flash('That subject already exists in the selected program.')
            return redirect(url_for('admindashboard'))
        log_action(session['user_id'], f'Added subject: {name}')
        flash(f'Subject added: {name}.')
        return redirect(url_for('admindashboard'))

    @app.route('/assign_program/<int:user_id>', methods=['POST'])
    @role_required('Admin')
    def assign_program(user_id):
        program_id = request.form.get('program_id', type=int)
        with get_cursor(commit=True) as cur:
            cur.execute(
                "SELECT id, role, program_id FROM users WHERE id = %s AND role IN ('Student', 'Teacher')",
                (user_id,),
            )
            account = cur.fetchone()
            if not account:
                flash('Only student and teacher accounts can be assigned to a program.')
                return redirect(url_for('admindashboard'))
            if program_id:
                cur.execute("SELECT id FROM programs WHERE id = %s", (program_id,))
                if not cur.fetchone():
                    flash('Choose a valid program.')
                    return redirect(url_for('admindashboard'))
            if account['role'] == 'Teacher' and account['program_id'] != program_id:
                cur.execute(
                    "SELECT COUNT(*) AS n FROM program_subjects WHERE teacher_id = %s",
                    (user_id,),
                )
                if cur.fetchone()['n']:
                    flash('Reassign this teacher’s subjects before changing their program.')
                    return redirect(url_for('admindashboard'))
            cur.execute(
                "UPDATE users SET program_id = %s WHERE id = %s",
                (program_id, user_id),
            )
        log_action(session['user_id'], f"Changed program for {account['role'].lower()} account {user_id}")
        flash('User program updated.')
        return redirect(url_for('admindashboard'))

    @app.route('/assign_subject_teacher/<int:subject_id>', methods=['POST'])
    @role_required('Admin')
    def assign_subject_teacher(subject_id):
        teacher_id = request.form.get('teacher_id', type=int)
        with get_cursor(commit=True) as cur:
            cur.execute(
                """
                SELECT id, program_id FROM users
                WHERE id = %s AND role = 'Teacher' AND is_active = 1
                """,
                (teacher_id,),
            )
            teacher = cur.fetchone()
            if not teacher:
                flash('Choose an active teacher account.')
                return redirect(url_for('admindashboard'))
            cur.execute("SELECT id, program_id FROM program_subjects WHERE id = %s", (subject_id,))
            subject = cur.fetchone()
            if not subject:
                flash('Subject not found.')
                return redirect(url_for('admindashboard'))
            if teacher['program_id'] != subject['program_id']:
                flash('Assign the teacher to the same program as this subject first.')
                return redirect(url_for('admindashboard'))
            cur.execute(
                "UPDATE program_subjects SET teacher_id = %s WHERE id = %s",
                (teacher_id, subject_id),
            )
        log_action(session['user_id'], f'Assigned teacher to subject {subject_id}')
        flash('Subject teacher updated.')
        return redirect(url_for('admindashboard'))

    @app.route('/toggleuser/<int:user_id>', methods=['POST'])
    @role_required('Admin')
    def toggle_user(user_id):
        if user_id == session['user_id']:
            flash("You can't disable your own account.")
            return redirect(url_for('admindashboard'))

        with get_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE users SET is_active = 1 - is_active WHERE id = %s",
                (user_id,),
            )
            cur.execute(
                "SELECT email, is_active FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()

        if row:
            state = 'Enabled' if row['is_active'] else 'Disabled'  # type: ignore
            log_action(session['user_id'], f"{state} account: {row['email']}")  # type: ignore
        return redirect(url_for('admindashboard'))

    return app


app = create_app()


if __name__ == '__main__':
    # NOTE: 3307 is your MySQL port, so Flask runs on 5000 instead.
    app.run(host='127.0.0.1', port=5000, debug=True)
