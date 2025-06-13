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


async def start_dns_server(config, logger):
    port = config["services"]["dns"]["port"]
    resolver = FakeDNSResolver(config, logger)
    server = DNSServer(resolver, port=port, address="0.0.0.0")

    logger.info(f"Starting DNS server on port {port}",service="dns")
    server.start_thread()

    while True:
        await asyncio.sleep(3600)  # Keep the DNS thread running
