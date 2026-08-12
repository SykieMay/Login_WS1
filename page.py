from flask import Flask, render_template, request, redirect, url_for

def create_app():
    app = Flask(__name__, template_folder='.')

    @app.route('/')
    @app.route('/index')
    @app.route('/index.html')
    def index():
        return render_template('dashboard.html')

    @app.route('/register')
    @app.route('/register.html')
    def register():
        return render_template('index.html')

    @app.route('/logout')
    def logout():
        return render_template('index.html')

    @app.route('/dashboard')
    @app.route('/dashboard.html')
    def dashboard():
        return render_template('index.html')

    @app.route('/login', methods=['POST'])
    def login():
        username = request.form['username']
        password = request.form['password']

        if username and password:  
            return redirect(url_for('index'))
        
        return redirect(url_for('dashboard'))

    return app

def main():
    app = create_app()
    app.run(debug=True)

if __name__ == '__main__':
    main()