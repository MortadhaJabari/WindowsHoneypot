import asyncio
import os
from impacket.smbserver import SimpleSMBServer


class SMBHoneypotServer(SimpleSMBServer):
    def __init__(self, config, logger):
        port = config["services"]["smb"]["port"]
        super().__init__(listenAddress='0.0.0.0', listenPort=port)
        self.config = config
        self.logger = logger
        self.shares = config["services"]["smb"].get("shares", [])

        # Prepare fake file directories
        base_fake_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fakefiles'))
        os.makedirs(base_fake_dir, exist_ok=True)

        for share in self.shares:
            share_path = os.path.join(base_fake_dir, share['name'])
            os.makedirs(share_path, exist_ok=True)
            for fname in share.get('files', []):
                fpath = os.path.join(share_path, fname)
                if not os.path.exists(fpath):
                    with open(fpath, 'w') as f:
                        f.write('This is a fake file for honeypot analysis.')
            self.addShare(share['name'], share_path, '')
            self.logger.info(f"Added fake SMB share: {share['name']} at {share_path}", service="smb")

        self.setSMB2Support(True)

    def processRequest(self, connId, smbCommand, **kwargs):
        # Overload to log every SMB command received, including client IP/port and operation
        try:
            conn = self._SimpleSMBServer__connections[connId]
            ip, port = conn.getPeerName()
        except Exception:
            ip, port = 'unknown', 'unknown'
        self.logger.info(
            f"SMB command from {ip}:{port} - Operation: {smbCommand}",
            service="smb"
        )
        return super().processRequest(connId, smbCommand, **kwargs)

    def getClientInfo(self, connId):
        # Helper to extract client IP and port from the connection table
        try:
            conn = self._SimpleSMBServer__connections[connId]
            ip, port = conn.getPeerName()
            return {'ip': ip, 'port': port}
        except Exception:
            return {'ip': 'unknown', 'port': 'unknown'}

    def logSMBActivity(self, msg, connId=None):
        # Try to get client info if connId is provided
        ip, port = 'unknown', 'unknown'
        if connId is not None:
            try:
                conn = self._SimpleSMBServer__connections[connId]
                ip, port = conn.getPeerName()
            except Exception:
                pass
        self.logger.info(f"SMB activity from {ip}:{port} - {msg}", service="smb")

    # Patch or wrap the SMB command handlers to call logSMBActivity
    # Example: wrap the doTreeConnectAndX handler
    def doTreeConnectAndX(self, connId, smbPacket, *args, **kwargs):
        self.logSMBActivity("TreeConnectAndX (share connect)", connId)
        return super().doTreeConnectAndX(connId, smbPacket, *args, **kwargs)

    def doOpenAndX(self, connId, smbPacket, *args, **kwargs):
        self.logSMBActivity("OpenAndX (file open)", connId)
        return super().doOpenAndX(connId, smbPacket, *args, **kwargs)

    def doReadAndX(self, connId, smbPacket, *args, **kwargs):
        self.logSMBActivity("ReadAndX (file read)", connId)
        return super().doReadAndX(connId, smbPacket, *args, **kwargs)

    def doWriteAndX(self, connId, smbPacket, *args, **kwargs):
        self.logSMBActivity("WriteAndX (file write)", connId)
        return super().doWriteAndX(connId, smbPacket, *args, **kwargs)

    def doDelete(self, connId, smbPacket, *args, **kwargs):
        self.logSMBActivity("Delete (file delete)", connId)
        return super().doDelete(connId, smbPacket, *args, **kwargs)

    def doClose(self, connId, smbPacket, *args, **kwargs):
        self.logSMBActivity("Close (file close)", connId)
        return super().doClose(connId, smbPacket, *args, **kwargs)


smb_server_instance = None
def set_smb_status(status):
    import json
    import os
    status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                data = json.load(f)
        else:
            data = {}
        data['smb'] = status
        with open(status_file, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

async def start_smb_server(config, logger):
    global smb_server_instance
    port = config["services"]["smb"]["port"]
    logger.info(f"SMB honeypot service is starting on port {port} using impacket...", service="smb")
    server = SMBHoneypotServer(config, logger)
    smb_server_instance = server
    set_smb_status("running")
    logger.info(f"SMB honeypot is now listening for external connections on port {port}.", service="smb")
    loop = asyncio.get_running_loop()
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            await loop.run_in_executor(pool, server.start)
        except asyncio.CancelledError:
            logger.info("SMB honeypot server received cancellation. Shutting down...", service="smb")
            set_smb_status("stopped")
            if hasattr(server, 'stop'):
                server.stop()
            raise
        except Exception:
            set_smb_status("error")
            raise
    set_smb_status("stopped")

async def stop_smb_server():
    global smb_server_instance
    if smb_server_instance and hasattr(smb_server_instance, 'stop'):
        smb_server_instance.stop()
        smb_server_instance = None
    set_smb_status("stopped")
