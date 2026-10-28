"""Исключения предметной области ValutaTrade Hub."""


class InsufficientFundsError(ValueError):
    """Возникает при попытке списать больше средств, чем доступно."""


class CurrencyNotFoundError(ValueError):
    """Ошибка при обращении к неподдерживаемой валюте."""

    def __init__(self, currency_code: str) -> None:
        self.currency_code = currency_code
        super().__init__(f"Валюта '{currency_code}' не поддерживается")


class ApiRequestError(Exception):
    """Ошибка получения данных от внешнего API."""

    def __init__(self, message: str, source: str | None = None) -> None:
        self.source = source
        self.message = message

        if source is not None:
            super().__init__(f"{source}: {message}")
        else:
            super().__init__(message)
