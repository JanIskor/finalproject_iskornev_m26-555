"""Общие функции валидации и конвертации валют."""

import math


def usd_rate(code: str, rates: dict[str, float]) -> float:
    """Возвращает стоимость единицы валюты в USD."""
    if code == "USD":
        return 1.0

    pair = f"{code}_USD"

    if pair not in rates:
        raise ValueError(f"Отсутствует курс валютной пары {pair}")

    rate = rates[pair]

    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        raise TypeError(f"Курс {pair} должен быть числом")

    if not math.isfinite(rate) or rate <= 0:
        raise ValueError(f"Курс {pair} должен быть положительным и конечным")

    return float(rate)


def convert_currency(
    amount: float,
    source: str,
    target: str,
    rates: dict[str, float],
) -> float:
    """Конвертирует сумму через USD без промежуточного округления."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise TypeError("Сумма должна быть числом")

    if not math.isfinite(amount) or amount < 0:
        raise ValueError("Сумма должна быть конечной и неотрицательной")

    if not isinstance(rates, dict):
        raise TypeError("Курсы валют должны быть словарём")

    result = amount * usd_rate(source, rates) / usd_rate(target, rates)

    if not math.isfinite(result):
        raise ValueError("Результат конвертации превышает допустимый диапазон")

    return result
