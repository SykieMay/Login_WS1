from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

db_connection = mysql.connector.connect(
    host="127.0.0.1",        # Or your server IP
    user="root",    # Your MySQL username
    password="",# Your MySQL password
    database="user_account", # The database name
    port=3307
)

def create_app():
    app = Flask(__name__, template_folder='.')

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
            middleinitial = request.form.get('middleinitial')
            email = request.form.get('email')
            password = request.form.get('password')

            if lastname and firstname and middleinitial and email and password:
                cursor = db_connection.cursor()

                query = """INSERT INTO users (lastname, firstname, middleinitial, email, password, role) VALUES (%s, %s, %s, %s, %s, %s)"""
                cursor.execute(query, (lastname, firstname, middleinitial, email, password, 'student'))

                db_connection.commit()
                cursor.close()

                return redirect(url_for('index'))

            return "Please fill in all fields."

        return render_template('register.html')

    @app.route('/logout')
    def logout():
        return render_template('index.html')

    @app.route('/dashboard')
    @app.route('/dashboard.html')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/login', methods=['POST', 'GET'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            cursor = db_connection.cursor(dictionary=True)

            query = "SELECT * FROM users WHERE email = %s AND password = %s"
            cursor.execute(query, (email, password))
            user = cursor.fetchone()  
            cursor.close()

            if user:  
                return redirect(url_for('dashboard'))
            
            return "Invalid email or password."
        
        return render_template(url_for('index'))

    return app


def main():
    app = create_app()
    app.run(debug=True)

if __name__ == '__main__':
    main()