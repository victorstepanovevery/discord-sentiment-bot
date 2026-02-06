"""Database management."""
import aiosqlite
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = None

    async def connect(self):
        logger.info(f"Connecting to database at {self.db_path}")
        self.connection = await aiosqlite.connect(self.db_path)
        await self._create_tables()
        logger.info("Database connected and tables created")

    async def disconnect(self):
        if self.connection:
            await self.connection.close()

    async def _create_tables(self):
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                channel_id TEXT,
                author_id TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await self.connection.commit()
