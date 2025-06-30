from loguru import logger
import os
import json

class Logger:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)
        logger.remove()
        self.ssh_logger = logger.bind(service="ssh")
        self.dns_logger = logger.bind(service="dns")
        self.smb_logger = logger.bind(service="smb")
        self.ftp_logger = logger.bind(service="ftp")
        self.web_logger = logger.bind(service="web")
        # Use JSON format for easier parsing
        log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[service]} | {message}"
        json_format = '{{"timestamp": "{time:YYYY-MM-DD HH:mm:ss}", "level": "{level}", "service": "{extra[service]}", "message": "{message}"}}'
        logger.add("logs/ssh_honeypot.log", rotation="1 MB", filter=lambda record: record["extra"].get("service") == "ssh", format=json_format)
        logger.add("logs/dns_honeypot.log", rotation="1 MB", filter=lambda record: record["extra"].get("service") == "dns", format=json_format)
        logger.add("logs/smb_honeypot.log", rotation="1 MB", filter=lambda record: record["extra"].get("service") == "smb", format=json_format)
        logger.add("logs/ftp_honeypot.log", rotation="1 MB", filter=lambda record: record["extra"].get("service") == "ftp", format=json_format)
        logger.add("logs/web_honeypot.log", rotation="1 MB", filter=lambda record: record["extra"].get("service") == "web", format=json_format)

    def info(self, msg, service="ssh"):
        if service == "ssh":
            self.ssh_logger.info(msg)
        elif service == "dns":
            self.dns_logger.info(msg)
        elif service == "smb":
            self.smb_logger.info(msg)
        elif service == "ftp":
            self.ftp_logger.info(msg)
        elif service == "web":
            self.web_logger.info(msg)

    def warning(self, msg, service="ssh"):
        if service == "ssh":
            self.ssh_logger.warning(msg)
        elif service == "dns":
            self.dns_logger.warning(msg)
        elif service == "smb":
            self.smb_logger.warning(msg)
        elif service == "ftp":
            self.ftp_logger.warning(msg)
        elif service == "web":
            self.web_logger.warning(msg)

    def error(self, msg, service="ssh"):
        if service == "ssh":
            self.ssh_logger.error(msg)
        elif service == "dns":
            self.dns_logger.error(msg)
        elif service == "smb":
            self.smb_logger.error(msg)
        elif service == "ftp":
            self.ftp_logger.error(msg)
        elif service == "web":
            self.web_logger.error(msg)
