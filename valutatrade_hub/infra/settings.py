"""Централизованные настройки приложения ValutaTrade Hub."""

from pathlib import Path
from threading import Lock


class SettingsLoader:
    """Предоставляет единый экземпляр настроек приложения."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """Создаёт экземпляр настроек только при первом обращении."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализирует пути и параметры приложения."""
        if getattr(self, "_initialized", False):
            return

        self._project_root = Path(__file__).resolve().parents[2]
        self._data_dir = self._project_root / "data"
        self._logs_dir = self._project_root / "logs"

        self._base_currency = "USD"
        self._rates_ttl_seconds = 300
        self._log_level = "INFO"
        self._log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

        self._initialized = True

    @property
    def project_root(self) -> Path:
        """Возвращает корневой каталог проекта."""
        return self._project_root

    @property
    def data_dir(self) -> Path:
        """Возвращает каталог хранения данных."""
        return self._data_dir

    @property
    def logs_dir(self) -> Path:
        """Возвращает каталог логов."""
        return self._logs_dir

    @property
    def users_file(self) -> Path:
        """Возвращает путь к файлу пользователей."""
        return self._data_dir / "users.json"

    @property
    def portfolios_file(self) -> Path:
        """Возвращает путь к файлу портфелей."""
        return self._data_dir / "portfolios.json"

    @property
    def rates_file(self) -> Path:
        """Возвращает путь к файлу актуальных курсов."""
        return self._data_dir / "rates.json"

    @property
    def exchange_rates_file(self) -> Path:
        """Возвращает путь к истории курсов."""
        return self._data_dir / "exchange_rates.json"

    @property
    def base_currency(self) -> str:
        """Возвращает базовую валюту приложения."""
        return self._base_currency

    @property
    def rates_ttl_seconds(self) -> int:
        """Возвращает срок актуальности курсов в секундах."""
        return self._rates_ttl_seconds

    @property
    def log_level(self) -> str:
        """Возвращает уровень файлового логирования."""
        return self._log_level

    @property
    def log_format(self) -> str:
        """Возвращает формат сообщений логирования."""
        return self._log_format

    def get(self, key: str, default=None):
        """Возвращает настройку по имени или значение по умолчанию."""
        if not isinstance(key, str):
            raise TypeError("Название настройки должно быть строкой")

        available_settings = {
            "project_root": self.project_root,
            "data_dir": self.data_dir,
            "logs_dir": self.logs_dir,
            "users_file": self.users_file,
            "portfolios_file": self.portfolios_file,
            "rates_file": self.rates_file,
            "exchange_rates_file": self.exchange_rates_file,
            "base_currency": self.base_currency,
            "rates_ttl_seconds": self.rates_ttl_seconds,
            "log_level": self.log_level,
            "log_format": self.log_format,
        }

        return available_settings.get(key, default)
