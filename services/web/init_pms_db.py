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
        # Drop and recreate users and production tables
        c.execute('DROP TABLE IF EXISTS users')
        c.execute('DROP TABLE IF EXISTS production')
        # Create users table
        c.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )''')
        if logger:
            logger.info("Created 'users' table in PMS database.", service="web")
        # Create production table with new schema
        c.execute('''CREATE TABLE production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT NOT NULL,
            family TEXT NOT NULL,
            product TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL
        )''')
        if logger:
            logger.info("Created 'production' table in PMS database.", service="web")
        # Insert users from config
        web_users = config['services']['web'].get('users', [])
        for user in web_users:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user['username'], user['password']))
            if logger:
                logger.info(f"Inserted user: {user['username']}", service="web")
        # Insert mock production data
        prod_data = [
            ('REF001', 'FamilyA', 'Widget A', 120, 'Completed'),
            ('REF002', 'FamilyB', 'Widget B', 75, 'In Progress'),
            ('REF003', 'FamilyC', 'Widget C', 200, 'Completed'),
            ('REF004', 'FamilyD', 'Widget D', 50, 'Pending'),
        ]
        for p in prod_data:
            c.execute("INSERT INTO production (reference, family, product, quantity, status) VALUES (?, ?, ?, ?, ?)", p)
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
