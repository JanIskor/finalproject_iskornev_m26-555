"""Проверки TTL валютных курсов и безопасности логирования."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.usecases import get_rate
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.api_clients import ExchangeRateApiClient
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


class RatesTTLTests(unittest.TestCase):
    """Проверяет обновление кеша при различных состояниях источников."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

        root = Path(self.directory.name)
        self.rates_file = root / "rates.json"
        self.history_file = root / "exchange_rates.json"
        self.storage = RatesStorage(self.rates_file, self.history_file)

        self.settings_patch = patch.object(
            SettingsLoader,
            "rates_file",
            new_callable=lambda: property(lambda settings: self.rates_file),
        )
        self.history_patch = patch.object(
            SettingsLoader,
            "exchange_rates_file",
            new_callable=lambda: property(lambda settings: self.history_file),
        )

        self.settings_patch.start()
        self.history_patch.start()

        self.addCleanup(self.settings_patch.stop)
        self.addCleanup(self.history_patch.stop)

    def _save(self, rates, age_seconds):
        timestamp = (
            (datetime.now(timezone.utc) - timedelta(seconds=age_seconds))
            .isoformat()
            .replace("+00:00", "Z")
        )
        self.storage.save_rates(rates, source="Test", timestamp=timestamp)

    def test_fresh_cache_does_not_refresh(self):
        self._save({"BTC_USD": 60000.0}, age_seconds=30)

        with patch.object(
            RatesUpdater,
            "run_update",
            side_effect=AssertionError("Обновление не требуется"),
        ):
            self.assertEqual(get_rate("BTC", "USD"), 60000.0)

    def test_stale_cache_triggers_refresh(self):
        self._save({"BTC_USD": 50000.0}, age_seconds=600)

        def refresh(updater):
            updater.storage.save_rates(
                {"BTC_USD": 60000.0},
                source="CoinGecko",
            )

        with patch.object(RatesUpdater, "run_update", autospec=True) as mocked:
            mocked.side_effect = refresh
            self.assertEqual(get_rate("BTC", "USD"), 60000.0)
            mocked.assert_called_once()

    def test_partial_failure_does_not_freshen_other_pair(self):
        self._save({"BTC_USD": 50000.0, "EUR_USD": 1.1}, age_seconds=600)

        def partial_refresh(updater):
            updater.storage.save_rates(
                {"BTC_USD": 60000.0},
                source="CoinGecko",
            )

        with patch.object(RatesUpdater, "run_update", autospec=True) as mocked:
            mocked.side_effect = partial_refresh

            with self.assertRaises(ApiRequestError):
                get_rate("BTC", "EUR")

        self.assertEqual(self.storage.load_rates()["pairs"]["BTC_USD"]["rate"], 60000.0)
        self.assertEqual(self.storage.load_rates()["pairs"]["EUR_USD"]["rate"], 1.1)

    def test_total_failure_preserves_cache(self):
        self._save({"BTC_USD": 50000.0}, age_seconds=600)

        with patch.object(
            RatesUpdater,
            "run_update",
            side_effect=ApiRequestError("Нет соединения", source="Test"),
        ):
            with self.assertRaises(ApiRequestError):
                get_rate("BTC", "USD")

        self.assertEqual(self.storage.load_rates()["pairs"]["BTC_USD"]["rate"], 50000.0)

    def test_http_error_does_not_log_api_key(self):
        secret = "SECRET_KEY_SHOULD_NEVER_APPEAR_IN_LOG"
        log_file = SettingsLoader().logs_dir / "parser.log"

        before = log_file.read_text(encoding="utf-8") if log_file.exists() else ""

        response = requests.Response()
        response.status_code = 401
        response.url = f"https://v6.exchangerate-api.com/v6/{secret}/latest/USD"

        with (
            patch.dict("os.environ", {"EXCHANGE_RATE_API_KEY": secret}),
            patch("requests.get", return_value=response),
        ):
            with self.assertRaises(ApiRequestError):
                RatesUpdater(
                    clients=[ExchangeRateApiClient()],
                    storage=self.storage,
                ).run_update()

        after = log_file.read_text(encoding="utf-8")
        self.assertNotIn(secret, after[len(before) :])


if __name__ == "__main__":
    unittest.main()
