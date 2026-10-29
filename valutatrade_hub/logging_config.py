"""Настройка файлового логирования ValutaTrade Hub."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
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


class UTCFormatter(logging.Formatter):
    """Форматирует время записи в ISO 8601 UTC."""

    def formatTime(self, record, datefmt=None):
        """Возвращает временную метку с часовым поясом UTC."""
        timestamp = datetime.fromtimestamp(record.created, timezone.utc)
        return timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def setup_parser_logging() -> logging.Logger:
    """Настраивает файловый логгер без дублирования обработчиков."""
    settings = SettingsLoader()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("valutatrade_hub.parser")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_path = settings.logs_dir / "parser.log"

    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename == str(
            log_path.resolve()
        ):
            return logger

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(UTCFormatter(settings.log_format))

    logger.addHandler(handler)
    return logger


@contextmanager
def parser_console_logging() -> Iterator[None]:
    """Временно выводит INFO-логи парсера в консоль."""
    logger = setup_parser_logging()
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger.addHandler(handler)

    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()
