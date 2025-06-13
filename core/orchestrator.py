import asyncio
from services.ssh import ssh_service
from services.dns import dns_service
from services.smb.smb_service import start_smb_server

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

        if self.config["services"]["smb"]["enabled"]:
            tasks.append(start_smb_server(self.config, self.logger))

        if tasks:
            try:
                asyncio.run(self.run_services(tasks))
            except (KeyboardInterrupt, SystemExit):
                print("\n[!] Honeypot interrupted by user. Shutting down...")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="ssh")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="dns")
                self.logger.info("Honeypot interrupted by user. Shutting down...", service="smb")

    async def run_services(self, services):
        await asyncio.gather(*services)
