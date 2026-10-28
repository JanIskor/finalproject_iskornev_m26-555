from valutatrade_hub.core.currencies import CryptoCurrency, Currency, FiatCurrency
from valutatrade_hub.core.exceptions import CurrencyNotFoundError


CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency("USD", "US Dollar", "United States"),
    "EUR": FiatCurrency("EUR", "Euro", "Eurozone"),
    "GBP": FiatCurrency("GBP", "British Pound", "United Kingdom"),
    "BTC": CryptoCurrency("BTC", "Bitcoin", "SHA-256", 1_200_000_000_000),
    "ETH": CryptoCurrency("ETH", "Ethereum", "Proof of Stake", 400_000_000_000),
    "SOL": CryptoCurrency("SOL", "Solana", "Proof of Stake", 70_000_000_000),
}


def get_currency(code: str) -> Currency:
    """Получить поддерживаемую валюту по её коду."""
    if not isinstance(code, str):
        raise TypeError("Код валюты должен быть строкой")

    normalized_code = code.strip().upper()

    try:
        return CURRENCY_REGISTRY[normalized_code]
    except KeyError:
        raise CurrencyNotFoundError(normalized_code) from None
