import asyncio
import asyncssh
import sys
from services.ssh.windows_shell import WindowsShell
from services.ssh.windows_banner import generate_banner
import os


class SSHHoneypotSession(asyncssh.SSHServerSession):
    def __init__(self, logger, config):
        self._input = ""
        self._chan = None
        self.logger = logger
        self.config = config
        users = config["services"]["ssh"].get("users", [])
        self.shell = WindowsShell(users=users)
        
   

     
    def connection_made(self, chan):
        self._chan = chan
        self.peername = chan.get_extra_info('peername')
        self.username = self._chan.get_extra_info('username')
        if self.peername:
            host, port =self.peername
            self.logger.info(f"New SSH connection from {self.username}@{host}:{port}", service="ssh")

    def session_started(self):
        host, port =self.peername
        self.logger.info(f" Shell session started from {self.username}@{host}:{port} ", service="ssh")
        banner  = generate_banner(self.username)
        self._chan.write(banner)

    def eof_received(self):
        self.logger.info(f"EOF received for user {self.username}")
        exit_signal = self.shell.handle_command(self.username, "exit")
        if exit_signal == "__exit__":
            self._chan.write("Logging off...\n")
            self._chan.exit(0)
        return True



    def data_received(self, data, datatype):

        host, port =self.peername
        self.logger.info(f"{self.username}@{host}:{port} executed  command: {data.strip()}   ", service="ssh")
        response = self.shell.handle_command(self.username,data.strip())
        if response == "__exit__":
            self._chan.write("Logging off...\n")
            self._chan.exit(0)  # Close session gracefully
            return 
        # Show the correct prompt reflecting the current directory
        prompt = f"{self.shell.current_dir}> "
        self._chan.write(response + "\n")
        self._chan.write(prompt)

    def connection_lost(self, exc):
        host, port =self.peername
        self.logger.info(f"{self.username}@{host}:{port}  SSH session ended" , service="ssh")

    def shell_requested(self):
        host, port =self.peername
        self.logger.info(f"{self.username}@{host}:{port}  Shell requested", service="ssh")
        return True  
    
class SSHHoneypotServer(asyncssh.SSHServer):
    def __init__(self, users, logger, config):
        self.users = users
        self.logger = logger
        self.config = config

    def connection_requested(self, dest_host, dest_port, orig_host, orig_port):
        self.logger.info(f"Connection requested from {orig_host}:{orig_port} to {dest_host}:{dest_port}", service="ssh")
        return self
    
    def connection_made(self, conn):
        self.peername = conn.get_extra_info('peername')


    def begin_auth(self, username):
        return True

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        host , port = self.peername
        for user in self.users:
            if user['username'] == username and user['password'] == password:
                self.logger.info(f"Login success: {username}@{host}:{port}", service="ssh")
                return True
        self.logger.warning(f"Login failed: {username}@{host}:{port} with password: {password}", service="ssh")
        return False

    def session_requested(self):
        return SSHHoneypotSession( self.logger, self.config )
    
ssh_server_instance = None
ssh_server_event = None

def set_ssh_status(status):
    import json
    status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                data = json.load(f)
        else:
            data = {}
        data['ssh'] = status
        with open(status_file, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

async def start_ssh_server(config, logger):
    global ssh_server_instance, ssh_server_event
    port = config["services"]["ssh"]["port"]
    users = config["services"]["ssh"]["users"]
    logger.info(f"Starting SSH honeypot on port {port}...")
    set_ssh_status("running")
    try:
        ssh_server_event = asyncio.Event()
        ssh_server_instance = await asyncssh.listen(
            '', port,
            server_factory=lambda: SSHHoneypotServer(users, logger, config),
            server_host_keys=['ssh_host_key'],
            encoding='utf-8'
        )
        logger.info("SSH honeypot running. Press Ctrl+C to stop.", service="ssh")
        await ssh_server_event.wait()  # Keeps the server alive
    except (OSError, asyncssh.Error) as e:
        logger.error(f"Failed to start SSH server: {e}", service="ssh")
        set_ssh_status("error")
    finally:
        set_ssh_status("stopped")

async def stop_ssh_server():
    global ssh_server_instance, ssh_server_event
    if ssh_server_instance:
        ssh_server_instance.close()
        await ssh_server_instance.wait_closed()
        ssh_server_instance = None
    if ssh_server_event:
        ssh_server_event.set()
        ssh_server_event = None
    set_ssh_status("stopped")

