"""Декораторы безопасного логирования бизнес-операций."""

import inspect
import logging
from functools import wraps
from typing import Callable, ParamSpec, TypeVar, overload

from valutatrade_hub.logging_config import LOGGER_NAME

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(LOGGER_NAME)

SAFE_ARGUMENTS = (
    "user_id",
    "username",
    "currency_code",
    "from_currency",
    "to_currency",
    "amount",
)
SAFE_ERROR_TYPES = {
    "InsufficientFundsError",
    "CurrencyNotFoundError",
}


def _operation_context(func: Callable, args: tuple, kwargs: dict) -> str:
    """Извлекает только разрешённые для логирования аргументы."""
    bound = inspect.signature(func).bind_partial(*args, **kwargs)

    context = []

    for name in SAFE_ARGUMENTS:
        if name not in bound.arguments:
            continue

        value = bound.arguments[name]

        if name == "amount":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
        elif name == "user_id":
            if isinstance(value, bool) or not isinstance(value, int):
                continue
        elif not isinstance(value, str):
            continue

        context.append(f"{name}={value!r}")

    return " ".join(context)


@overload
def log_action(func: Callable[P, R]) -> Callable[P, R]: ...


@overload
def log_action(
    func: None = None,
    *,
    verbose: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def log_action(func=None, *, verbose: bool = False):
    """Логирует операции, при verbose добавляя изменение баланса."""

    def decorator(operation):
        @wraps(operation)
        def wrapper(*args, **kwargs):
            action = operation.__name__.upper()
            context = _operation_context(operation, args, kwargs)

            logger.debug("action=%s %s stage=START", action, context)

            result = operation(*args, **kwargs)

            details = ""

            if verbose and action in {"BUY", "SELL"}:
                try:
                    bound = inspect.signature(operation).bind_partial(*args, **kwargs)

                    currency_code = bound.arguments.get("currency_code")
                    amount = bound.arguments.get("amount")

                    if (
                        isinstance(currency_code, str)
                        and isinstance(amount, (int, float))
                        and not isinstance(amount, bool)
                    ):
                        wallet = result.get_wallet(currency_code)
                        balance_after = wallet.balance

                        if action == "BUY":
                            balance_before = balance_after - amount
                        else:
                            balance_before = balance_after + amount

                        details = (
                            f" balance_before={balance_before:.12g}"
                            f" balance_after={balance_after:.12g}"
                        )

                except Exception:
                    logger.debug(
                        "action=%s stage=VERBOSE_CONTEXT_UNAVAILABLE",
                        action,
                    )

            logger.info(
                "action=%s %s%s result=OK",
                action,
                context,
                details,
            )

            return result

        return wrapper

    if func is None:
        return decorator

    return decorator(func)


def log_errors(func: Callable[P, R]) -> Callable[P, R]:
    """Логирует ошибки операций, не раскрывая секретные данные."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            action = func.__name__.upper()
            context = _operation_context(func, args, kwargs)
            error_type = type(exc).__name__

            if error_type in SAFE_ERROR_TYPES:
                error_message = str(exc)
            else:
                error_message = "Внутренняя ошибка приложения"

            logger.error(
                "action=%s %s result=ERROR error_type=%s error_message=%r",
                action,
                context,
                error_type,
                error_message,
            )
            raise

    return wrapper
