"""Проверки API-клиентов, обновления курсов и хранения данных."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def response_with(payload):
    """Создаёт поддельный успешный HTTP-ответ."""
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class WorkingClient:
    """Тестовый источник курсов."""

    def fetch_rates(self):
        return {"BTC_USD": 60000.0}


class BrokenClient:
    """Тестовый источник с ошибкой."""

    def fetch_rates(self):
        raise ApiRequestError("Сервис недоступен", source="TestAPI")


class ParserServiceTests(unittest.TestCase):
    """Проверяет основные сценарии работы парсера."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.storage = RatesStorage(
            rates_file=root / "rates.json",
            history_file=root / "history.json",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_coingecko_success(self):
        payload = {
            "bitcoin": {"usd": 60000},
            "ethereum": {"usd": 3000},
            "solana": {"usd": 150},
        }
        with patch("requests.get", return_value=response_with(payload)):
            rates = CoinGeckoClient().fetch_rates()

        self.assertEqual(rates["BTC_USD"], 60000.0)
        self.assertEqual(len(rates), 3)

    def test_http_401_and_429(self):
        for status in (401, 429):
            with self.subTest(status=status):
                response = Mock()
                response.raise_for_status.side_effect = requests.HTTPError(
                    f"HTTP {status}"
                )
                with patch("requests.get", return_value=response):
                    with self.assertRaises(ApiRequestError):
                        CoinGeckoClient().fetch_rates()

    def test_timeout(self):
        with patch(
            "requests.get",
            side_effect=requests.Timeout("Тайм-аут"),
        ):
            with self.assertRaises(ApiRequestError):
                CoinGeckoClient().fetch_rates()

    def test_invalid_json(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("Неверный JSON")

        with patch("requests.get", return_value=response):
            with self.assertRaises(ApiRequestError):
                CoinGeckoClient().fetch_rates()

    def test_exchange_rate_inversion(self):
        payload = {
            "result": "success",
            "conversion_rates": {
                "EUR": 0.8,
                "GBP": 0.5,
                "RUB": 100,
            },
        }
        with patch.dict(os.environ, {"EXCHANGE_RATE_API_KEY": "test-key"}):
            with patch("requests.get", return_value=response_with(payload)):
                rates = ExchangeRateApiClient().fetch_rates()

        self.assertEqual(rates["EUR_USD"], 1.25)
        self.assertEqual(rates["RUB_USD"], 0.01)

    def test_partial_failure(self):
        result = RatesUpdater(
            clients=[WorkingClient(), BrokenClient()],
            storage=self.storage,
        ).run_update()

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.saved_count, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(self.storage.load_history()), 1)

    def test_total_failure_preserves_cache(self):
        RatesUpdater(
            clients=[WorkingClient()],
            storage=self.storage,
        ).run_update()

        before = self.storage.load_rates()

        with self.assertRaises(ApiRequestError):
            RatesUpdater(
                clients=[BrokenClient(), BrokenClient()],
                storage=self.storage,
            ).run_update()

        self.assertEqual(self.storage.load_rates(), before)

    def test_duplicate_and_old_rates(self):
        timestamp = "2026-10-29T10:00:00Z"

        self.assertEqual(
            self.storage.save_rates(
                {"BTC_USD": 60000},
                source="CoinGecko",
                timestamp=timestamp,
            ),
            1,
        )

        self.assertEqual(
            self.storage.save_rates(
                {"BTC_USD": 60000},
                source="CoinGecko",
                timestamp=timestamp,
            ),
            0,
        )

        self.assertEqual(
            self.storage.save_rates(
                {"BTC_USD": 100},
                source="CoinGecko",
                timestamp="2026-10-29T09:00:00Z",
            ),
            0,
        )

        self.assertEqual(len(self.storage.load_history()), 1)

    def test_api_key_not_in_parser_log(self):
        secret = "test-secret-api-key-123"

        with patch.dict(os.environ, {"EXCHANGE_RATE_API_KEY": secret}):
            with patch(
                "requests.get",
                side_effect=requests.Timeout("Секретный URL не раскрываем"),
            ):
                result = RatesUpdater(
                    clients=[ExchangeRateApiClient(), WorkingClient()],
                    storage=self.storage,
                ).run_update()

        self.assertEqual(len(result.errors), 1)
        self.assertNotIn(secret, str(result.errors))

        from valutatrade_hub.infra.settings import SettingsLoader

        log_path = SettingsLoader().logs_dir / "parser.log"
        log_content = log_path.read_text(encoding="utf-8")
        self.assertNotIn(secret, log_content)


if __name__ == "__main__":
    unittest.main()
