"""Исключения предметной области ValutaTrade Hub."""


class InsufficientFundsError(ValueError):
    """Возникает при попытке списать больше средств, чем доступно."""
