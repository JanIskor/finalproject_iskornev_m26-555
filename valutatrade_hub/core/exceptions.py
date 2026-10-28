"""Исключения предметной области ValutaTrade Hub."""


class InsufficientFundsError(ValueError):
    """Возникает при попытке списать больше средств, чем доступно."""


class CurrencyNotFoundError(ValueError):
    """Ошибка при обращении к неподдерживаемой валюте."""

    def __init__(self, currency_code: str) -> None:
        self.currency_code = currency_code
        super().__init__(f"Валюта '{currency_code}' не поддерживается")
