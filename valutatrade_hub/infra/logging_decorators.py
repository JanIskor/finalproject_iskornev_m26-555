"""Декораторы безопасного логирования операций приложения."""

import logging
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from valutatrade_hub.infra.logging_config import LOGGER_NAME

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(LOGGER_NAME)


def log_action(func: Callable[P, R]) -> Callable[P, R]:
    """Логирует начало и успешное завершение операции без её аргументов."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger.debug("Начало операции: %s", func.__name__)
        result = func(*args, **kwargs)
        logger.info("Операция успешно завершена: %s", func.__name__)
        return result

    return wrapper


def log_errors(func: Callable[P, R]) -> Callable[P, R]:
    """Логирует тип ошибки, сохраняя исходное исключение."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.error(
                "Ошибка операции %s: %s",
                func.__name__,
                type(exc).__name__,
            )
            raise

    return wrapper
