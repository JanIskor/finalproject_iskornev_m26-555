"""Настройка отдельного файлового логирования парсера."""

import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


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
