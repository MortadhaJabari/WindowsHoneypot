import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, session, g
from datetime import datetime, timedelta
from core.logger import Logger

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management (not secure, but fine for honeypot)
logger = Logger()

DB_PATH = os.path.join(os.path.dirname(__file__), 'pms.db')

@app.before_request
def before_request():
    g.start_time = datetime.now()
    logger.info(f"WEB request: {request.method} {request.path} from {request.remote_addr}", service="web")

@app.after_request
def after_request(response):
    duration = (datetime.now() - g.start_time).total_seconds()
    logger.info(f"WEB response: {request.method} {request.path} status {response.status_code} ({duration:.3f}s)", service="web")
    return response

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        ip = request.remote_addr
        logger.info(f"WEB login attempt from {ip}: username='{username}' password='{password}'", service="web")
        # VULNERABLE: Directly interpolating user input into SQL (SQL injection possible!)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        c.execute(query)
        user = c.fetchone()
        conn.close()
        if user:
            logger.info(f"WEB login success for '{username}' from {ip}", service="web")
            session['user'] = username
            return redirect(url_for('dashboard'))
        logger.warning(f"WEB login failed for '{username}' from {ip}", service="web")
        error = 'Invalid credentials.'
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM production")
    data = c.fetchall()
    conn.close()
    return render_template('dashboard.html', data=data)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PMS_WEB_PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
