"""Настройка файлового логирования ValutaTrade Hub."""

import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

LOGGER_NAME = "valutatrade_hub"
LOG_FILENAME = "valutatrade.log"
MAX_LOG_SIZE = 1_048_576
BACKUP_COUNT = 3


class ISO8601Formatter(logging.Formatter):
    """Форматирует время логирования в ISO 8601 с часовым поясом UTC."""

    def formatTime(self, record, datefmt=None):
        """Возвращает временную метку записи в UTC."""
        return datetime.fromtimestamp(
            record.created,
            tz=timezone.utc,
        ).isoformat(timespec="milliseconds")


def setup_logging() -> logging.Logger:
    """Настраивает файловый логгер приложения без дублирования обработчиков."""
    settings = SettingsLoader()
    logger = logging.getLogger(LOGGER_NAME)

    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    log_level = logging.getLevelName(settings.log_level.upper())
    if not isinstance(log_level, int):
        raise ValueError(f"Некорректный уровень логирования: {settings.log_level}")

    logger.setLevel(log_level)
    logger.propagate = False

    log_file = settings.logs_dir / LOG_FILENAME

    for handler in logger.handlers:
        if (
            isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename).resolve() == log_file.resolve()
        ):
            handler.setLevel(log_level)
            handler.setFormatter(ISO8601Formatter(settings.log_format))
            return logger

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(ISO8601Formatter(settings.log_format))

    logger.addHandler(file_handler)

    return logger
