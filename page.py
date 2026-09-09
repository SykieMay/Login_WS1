from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",        # Or your server IP
        user="root",    # Your MySQL username
        password="",# Your MySQL password
        database="user_account", # The database name
        port=3307
    )

def create_app():
    app = Flask(__name__, template_folder='.')
    app.secret_key = "your-secret-key"

    @app.route('/')
    @app.route('/index')
    @app.route('/index.html')
    def index():
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
                cursor.execute(query, (lastname, firstname, middlename, email, password, 'student'))

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

        if session.get('role') != 'student':
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

        if session.get('role') != 'teacher':
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

        return render_template(
            'admindashboard.html',
            lastname = session.get('lastname'), 
            firstname = session.get('firstname'), 
            middlename = session.get('middlename'), 
            role = session.get('role'),
            users={'students': {'total': 0}}
        )

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
                session['user_id'] = user['id']
                session['lastname'] = user['lastname']
                session['firstname'] = user['firstname']
                session['middlename'] = user['middlename']
                session['role'] = user['role']

            if user['role'] == 'student':
                return redirect(url_for('studentdashboard'))

            elif user['role'] == 'teacher':
                return redirect(url_for('teacherdashboard'))

            elif user['role'] == 'Admin':
                return redirect(url_for('admindashboard'))

            return redirect(url_for('index'))
        
        return render_template('index.html') 

    return app


def main():
    app = create_app()
    app.run(debug=True)

if __name__ == '__main__':
    main()

 