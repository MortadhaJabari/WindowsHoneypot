import asyncio
import subprocess
import os
import time
from services.ssh import ssh_service
from services.dns import dns_service
from services.smb.smb_service import start_smb_server
from services.ftp.ftp_service import start_ftp_server
from services.web.web_honeypot import app as web_app
from services.web.init_pms_db import PMSDatabaseInitializer
import threading

class HoneypotOrchestrator:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.ssh_task = None
        self.ssh_should_run = False

    def run(self):
        tasks = []
        # Add enabled service watchers to the asyncio task list
        if self.config["services"]["ssh"]["enabled"]:
            self.ssh_should_run = True
            tasks.append(self.ssh_service_watcher())
        if self.config["services"]["ftp"]["enabled"]:
            tasks.append(self.ftp_service_watcher())
        if self.config["services"]["dns"]["enabled"]:
            tasks.append(self.dns_service_watcher())
        if self.config["services"].get("smb", {}).get("enabled", False):
            tasks.append(self.smb_service_watcher())
        if self.config["services"].get("web", {}).get("enabled", False):
            tasks.append(self.web_service_watcher())

        # Ensure PMS DB is initialized before starting web honeypot
        if self.config["services"].get("web", {}).get("enabled", False):
            PMSDatabaseInitializer.initialize(self.config)

        # Start the web honeypot in a background thread if enabled
        if self.config["services"].get("web", {}).get("enabled", False):
            port = self.config["services"]["web"].get("port", 8080)
            def run_web():
                web_app.run(host='0.0.0.0', port=port, debug=False)
            t = threading.Thread(target=run_web, daemon=True)
            t.start()
            self.logger.info(f"Web honeypot started on port {port}", service="web")

        # Start the admin panel in a background thread if enabled
        if self.config["services"].get("admin", {}).get("enabled", False):
            admin_port = self.config["services"]["admin"].get("port", 6000)
            from services.admin.admin_service import run_admin_app
            def run_admin():
                run_admin_app(port=admin_port)
            t = threading.Thread(target=run_admin, daemon=True)
            t.start()
            self.logger.info(f"Admin panel started on port {admin_port}", service="admin")

        # Run all enabled service watchers concurrently
        if tasks:
            try:
                asyncio.run(self.run_services(tasks))
            except (KeyboardInterrupt, SystemExit):
                print("\n[!] Honeypot interrupted by user. Shutting down...")
                # Log shutdown for all services
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="ssh")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="dns")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="smb")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="ftp")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="web")

    async def run_services(self, services):
        # Run all service watcher coroutines concurrently
        await asyncio.gather(*services)

    async def ssh_service_watcher(self):
        # Watches the desired state for SSH and starts/stops the service accordingly
        import json
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logs/service_status.json'))
        running = False
        while True:
            desired = 'running'
            try:
                if os.path.exists(status_file):
                    with open(status_file, 'r') as f:
                        data = json.load(f)
                else:
                    data = {}
                desired = data.get('ssh_desired', 'running')
            except Exception:
                data = {}
            if desired == 'running' and not running:
                # Start SSH server as an asyncio task
                self.ssh_task = asyncio.create_task(
                    ssh_service.start_ssh_server(self.config, self.logger)
                )
                running = True
                # Set status to running in status file
                try:
                    data['ssh'] = 'running'
                    with open(status_file, 'w') as f:
                        json.dump(data, f)
                except Exception:
                    pass
            elif desired == 'stopped' and running:
                # Stop SSH server and update status
                await ssh_service.stop_ssh_server()
                if self.ssh_task:
                    self.ssh_task.cancel()
                    self.ssh_task = None
                running = False
                try:
                    data['ssh'] = 'stopped'
                    with open(status_file, 'w') as f:
                        json.dump(data, f)
                except Exception:
                    pass
            await asyncio.sleep(2)

    async def ftp_service_watcher(self):
        # Watches the desired state for FTP and starts/stops the service accordingly
        import json
        from services.ftp import ftp_service
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logs/service_status.json'))
        running = False
        while True:
            desired = 'running'
            try:
                if os.path.exists(status_file):
                    with open(status_file, 'r') as f:
                        data = json.load(f)
                    desired = data.get('ftp_desired', 'running')
            except Exception:
                pass
            if desired == 'running' and not running:
                # Start FTP server as an asyncio task
                self.ftp_task = asyncio.create_task(
                    ftp_service.start_ftp_server(self.config, self.logger)
                )
                running = True
            elif desired == 'stopped' and running:
                # Stop FTP server and update status
                await ftp_service.stop_ftp_server()
                if hasattr(self, 'ftp_task') and self.ftp_task:
                    self.ftp_task.cancel()
                    self.ftp_task = None
                running = False
            await asyncio.sleep(2)

    async def dns_service_watcher(self):
        # Watches the desired state for DNS and starts/stops the service accordingly
        import json
        from services.dns import dns_service
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logs/service_status.json'))
        running = False
        while True:
            desired = 'running'
            try:
                if os.path.exists(status_file):
                    with open(status_file, 'r') as f:
                        data = json.load(f)
                    desired = data.get('dns_desired', 'running')
            except Exception:
                pass
            if desired == 'running' and not running:
                # Start DNS server as an asyncio task
                self.dns_task = asyncio.create_task(
                    dns_service.start_dns_server(self.config, self.logger)
                )
                running = True
            elif desired == 'stopped' and running:
                # Stop DNS server and update status
                await dns_service.stop_dns_server()
                if hasattr(self, 'dns_task') and self.dns_task:
                    self.dns_task.cancel()
                    self.dns_task = None
                running = False
            await asyncio.sleep(2)

    async def smb_service_watcher(self):
        # Watches the desired state for SMB and starts/stops the service accordingly
        import json
        from services.smb import smb_service
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logs/service_status.json'))
        running = False
        while True:
            desired = 'running'
            try:
                if os.path.exists(status_file):
                    with open(status_file, 'r') as f:
                        data = json.load(f)
                    desired = data.get('smb_desired', 'running')
            except Exception:
                pass
            if desired == 'running' and not running:
                # Start SMB server as an asyncio task
                self.smb_task = asyncio.create_task(
                    smb_service.start_smb_server(self.config, self.logger)
                )
                running = True
            elif desired == 'stopped' and running:
                # Stop SMB server and update status
                await smb_service.stop_smb_server()
                if hasattr(self, 'smb_task') and self.smb_task:
                    self.smb_task.cancel()
                    self.smb_task = None
                running = False
            await asyncio.sleep(2)

    async def web_service_watcher(self):
        # Watches the desired state for the web honeypot and blocks/unblocks access accordingly
        import json
        from services.web import web_honeypot
        status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logs/service_status.json'))
        port = self.config["services"]["web"].get("port", 8080)
        # Ensure web server is running in a background thread
        if not hasattr(web_honeypot, 'web_server_thread') or not web_honeypot.web_server_thread or not web_honeypot.web_server_thread.is_alive():
            try:
                web_honeypot.start_web_server(self.config, self.logger)
            except Exception as e:
                self.logger.error(f"Failed to start web honeypot: {e}", service="web")
        while True:
            desired = 'running'
            try:
                if os.path.exists(status_file):
                    with open(status_file, 'r') as f:
                        data = json.load(f)
                else:
                    data = {}
                desired = data.get('web_desired', 'running')
            except Exception:
                data = {}
            # Always set block flag and update status
            if desired == 'running':
                web_honeypot.set_web_blocked(False)
                # Set status to running
                try:
                    data['web'] = 'running'
                    with open(status_file, 'w') as f:
                        json.dump(data, f)
                except Exception:
                    pass
            else:
                web_honeypot.set_web_blocked(True)
                # Set status to blocked
                try:
                    data['web'] = 'blocked'
                    with open(status_file, 'w') as f:
                        json.dump(data, f)
                except Exception:
                    pass
            await asyncio.sleep(2)
