import asyncio
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

    def run(self):
        tasks = []

        if self.config["services"]["ssh"]["enabled"]:
            tasks.append(ssh_service.start_ssh_server(self.config, self.logger))

        if self.config["services"]["dns"]["enabled"]:
            tasks.append(dns_service.start_dns_server(self.config, self.logger))

        if self.config["services"].get("smb", {}).get("enabled", False):
            tasks.append(start_smb_server(self.config, self.logger))

        if self.config["services"].get("ftp", {}).get("enabled", False):
            tasks.append(start_ftp_server(self.config, self.logger))

        # Ensure PMS DB is initialized before starting web honeypot
        if self.config["services"].get("web", {}).get("enabled", False):
            PMSDatabaseInitializer.initialize(self.config)

        if self.config["services"].get("web", {}).get("enabled", False):
            port = self.config["services"]["web"].get("port", 8080)
            def run_web():
                web_app.run(host='0.0.0.0', port=port, debug=False)
            t = threading.Thread(target=run_web, daemon=True)
            t.start()
            self.logger.info(f"Web honeypot started on port {port}", service="web")

        if tasks:
            try:
                asyncio.run(self.run_services(tasks))
            except (KeyboardInterrupt, SystemExit):
                print("\n[!] Honeypot interrupted by user. Shutting down...")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="ssh")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="dns")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="smb")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="ftp")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="web")

    async def run_services(self, services):
        await asyncio.gather(*services)
