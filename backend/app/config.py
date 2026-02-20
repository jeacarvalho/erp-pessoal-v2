from __future__ import annotations
import os
from typing import Optional


class Config:
    """Configurações centralizadas do aplicativo.

    Permite configuração via variáveis de ambiente para suportar
    diferentes ambientes (dev, prod, tunnel, etc).
    """

    _instance: Optional["Config"] = None

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._initialized = True

        # Backend server
        self.host: str = os.getenv("API_HOST", "0.0.0.0")
        self.port: int = int(os.getenv("API_PORT", "8000"))

        # URL base do backend para frontends
        # Em dev local: http://localhost:8000
        # Em prod VPS: http://<ip>:8000
        # Em tunnel cloudflare: https://<tunnel-id>.trycloudflare.com
        self.api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000")

        # Database
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            f"sqlite+pysqlite:///{os.getenv('SQLITE_DB_PATH', 'data/sqlite/app.db')}",
        )
        self.sqlite_db_path: Optional[str] = None
        if not os.getenv("DATABASE_URL"):
            self.sqlite_db_path = os.getenv("SQLITE_DB_PATH", "data/sqlite/app.db")

    @property
    def is_production(self) -> bool:
        """Detecta se está em ambiente de produção."""
        return os.getenv("ENV", "development").lower() == "production"

    @property
    def is_development(self) -> bool:
        """Detecta se está em ambiente de desenvolvimento."""
        return not self.is_production


config = Config()


__all__ = ["config", "Config"]
