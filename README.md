# WindowsServerHoneypot

A multi-service honeypot for Windows and Linux, simulating SSH, FTP, DNS, SMB, and a vulnerable web application for research and monitoring purposes.

## Features
- **SSH Honeypot:** Simulates an SSH server to capture login attempts and attacker behavior.
- **FTP Honeypot:** Emulates an FTP server, logging file access and credentials.
- **DNS Honeypot:** Responds to DNS queries and logs suspicious or unexpected requests.
- **Web Honeypot:** Runs a vulnerable web application (with fake login, dashboard, and CRUD) to attract and analyze web attacks.
- **Admin Panel:** Web-based interface for monitoring logs and managing the honeypot.
- **Centralized Logging:** All service activity is logged for analysis and alerting.
- **Modular and Extensible:** Easily enable/disable or extend services via configuration.
- **Designed for Research & Detection:** Useful for threat intelligence, deception, and security education.

## Quick Start

### 1. Install uv (Python dependency manager)

**Linux:**
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Generate SSH Key Pair

This is required for the SSH honeypot to function.

```sh
ssh-keygen -t rsa -b 4096 -C "your_email@example.com" -f ./ssh_host_key
```

This will create `ssh_host_key` and `ssh_host_key.pub` in your project root.

### 3. Install dependencies

```sh
uv sync
```

This will install all dependencies as specified in `uv.lock`/`pyproject.toml`.

### 4. Run the honeypot

```sh
uv run main.py
```

All services will start according to your configuration. By default, the admin honeypot is available at [http://localhost:8080](http://localhost:8080).

## Tips & Notes
- **Configuration:** Edit `config/honeypot.yaml` to enable/disable services and set ports.
- **Logs:** All logs are stored in the `logs/` directory.
- **Admin Panel:** Accessible at the port specified in your config (default: 8080 at url /secret-admin/9595 (can be edited in the admin_service.py)).
- **SSH/FTP/DNS/SMB:** Make sure the required ports are open and not used by other services.
<!-- Docker usage removed as per latest instructions -->
- **Production:** For real deployments, use a non-default secret key and secure your environment.

## About
This project is for research, education, and security monitoring. Do not deploy in production environments without understanding the risks. Contributions and feedback are welcome!
