from core.config_manager import ConfigManager
from core.logger import Logger
from core.orchestrator import HoneypotOrchestrator

if __name__ == "__main__":
    config = ConfigManager("config/honeypot.yaml").load()
    logger = Logger()
    orchestrator = HoneypotOrchestrator(config, logger)
    orchestrator.run()
