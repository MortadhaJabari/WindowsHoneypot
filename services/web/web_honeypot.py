"""
Web Honeypot Service
--------------------
This Flask app simulates a vulnerable web application for honeypot purposes.
It supports blocking/unblocking access via a global flag, and logs all activity.
"""
import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, session, g
from datetime import datetime, timedelta
from core.logger import Logger
import json
import threading
import requests
from flask import make_response

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management (not secure, but fine for honeypot)
logger = Logger()

DB_PATH = os.path.join(os.path.dirname(__file__), 'pms.db')
web_server_thread = None
web_should_run = False
web_blocked = False  # If True, all requests return 503 Service Unavailable

# Set the block flag to control access to the web honeypot
def set_web_blocked(blocked: bool):
    """Block or unblock all web honeypot endpoints."""
    global web_blocked
    web_blocked = blocked

@app.before_request
def before_request():
    """Log every request and block if web_blocked is True."""
    if web_blocked:
        return make_response(render_template('service_unavailable.html'), 503)
    g.start_time = datetime.now()
    logger.info(f"WEB request: {request.method} {request.path} from {request.remote_addr}", service="web")

@app.after_request
def after_request(response):
    """Log every response with timing info."""
    duration = (datetime.now() - g.start_time).total_seconds()
    logger.info(f"WEB response: {request.method} {request.path} status {response.status_code} ({duration:.3f}s)", service="web")
    return response

@app.route('/', methods=['GET', 'POST'])
def login():
    """Simulated login page (vulnerable to SQL injection)."""
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
    """Simulated dashboard page (requires login)."""
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM production")
    data = c.fetchall()
    conn.close()
    return render_template('dashboard.html', data=data)

# CRUD: Add Product
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user' not in session:
        return redirect(url_for('login'))
    error = None
    if request.method == 'POST':
        reference = request.form.get('reference')
        family = request.form.get('family')
        product = request.form.get('product')
        quantity = request.form.get('quantity')
        status = request.form.get('status')
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO production (reference, family, product, quantity, status) VALUES (?, ?, ?, ?, ?)",
                      (reference, family, product, quantity, status))
            conn.commit()
            conn.close()
            logger.info(f"WEB product added: {reference} - {product}", service="web")
            return redirect(url_for('dashboard'))
        except Exception as e:
            error = str(e)
    return render_template('add_product.html', error=error)

# CRUD: Edit Product
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM production WHERE id = ?", (product_id,))
    product = c.fetchone()
    error = None
    if request.method == 'POST':
        reference = request.form.get('reference')
        family = request.form.get('family')
        prod = request.form.get('product')
        quantity = request.form.get('quantity')
        status = request.form.get('status')
        try:
            c.execute("UPDATE production SET reference = ?, family = ?, product = ?, quantity = ?, status = ? WHERE id = ?",
                      (reference, family, prod, quantity, status, product_id))
            conn.commit()
            logger.info(f"WEB product edited: {reference} - {prod}", service="web")
            return redirect(url_for('dashboard'))
        except Exception as e:
            error = str(e)
    conn.close()
    return render_template('edit_product.html', product=product, error=error)

# CRUD: Delete Product
@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM production WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        logger.info(f"WEB product deleted: {product_id}", service="web")
    except Exception as e:
        logger.warning(f"WEB product delete failed: {product_id} - {e}", service="web")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    """Log out the current user."""
    session.pop('user', None)
    return redirect(url_for('login'))

def set_web_status(status):
    """Update the web service status in the shared status file."""
    status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                data = json.load(f)
        else:
            data = {}
        data['web'] = status
        with open(status_file, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

def start_web_server(config=None, logger=None):
    """Start the web honeypot Flask app in a background thread."""
    global web_server_thread, web_should_run
    port = 8080
    if config:
        port = config.get('services', {}).get('web', {}).get('port', 8080)
    def run():
        set_web_status("running")
        try:
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        except Exception:
            set_web_status("error")
        set_web_status("stopped")
    web_should_run = True
    web_server_thread = threading.Thread(target=run, daemon=True)
    web_server_thread.start()

def stop_web_server():
    """Attempt to stop the Flask app by calling the /shutdown route."""
    global web_should_run
    try:
        # Try to stop Flask by sending a shutdown request
        requests.get('http://127.0.0.1:8080/shutdown')
    except Exception:
        pass
    web_should_run = False
    set_web_status("stopped")

@app.route('/shutdown')
def shutdown():
    """Shutdown route for hard-stopping the Flask app (used internally)."""
    set_web_status("stopped")
    import os
    os._exit(0)

@app.errorhandler(404)
def handle_404(e):
    """Return 503 if blocked, otherwise default 404."""
    if web_blocked:
        from flask import make_response, render_template
        return make_response(render_template('service_unavailable.html'), 503)
    return e

@app.errorhandler(500)
def handle_500(e):
    """Return 503 if blocked, otherwise default 500."""
    if web_blocked:
        from flask import make_response, render_template
        return make_response(render_template('service_unavailable.html'), 503)
    return e

if __name__ == '__main__':
    # For standalone testing
    port = int(os.environ.get('PMS_WEB_PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
