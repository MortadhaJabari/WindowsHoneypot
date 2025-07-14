from flask import Flask, render_template, request, redirect, url_for, session, abort, make_response, Response
import os
from dotenv import load_dotenv
import re
import json
import time

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs'))

# Helper to parse log lines (simple example, can be improved)
def parse_log_file(filepath, page=1, per_page=50):
    entries = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        lines = lines[::-1]  # Most recent first
        start = (page - 1) * per_page
        end = start + per_page
        for line in lines[start:end]:
            try:
                log = json.loads(line)
                entries.append({
                    'timestamp': log.get('timestamp', ''),
                    'level': log.get('level', ''),
                    'service': log.get('service', ''),
                    'message': log.get('message', '')
                })
            except Exception:
                entries.append({'timestamp': '', 'level': 'ERROR', 'service': '', 'message': line.strip()})
    except Exception as e:
        entries.append({'timestamp': '', 'level': 'ERROR', 'service': '', 'message': f'Could not read log: {e}'})
    return entries

def run_admin_app(port=6000):
    app = Flask(__name__, template_folder='templates', static_folder=None)
    app.secret_key = os.urandom(32)

    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'changeme')

    @app.route('/secret-admin/9595', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                session['admin_logged_in'] = True
                resp = make_response(redirect(url_for('dashboard')))
                resp.set_cookie('admin_logged_in', '1', max_age=60*60*24)
                return resp
            else:
                error = 'Invalid credentials.'
        return render_template('login.html', error=error)

    @app.before_request
    def check_login_cookie():
        if not session.get('admin_logged_in') and request.cookies.get('admin_logged_in') == '1':
            session['admin_logged_in'] = True

    @app.route('/admin/dashboard')
    def dashboard():
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        # Read status file for all services
        import json
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
        ssh_status = ftp_status = dns_status = smb_status = web_status = 'unknown'
        try:
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    data = json.load(f)
                ssh_status = data.get('ssh', 'unknown')
                ftp_status = data.get('ftp', 'unknown')
                dns_status = data.get('dns', 'unknown')
                web_status = data.get('web', 'unknown')
        except Exception:
            pass
        return render_template('logs.html', log_files=get_log_files(),
            ssh_status=ssh_status, ftp_status=ftp_status, dns_status=dns_status, web_status=web_status)

    @app.route('/admin/logs/<logfile>')
    def view_log(logfile):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        if not logfile.endswith('.log'):
            abort(404)
        log_path = os.path.join(LOGS_DIR, logfile)
        page = int(request.args.get('page', 1))
        per_page = 50
        entries = parse_log_file(log_path, page=page, per_page=per_page)
        # Count total lines for pagination
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                total_lines = len(f.readlines())
        except Exception:
            total_lines = 0
        total_pages = (total_lines + per_page - 1) // per_page
        return render_template('log_view.html', logfile=logfile, entries=entries, page=page, total_pages=total_pages)

    @app.route('/admin/logout')
    def logout():
        session.pop('admin_logged_in', None)
        resp = make_response(redirect(url_for('login')))
        resp.set_cookie('admin_logged_in', '', expires=0)
        return resp

    @app.route('/admin/service/ssh/<action>', methods=['POST'])
    def control_ssh(action):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        # Update desired state in service_status.json
        import json
        import datetime
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
        try:
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            if action == 'stop':
                data['ssh_desired'] = 'stopped'
                # Log to SSH service log
                try:
                    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/ssh_honeypot.log')), 'a', encoding='utf-8') as sshlog:
                        import datetime
                        sshlog.write('{"timestamp": "%s", "level": "INFO", "service": "ssh", "message": "SSH honeypot stopped by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                except Exception:
                    pass
            elif action == 'start':
                data['ssh_desired'] = 'running'
                # Log to SSH service log
                try:
                    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/ssh_honeypot.log')), 'a', encoding='utf-8') as sshlog:
                        import datetime
                        sshlog.write('{"timestamp": "%s", "level": "INFO", "service": "ssh", "message": "SSH honeypot started by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                except Exception:
                    pass
            with open(status_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
        return redirect(url_for('dashboard'))

    @app.route('/admin/service/ftp/<action>', methods=['POST'])
    def control_ftp(action):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        import json, datetime
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
        ftp_log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/ftp_honeypot.log'))
        try:
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            if action == 'stop':
                data['ftp_desired'] = 'stopped'
                with open(ftp_log_file, 'a', encoding='utf-8') as f:
                    f.write('{"timestamp": "%s", "level": "INFO", "service": "ftp", "message": "FTP honeypot stopped by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            elif action == 'start':
                data['ftp_desired'] = 'running'
                with open(ftp_log_file, 'a', encoding='utf-8') as f:
                    f.write('{"timestamp": "%s", "level": "INFO", "service": "ftp", "message": "FTP honeypot started by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            with open(status_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
        return redirect(url_for('dashboard'))

    @app.route('/admin/service/dns/<action>', methods=['POST'])
    def control_dns(action):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        import json, datetime
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
        dns_log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/dns_honeypot.log'))
        try:
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            if action == 'stop':
                data['dns_desired'] = 'stopped'
                with open(dns_log_file, 'a', encoding='utf-8') as f:
                    f.write('{"timestamp": "%s", "level": "INFO", "service": "dns", "message": "DNS honeypot stopped by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            elif action == 'start':
                data['dns_desired'] = 'running'
                with open(dns_log_file, 'a', encoding='utf-8') as f:
                    f.write('{"timestamp": "%s", "level": "INFO", "service": "dns", "message": "DNS honeypot started by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            with open(status_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
        return redirect(url_for('dashboard'))

    @app.route('/admin/service/smb/<action>', methods=['POST'])
    def control_smb(action):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        import json, datetime
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
        smb_log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/smb_honeypot.log'))
        try:
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            if action == 'stop':
                data['smb_desired'] = 'stopped'
                with open(smb_log_file, 'a', encoding='utf-8') as f:
                    f.write('{"timestamp": "%s", "level": "INFO", "service": "smb", "message": "SMB honeypot stopped by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            elif action == 'start':
                data['smb_desired'] = 'running'
                with open(smb_log_file, 'a', encoding='utf-8') as f:
                    f.write('{"timestamp": "%s", "level": "INFO", "service": "smb", "message": "SMB honeypot started by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            with open(status_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
        return redirect(url_for('dashboard'))

    @app.route('/admin/service/web/<action>', methods=['POST'])
    def control_web(action):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        import json, datetime
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
        web_log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/web_honeypot.log'))
        try:
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            if action == 'stop':
                data['web_desired'] = 'stopped'
                with open(web_log_file, 'a', encoding='utf-8') as f:
                    f.write('{"timestamp": "%s", "level": "INFO", "service": "web", "message": "Web honeypot stopped by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            elif action == 'start':
                data['web_desired'] = 'running'
                with open(web_log_file, 'a', encoding='utf-8') as f:
                    f.write('{"timestamp": "%s", "level": "INFO", "service": "web", "message": "Web honeypot started by admin panel"}\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            with open(status_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
        return redirect(url_for('dashboard'))

    # --- SSE endpoint for real-time service status updates ---
    @app.route('/admin/events')
    def admin_events():
        def event_stream():
            last_status = None
            status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
            while True:
                try:
                    if os.path.exists(status_file):
                        with open(status_file, 'r') as f:
                            data = json.load(f)
                    else:
                        data = {}
                except Exception:
                    data = {}
                if data != last_status:
                    yield f"data: {json.dumps(data)}\n\n"
                    last_status = data.copy() if isinstance(data, dict) else data
                time.sleep(2)
        return Response(event_stream(), mimetype="text/event-stream")

    def get_log_files():
        try:
            return [f for f in os.listdir(LOGS_DIR) if f.endswith('.log')]
        except Exception:
            return []

    app.run(host='0.0.0.0', port=port, debug=False)
