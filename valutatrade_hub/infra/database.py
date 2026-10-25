"""Хранение пользователей и портфелей в JSON-файлах."""

import json
import os
import tempfile
from pathlib import Path
from threading import Lock
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Управляет локальным хранилищем данных приложения."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """Возвращает единственный экземпляр менеджера."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Настраивает хранилище и создаёт отсутствующие файлы."""
        if getattr(self, "_initialized", False):
            return

        self._settings = SettingsLoader()
        self._settings.data_dir.mkdir(parents=True, exist_ok=True)

        self._initialize_file(self._settings.users_file, [])
        self._initialize_file(self._settings.portfolios_file, {})

        self._initialized = True

    @staticmethod
    def _initialize_file(path: Path, default: Any) -> None:
        """Создаёт файл с начальными данными, если он отсутствует."""
        if not path.exists():
            DatabaseManager._write_json(path, default)

    @staticmethod
    def _read_json(path: Path, expected_type: type) -> Any:
        """Читает JSON и проверяет тип корневой структуры."""
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Не удалось прочитать данные из {path.name}: {exc}"
            ) from exc

        if not isinstance(data, expected_type):
            raise ValueError(f"Некорректная структура данных в файле {path.name}")

        return data

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        """Атомарно сохраняет JSON, не повреждая предыдущую версию."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.stem}_",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def load_users(self) -> list[dict]:
        """Загружает список зарегистрированных пользователей."""
        return self._read_json(self._settings.users_file, list)

    def save_users(self, users: list[dict]) -> None:
        """Сохраняет список пользователей."""
        if not isinstance(users, list):
            raise TypeError("Пользователи должны быть представлены списком")

        self._write_json(self._settings.users_file, users)

    def load_portfolios(self) -> dict:
        """Загружает портфели пользователей."""
        return self._read_json(self._settings.portfolios_file, dict)

    def save_portfolios(self, portfolios: dict) -> None:
        """Сохраняет портфели пользователей."""
        if not isinstance(portfolios, dict):
            raise TypeError("Портфели должны быть представлены словарём")

        self._write_json(self._settings.portfolios_file, portfolios)
