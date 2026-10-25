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
