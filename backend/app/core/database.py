import aiosqlite
from typing import Optional, List, Dict, Any
from .config import settings
import os

class Database:
    def __init__(self):
        # Преобразуем относительный путь в абсолютный
        db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), db_path))
        self.connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Подключиться к базе данных"""
        self.connection = await aiosqlite.connect(self.db_path, timeout=5.0)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.execute("PRAGMA journal_mode = WAL")

    async def disconnect(self):
        """Отключиться от базы данных"""
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Получить одну запись"""
        if not self.connection:
            await self.connect()

        async with self.connection.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Получить все записи"""
        if not self.connection:
            await self.connect()

        async with self.connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def execute(self, query: str, params: tuple = ()) -> int:
        """Выполнить запрос (INSERT/UPDATE/DELETE)"""
        if not self.connection:
            await self.connect()

        cursor = await self.connection.execute(query, params)
        await self.connection.commit()
        return cursor.lastrowid

    async def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Выполнить множественный запрос"""
        if not self.connection:
            await self.connect()

        await self.connection.executemany(query, params_list)
        await self.connection.commit()

# Глобальный экземпляр
db = Database()

async def get_db() -> Database:
    """Dependency для получения соединения с БД"""
    if not db.connection:
        await db.connect()
    return db
