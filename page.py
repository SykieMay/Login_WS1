from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", "3306")),
        ssl_ca="/etc/secrets/ca.pem"
    )

def create_app():
    app = Flask(__name__, template_folder='.')
    app.secret_key = "your-secret-key"

    @app.route('/')
    @app.route('/index')
    @app.route('/index.html')
    def index():
        return render_template('index.html')

    @app.route('/login', methods=['POST', 'GET'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            db_connection = get_db_connection()
            cursor = db_connection.cursor(dictionary=True)

            query = "SELECT * FROM users WHERE email = %s AND password = %s"
            cursor.execute(query, (email, password))

            user = cursor.fetchone()  

            cursor.close()
            db_connection.close()

            if user:
                session['user_id'] = user['id'] # type: ignore
                session['lastname'] = user['lastname'] # type: ignore
                session['firstname'] = user['firstname'] # type: ignore
                session['middlename'] = user['middlename'] # type: ignore
                session['role'] = user['role'] # type: ignore

                if user['role'] == 'Student': # type: ignore
                    return redirect(url_for('studentdashboard'))

                elif user['role'] == 'Teacher': # type: ignore
                    return redirect(url_for('teacherdashboard'))

                elif user['role'] == 'Admin': # type: ignore
                    return redirect(url_for('admindashboard'))

                return redirect(url_for('index'))
            return "Invalid Pass or username"
        
        return render_template('index.html') 

    @app.route('/register', methods=['POST', 'GET'])
    @app.route('/register.html', methods=['POST', 'GET'])
    def register():
        if request.method == 'POST':
            lastname = request.form.get('lastname')
            firstname = request.form.get('firstname')
            middlename = request.form.get('middlename')
            email = request.form.get('email')
            password = request.form.get('password')

            if lastname and firstname and middlename and email and password:
                db_connection = get_db_connection()
                cursor = db_connection.cursor()

                query = """INSERT INTO users (lastname, firstname, middlename, email, password, role) VALUES (%s, %s, %s, %s, %s, %s)"""
                cursor.execute(query, (lastname, firstname, middlename, email, password, 'Student'))

                db_connection.commit()
                cursor.close()
                db_connection.close()

                return redirect(url_for('index'))

            return "Please fill in all fields."

        return render_template('register.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

    @app.route('/studentdashboard')
    @app.route('/studentdashboard.html')
    def studentdashboard():
        if 'user_id' not in session:
            return redirect(url_for('index'))

        if session.get('role') != 'Student':
            return redirect(url_for('index'))

        return render_template(
            'studentdashboard.html', 
            lastname = session.get('lastname'), 
            firstname = session.get('firstname'), 
            middlename = session.get('middlename'), 
            role = session.get('role')
        )

    @app.route('/teacherdashboard')
    @app.route('/teacherdashboard.html')
    def teacherdashboard():
        if 'user_id' not in session:
            return redirect(url_for('index'))

        if session.get('role') != 'Teacher':
            return redirect(url_for('index'))

        return render_template(
            'teacherdashboard.html', 
            lastname = session.get('lastname'), 
            firstname = session.get('firstname'), 
            middlename = session.get('middlename'), 
            role = session.get('role')
        )

    @app.route('/admindashboard')
    @app.route('/admindashboard.html')
    def admindashboard():
        if 'user_id' not in session:
            return redirect(url_for('index'))

        if session.get('role') != 'Admin':
            return redirect(url_for('index'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total_students FROM users WHERE role = %s", ('Student',))
        total_students = cursor.fetchone()['total_students'] # type: ignore

        cursor.execute("SELECT COUNT(*) AS total_teachers FROM users WHERE role = %s", ('Teacher',))
        total_teachers = cursor.fetchone()['total_teachers'] # type: ignore

        cursor.close()
        conn.close()

        return render_template(
            'admindashboard.html',
            lastname = session.get('lastname'), 
            firstname = session.get('firstname'), 
            middlename = session.get('middlename'), 
            role = session.get('role'),
            users={'students': {'total': 0}},
            total_students = total_students,
            total_teachers = total_teachers
        )

    @app.route('/adduser', methods=['POST'])
    def add_user():
        if request.method == 'POST':
            lastname = request.form.get('lastname')
            firstname = request.form.get('firstname')
            middlename = request.form.get('middlename')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')

            if lastname and firstname and middlename and email and password and role:
                db_connection = get_db_connection()
                cursor = db_connection.cursor()

                query = """INSERT INTO users (lastname, firstname, middlename, email, password, role) VALUES (%s, %s, %s, %s, %s, %s)"""
                cursor.execute(query, (lastname, firstname, middlename, email, password, role))

                db_connection.commit()
                cursor.close()
                db_connection.close()

                return redirect(url_for('admindashboard'))

            return "Please fill in all fields."

        return render_template('admindashboard.html')      

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)

 