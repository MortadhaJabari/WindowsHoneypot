import yaml

class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file

    def load(self):
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)
