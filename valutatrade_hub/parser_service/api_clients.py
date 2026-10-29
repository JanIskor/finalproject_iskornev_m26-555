"""HTTP-клиенты для получения валютных курсов."""

import math
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


def _valid_rate(value: object) -> bool:
    """Проверяет, что курс — положительное конечное число."""
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


class BaseApiClient(ABC):
    """Общий интерфейс источников валютных курсов."""

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config if config is not None else ParserConfig()

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Возвращает курсы валют относительно USD."""

    def _request_json(
        self,
        url: str,
        source: str,
        params: dict[str, str] | None = None,
    ) -> dict:
        """Выполняет запрос и проверяет корректность ответа."""
        try:
            response = requests.get(
                url,
                params=params,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise ApiRequestError(
                "Не удалось получить данные от сервиса",
                source=source,
            ) from exc
        except ValueError as exc:
            raise ApiRequestError(
                "Сервис вернул некорректный JSON",
                source=source,
            ) from exc

        if not isinstance(data, dict):
            raise ApiRequestError(
                "Ожидался JSON-объект",
                source=source,
            )

        return data


class CoinGeckoClient(BaseApiClient):
    """Получает USD-курсы криптовалют через CoinGecko."""

    def fetch_rates(self) -> dict[str, float]:
        """Загружает и проверяет котировки криптовалют."""
        crypto_ids = self.config.crypto_ids

        if not crypto_ids:
            return {}

        data = self._request_json(
            self.config.coingecko_url,
            source="CoinGecko",
            params={
                "ids": ",".join(crypto_ids.values()),
                "vs_currencies": "usd",
            },
        )

        rates = {}

        for code, coin_id in crypto_ids.items():
            coin_data = data.get(coin_id)

            if not isinstance(coin_data, dict):
                raise ApiRequestError(
                    f"Отсутствуют данные для {code}",
                    source="CoinGecko",
                )

            rate = coin_data.get("usd")

            if not _valid_rate(rate):
                raise ApiRequestError(
                    f"Некорректный курс {code}_USD",
                    source="CoinGecko",
                )

            rates[f"{code}_USD"] = float(rate)

        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Получает курсы фиатных валют через ExchangeRate API."""

    def fetch_rates(self) -> dict[str, float]:
        """Загружает курсы и преобразует их относительно USD."""
        if not self.config.fiat_currencies:
            return {}

        api_key = self.config.exchange_rate_api_key

        if not api_key:
            raise ApiRequestError(
                "Не задан EXCHANGE_RATE_API_KEY",
                source="ExchangeRate API",
            )

        url = (
            f"{self.config.exchange_rate_url.rstrip('/')}"
            f"/{api_key}/latest/{self.config.base_currency}"
        )

        data = self._request_json(
            url,
            source="ExchangeRate API",
        )

        if data.get("result") != "success":
            raise ApiRequestError(
                "API не подтвердил успешное выполнение запроса",
                source="ExchangeRate API",
            )

        conversion_rates = data.get("conversion_rates")

        if not isinstance(conversion_rates, dict):
            raise ApiRequestError(
                "Отсутствует объект conversion_rates",
                source="ExchangeRate API",
            )

        rates = {}

        for code in self.config.fiat_currencies:
            usd_to_currency = conversion_rates.get(code)

            if not _valid_rate(usd_to_currency):
                raise ApiRequestError(
                    f"Некорректный курс USD_{code}",
                    source="ExchangeRate API",
                )

            rates[f"{code}_USD"] = 1.0 / float(usd_to_currency)

        return rates
