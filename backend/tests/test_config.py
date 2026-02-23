import os
import pytest
from backend.app.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_default_host(self):
        """Should have default host."""
        # Reset singleton
        Config._instance = None
        os.environ.pop("API_HOST", None)
        config = Config()
        assert config.host == "0.0.0.0"

    def test_custom_host_from_env(self):
        """Should read host from environment variable."""
        Config._instance = None
        os.environ["API_HOST"] = "127.0.0.1"
        config = Config()
        assert config.host == "127.0.0.1"
        os.environ.pop("API_HOST", None)
        Config._instance = None

    def test_default_port(self):
        """Should have default port."""
        Config._instance = None
        os.environ.pop("API_PORT", None)
        config = Config()
        assert config.port == 8000

    def test_custom_port_from_env(self):
        """Should read port from environment variable."""
        Config._instance = None
        os.environ["API_PORT"] = "9000"
        config = Config()
        assert config.port == 9000
        os.environ.pop("API_PORT", None)
        Config._instance = None

    def test_is_production_when_env_is_production(self):
        """Should return True when ENV is production."""
        Config._instance = None
        os.environ["ENV"] = "production"
        config = Config()
        assert config.is_production is True
        os.environ.pop("ENV", None)
        Config._instance = None

    def test_is_production_when_env_is_development(self):
        """Should return False when ENV is development."""
        Config._instance = None
        os.environ["ENV"] = "development"
        config = Config()
        assert config.is_production is False
        os.environ.pop("ENV", None)
        Config._instance = None

    def test_is_development_default(self):
        """Should be development by default."""
        Config._instance = None
        os.environ.pop("ENV", None)
        config = Config()
        assert config.is_development is True
        Config._instance = None

    def test_api_base_url_default(self):
        """Should have default API base URL."""
        Config._instance = None
        os.environ.pop("API_BASE_URL", None)
        config = Config()
        assert config.api_base_url == "http://localhost:8000"
        Config._instance = None

    def test_database_url_default(self):
        """Should have default database URL."""
        Config._instance = None
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("SQLITE_DB_PATH", None)
        config = Config()
        assert "sqlite" in config.database_url
        Config._instance = None

    def test_singleton_returns_same_instance(self):
        """Should return same instance (singleton pattern)."""
        Config._instance = None
        config1 = Config()
        config2 = Config()
        assert config1 is config2
        Config._instance = None
