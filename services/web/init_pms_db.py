from core.config_manager import ConfigManager
from core.logger import Logger
import sqlite3
from datetime import datetime
import os

class PMSDatabaseInitializer:
    @staticmethod
    def initialize(config, logger=None):
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), 'pms.db')
        db_exists = os.path.exists(db_path)
        if logger:
            if not db_exists:
                logger.info(f"Creating new PMS database file at {db_path}", service="web")
            else:
                logger.info(f"Opening existing PMS database file at {db_path}", service="web")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        # Create users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )''')
        if logger:
            logger.info("Created or verified 'users' table in PMS database.", service="web")
        # Create production table
        c.execute('''CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )''')
        if logger:
            logger.info("Created or verified 'production' table in PMS database.", service="web")
        # Insert mock users
        web_users = config['services']['web'].get('users', [])
        c.execute("DELETE FROM users")
        for user in web_users:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user['username'], user['password']))
            if logger:
                logger.info(f"Inserted user: {user['username']}", service="web")
        # Insert mock production data
        c.execute("DELETE FROM production")
        prod_data = [
            ('Widget A', 120, 'Completed', '2025-06-27 08:30:00'),
            ('Widget B', 75, 'In Progress', '2025-06-27 09:15:00'),
            ('Widget C', 200, 'Completed', '2025-06-27 10:00:00'),
            ('Widget D', 50, 'Pending', '2025-06-27 10:45:00'),
        ]
        for p in prod_data:
            c.execute("INSERT INTO production (product, quantity, status, timestamp) VALUES (?, ?, ?, ?)", p)
            if logger:
                logger.info(f"Inserted production record: {p}", service="web")
        conn.commit()
        conn.close()
        if logger:
            logger.info("--- PMS DB INIT END ---", service="web")
        print("PMS database initialized.")

if __name__ == "__main__":
    from core.config_manager import ConfigManager
    from core.logger import Logger
    config = ConfigManager('../../config/honeypot.yaml').load()
    logger = Logger()
    PMSDatabaseInitializer.initialize(config, logger)
