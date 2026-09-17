from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .core.config import settings
from .core.database import db
from .api.routes import auth, guilds, contracts, users, reports, permissions

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    await db.connect()
    logger.info("Database connected")
    yield
    # Shutdown
    await db.disconnect()
    logger.info("Database disconnected")

app = FastAPI(
    title="Melancholia Bot API",
    description="API для управления Discord ботом Melancholia",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router, prefix="/api")
app.include_router(guilds.router, prefix="/api")
app.include_router(contracts.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(permissions.router)

# WebSocket для real-time обновлений
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, guild_id: str):
        await websocket.accept()
        if guild_id not in self.active_connections:
            self.active_connections[guild_id] = []
        self.active_connections[guild_id].append(websocket)
        logger.info(f"WebSocket connected for guild {guild_id}")

    def disconnect(self, websocket: WebSocket, guild_id: str):
        if guild_id in self.active_connections:
            self.active_connections[guild_id].remove(websocket)
            logger.info(f"WebSocket disconnected for guild {guild_id}")

    async def broadcast(self, guild_id: str, message: dict):
        """Отправить сообщение всем подключенным клиентам сервера"""
        if guild_id in self.active_connections:
            for connection in self.active_connections[guild_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{guild_id}")
async def websocket_endpoint(websocket: WebSocket, guild_id: str):
    await manager.connect(websocket, guild_id)
    try:
        while True:
            # Ждем сообщений от клиента (ping для keep-alive)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, guild_id)

@app.get("/")
async def root():
    return {
        "message": "Melancholia Bot API",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

# Экспортируем manager для использования в других модулях
__all__ = ["app", "manager"]
