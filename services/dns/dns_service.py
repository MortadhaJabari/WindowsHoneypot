import asyncio
from dnslib.server import DNSServer, DNSHandler, BaseResolver
from dnslib import RR, QTYPE, A

class FakeDNSResolver(BaseResolver):
    def __init__(self, config, logger):
        self.records = config["services"]["dns"]["fake_records"]
        self.logger = logger

    def resolve(self, request, handler):
        reply = request.reply()
        qname = request.q.qname
        qtype = QTYPE[request.q.qtype]
        subdomain = str(qname).rstrip('.').split('.')[0]

        client_ip = handler.client_address[0]  # Extract client IP from handler
        self.logger.info(f"DNS Query from {client_ip} for {qname}", service="dns")

        ip = self.records.get(subdomain)
        if ip:
            self.logger.info(f"Resolved {qname} to {ip} for client {client_ip}", service="dns")
            reply.add_answer(RR(qname, QTYPE.A, rdata=A(ip), ttl=60))
        else:
            self.logger.warning(f"No fake record found for {qname} from client {client_ip}", service="dns")

        return reply

dns_server_instance = None
def set_dns_status(status):
    import json
    import os
    status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs/service_status.json'))
    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                data = json.load(f)
        else:
            data = {}
        data['dns'] = status
        with open(status_file, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

async def start_dns_server(config, logger):
    global dns_server_instance
    port = config["services"]["dns"]["port"]
    resolver = FakeDNSResolver(config, logger)
    server = DNSServer(resolver, port=port, address="0.0.0.0")
    dns_server_instance = server
    logger.info(f"Starting DNS server on port {port}",service="dns")
    set_dns_status("running")
    server.start_thread()
    try:
        while True:
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        set_dns_status("stopped")
        if dns_server_instance:
            dns_server_instance.stop()
            dns_server_instance = None
        raise
    except Exception:
        set_dns_status("error")
        raise
    set_dns_status("stopped")

async def stop_dns_server():
    global dns_server_instance
    if dns_server_instance:
        dns_server_instance.stop()
        dns_server_instance = None
    set_dns_status("stopped")
