import os
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

load_dotenv(override=True)
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
    """Write a row to audit_logs (never breaks the request if it fails)."""
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO audit_logs (user_id, action) VALUES (%s, %s)",
                (user_id, action),
            )
    except mysql.connector.Error:
        pass


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
        return render_template('studentdashboard.html')


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

        return render_template(
            'teacherdashboard.html',
            teacher_assignments=teacher_assignments,
            lesson_plans=lesson_plans
        )

    @app.route('/add_assignment', methods=['POST'])
    @role_required('Teacher')
    def add_assignment():
        title = (request.form.get('title') or '').strip()
        subject = (request.form.get('subject') or '').strip()
        description = (request.form.get('description') or '').strip()
        due_date = (request.form.get('due_date') or '').strip()

        if not all([title, subject, description, due_date]):
            flash('Please complete all assignment fields.')
            return redirect(url_for('teacherdashboard'))

        try:
            with get_cursor(commit=True) as cur:
                cur.execute(
                    """
                    INSERT INTO assignments
                        (teacher_id, title, subject, description, due_date)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        session['user_id'],
                        title,
                        subject,
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
        subject = (request.form.get('subject') or '').strip()
        title = (request.form.get('title') or '').strip()
        objectives = (request.form.get('objectives') or '').strip()
        content = (request.form.get('content') or '').strip()
        lesson_date = (request.form.get('lesson_date') or '').strip()

        if not all([subject, title, objectives, content, lesson_date]):
            flash('Please complete all lesson plan fields.')
            return redirect(url_for('teacherdashboard'))

        try:
            with get_cursor(commit=True) as cur:
                cur.execute(
                    """
                    INSERT INTO lesson_plans
                        (teacher_id, subject, title, objectives, content, lesson_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session['user_id'],
                        subject,
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
            cur.execute(
                """SELECT a.created_at,
                          COALESCE(CONCAT(u.lastname, ', ', u.firstname), 'Unknown') AS username,
                          a.action
                   FROM audit_logs a
                   LEFT JOIN users u ON u.id = a.user_id
                   ORDER BY a.created_at DESC
                   LIMIT 50"""
            )
            audit_logs = cur.fetchall()

        return render_template(
            'admindashboard.html',
            total_students=total_students,
            total_teachers=total_teachers,
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

        if not (lastname and firstname and email and password) or role not in ('Student', 'Teacher'):
            flash("Please fill in all required fields.")
            return redirect(url_for('admindashboard'))

        try:
            with get_cursor(commit=True) as cur:
                cur.execute(
                    """INSERT INTO users (lastname, firstname, middlename, email, password, role)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (lastname, firstname, middlename, email,
                     generate_password_hash(password), role),
                )
        except mysql.connector.IntegrityError:
            flash("That email is already registered.")
            return redirect(url_for('admindashboard'))

        log_action(session['user_id'], f"Added {role.lower()} account: {email}")
        flash(f"{role} account created for {firstname} {lastname}.")
        return redirect(url_for('admindashboard'))

    return app


app = create_app()


if __name__ == '__main__':
    # NOTE: 3307 is your MySQL port, so Flask runs on 5000 instead.
    app.run(host='127.0.0.1', port=5000, debug=True)