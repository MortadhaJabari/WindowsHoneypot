from loguru import logger
import os

class Logger:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)
        # Remove all previously added handlers just in case
        logger.remove()

        # Add handlers for SSH and DNS logs separately
        self.ssh_logger = logger.bind(service="ssh")
        self.dns_logger = logger.bind(service="dns")
        self.smb_logger = logger.bind(service="smb")
        logger.add("logs/ssh_honeypot.log", rotation="1 MB", filter=lambda record: record["extra"].get("service") == "ssh")
        logger.add("logs/dns_honeypot.log", rotation="1 MB", filter=lambda record: record["extra"].get("service") == "dns")
        logger.add("logs/smb_honeypot.log", rotation="1 MB", filter=lambda record: record["extra"].get("service") == "smb")

    
    def info(self, msg, service="ssh"):
        if service == "ssh":
            self.ssh_logger.info(msg)
        elif service == "dns":
            self.dns_logger.info(msg)
        elif service == "smb":
            self.smb_logger.info(msg)

    def warning(self, msg, service="ssh"):
        if service == "ssh":
            self.ssh_logger.warning(msg)
        elif service == "dns":
            self.dns_logger.warning(msg)
        elif service == "smb":
            self.smb_logger.warning(msg)

    def error(self, msg, service="ssh"):
        if service == "ssh":
            self.ssh_logger.error(msg)
        elif service == "dns":
            self.dns_logger.error(msg)
        elif service == "smb":
            self.smb_logger.error(msg)
