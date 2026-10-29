"""Конфигурация источников валютных курсов."""

import os
from dataclasses import dataclass, field

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
EXCHANGE_RATE_API_URL = "https://v6.exchangerate-api.com/v6"

CRYPTO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}

FIAT_CURRENCIES = ("EUR", "GBP", "RUB")


@dataclass(frozen=True, slots=True)
class ParserConfig:
    """Хранит настройки HTTP-клиентов и обновления курсов."""

    coingecko_url: str = COINGECKO_API_URL
    exchange_rate_url: str = EXCHANGE_RATE_API_URL
    timeout_seconds: float = 10.0
    base_currency: str = "USD"
    crypto_ids: dict[str, str] = field(default_factory=lambda: CRYPTO_IDS.copy())
    fiat_currencies: tuple[str, ...] = FIAT_CURRENCIES

    @property
    def exchange_rate_api_key(self) -> str | None:
        """Читает API-ключ из окружения, не сохраняя его в коде."""
        return os.getenv("EXCHANGE_RATE_API_KEY") or None
