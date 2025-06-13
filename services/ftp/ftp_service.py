import asyncio
import os
import logging
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

# Suppress pyftpdlib's own logging to the terminal
logging.getLogger("pyftpdlib").setLevel(logging.CRITICAL)

class FTPHoneypotHandler(FTPHandler):
    def on_connect(self):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.info(f"FTP connection from {ip}:{port}", service="ftp")

    def on_login(self, username):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.info(f"FTP login: {username} from {ip}:{port}", service="ftp")

    def on_login_failed(self, username, password):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.warning(f"FTP failed login: {username} with password: {password} from {ip}:{port}", service="ftp")

    def on_file_sent(self, file):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.info(f"FTP file sent: {file} to {ip}:{port}", service="ftp")

    def on_file_received(self, file):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.info(f"FTP file uploaded: {file} from {ip}:{port}", service="ftp")

    def on_incomplete_file_sent(self, file):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.warning(f"FTP incomplete file sent: {file} to {ip}:{port}", service="ftp")

    def on_incomplete_file_received(self, file):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.warning(f"FTP incomplete file uploaded: {file} from {ip}:{port}", service="ftp")

    def on_disconnect(self):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.info(f"FTP disconnect from {ip}:{port}", service="ftp")

    def ftp_RETR(self, file):
        ip, port = self.remote_ip, self.remote_port
        if not os.path.exists(file):
            self.log_service.warning(f"FTP attempted download of non-existent file: {file} from {ip}:{port}", service="ftp")
        return super().ftp_RETR(file)

    def ftp_STOR(self, file):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.info(f"FTP attempted upload: {file} from {ip}:{port}", service="ftp")
        return super().ftp_STOR(file)

    def on_command(self, cmd, arg, resp, resp_code):
        ip, port = self.remote_ip, self.remote_port
        self.log_service.info(f"FTP command: {cmd} {arg if arg else ''} from {ip}:{port} -> {resp_code} {resp}", service="ftp")

async def start_ftp_server(config, logger):
    port = config["services"]["ftp"]["port"]
    users = config["services"]["ftp"]["users"]
    fake_files = config["services"]["ftp"].get("fake_files", [])
    banner = config["services"]["ftp"].get("banner", "220 Microsoft FTP Service")

    # Prepare fake FTP directory
    base_fake_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fakefiles'))
    os.makedirs(base_fake_dir, exist_ok=True)
    for fname in fake_files:
        fpath = os.path.join(base_fake_dir, fname)
        if not os.path.exists(fpath):
            with open(fpath, 'w') as f:
                f.write('This is a fake FTP file for honeypot analysis.')

    authorizer = DummyAuthorizer()
    for user in users:
        authorizer.add_user(user['username'], user['password'], base_fake_dir, perm='elradfmwMT')
    authorizer.add_anonymous(base_fake_dir, perm='elr')

    handler = FTPHoneypotHandler
    handler.authorizer = authorizer
    handler.banner = banner
    handler.log_service = logger

    server = FTPServer(('0.0.0.0', port), handler)
    logger.info(f"FTP honeypot service is starting on port {port}...", service="ftp")
    loop = asyncio.get_running_loop()
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            await loop.run_in_executor(pool, server.serve_forever)
        except asyncio.CancelledError:
            logger.info("FTP honeypot server received cancellation. Shutting down...", service="ftp")
            server.close_all()
            raise
