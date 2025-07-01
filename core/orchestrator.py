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
        self.ftp_task = None
        self.dns_task = None
        self.smb_task = None

    def run(self):
        tasks = []
        # Add enabled service watchers to the asyncio task list
        if self.config["services"]["ssh"]["enabled"]:
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


    async def generic_service_watcher(self, service_name, desired_key, status_key, start_func, stop_func, task_attr):
        """
        Generic watcher for services.
        service_name: e.g. 'ssh', 'ftp', 'dns', 'smb'
        desired_key: e.g. 'ssh_desired'
        status_key: e.g. 'ssh'
        start_func: function to start the service (should be a coroutine)
        stop_func: function to stop the service (should be a coroutine)
        task_attr: attribute name for the asyncio task (e.g. 'ssh_task')
        """
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
                desired = data.get(desired_key, 'running')
            except Exception:
                data = {}
            if desired == 'running' and not running:
                # Start service as an asyncio task
                task = asyncio.create_task(start_func(self.config, self.logger))
                setattr(self, task_attr, task)
                running = True
                # Set status to running in status file
                try:
                    data[status_key] = 'running'
                    with open(status_file, 'w') as f:
                        json.dump(data, f)
                except Exception:
                    pass
            elif desired == 'stopped' and running:
                # Stop service and update status
                await stop_func()
                task = getattr(self, task_attr, None)
                if task:
                    task.cancel()
                    setattr(self, task_attr, None)
                running = False
                try:
                    data[status_key] = 'stopped'
                    with open(status_file, 'w') as f:
                        json.dump(data, f)
                except Exception:
                    pass
            await asyncio.sleep(2)

    # Wrappers for each service watcher
    async def ssh_service_watcher(self):
        from services.ssh import ssh_service
        return await self.generic_service_watcher(
            service_name='ssh',
            desired_key='ssh_desired',
            status_key='ssh',
            start_func=ssh_service.start_ssh_server,
            stop_func=ssh_service.stop_ssh_server,
            task_attr='ssh_task'
        )

    async def ftp_service_watcher(self):
        from services.ftp import ftp_service
        return await self.generic_service_watcher(
            service_name='ftp',
            desired_key='ftp_desired',
            status_key='ftp',
            start_func=ftp_service.start_ftp_server,
            stop_func=ftp_service.stop_ftp_server,
            task_attr='ftp_task'
        )

    async def dns_service_watcher(self):
        from services.dns import dns_service
        return await self.generic_service_watcher(
            service_name='dns',
            desired_key='dns_desired',
            status_key='dns',
            start_func=dns_service.start_dns_server,
            stop_func=dns_service.stop_dns_server,
            task_attr='dns_task'
        )

    async def smb_service_watcher(self):
        from services.smb import smb_service
        return await self.generic_service_watcher(
            service_name='smb',
            desired_key='smb_desired',
            status_key='smb',
            start_func=smb_service.start_smb_server,
            stop_func=smb_service.stop_smb_server,
            task_attr='smb_task'
        )

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
