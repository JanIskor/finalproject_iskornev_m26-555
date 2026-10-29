"""Интеграционные проверки команд валютных курсов."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.cli.interface import run
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.updater import RatesUpdater


class CLIIntegrationTests(unittest.TestCase):
    """Проверяет совместную работу CLI, кеша и Parser Service."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

        root = Path(self.directory.name)
        rates_file = root / "rates.json"
        history_file = root / "exchange_rates.json"

        self.rates_patch = patch.object(
            SettingsLoader,
            "rates_file",
            property(lambda _: rates_file),
        )
        self.history_patch = patch.object(
            SettingsLoader,
            "exchange_rates_file",
            property(lambda _: history_file),
        )

        self.rates_patch.start()
        self.history_patch.start()

        self.addCleanup(self.rates_patch.stop)
        self.addCleanup(self.history_patch.stop)

    def _run_cli(self, commands):
        output = io.StringIO()

        with (
            patch("builtins.input", side_effect=[*commands, "exit"]),
            redirect_stdout(output),
        ):
            run()

        return output.getvalue()

    def test_update_show_and_get_rate(self):
        def fetch_rates(client):
            if type(client).__name__ == "CoinGeckoClient":
                return {"BTC_USD": 60000.0, "ETH_USD": 3000.0}
            return {"EUR_USD": 1.2}

        with (
            patch(
                "valutatrade_hub.parser_service.api_clients."
                "CoinGeckoClient.fetch_rates",
                autospec=True,
                side_effect=fetch_rates,
            ),
            patch(
                "valutatrade_hub.parser_service.api_clients."
                "ExchangeRateApiClient.fetch_rates",
                autospec=True,
                side_effect=fetch_rates,
            ),
        ):
            output = self._run_cli(
                [
                    "update-rates",
                    "show-rates --top 2",
                    "get-rate --from BTC --to EUR",
                ]
            )

        self.assertIn("Обновление успешно завершено", output)
        self.assertIn("BTC_USD", output)
        self.assertIn("ETH_USD", output)
        self.assertIn("50000", output)

    def test_invalid_source_does_not_stop_cli(self):
        output = self._run_cli(
            [
                "update-rates --source unknown",
                "help",
            ]
        )

        self.assertIn("Неизвестный источник", output)
        self.assertIn("Доступные команды", output)

    def test_api_failure_does_not_stop_cli(self):
        with patch.object(
            RatesUpdater,
            "run_update",
            side_effect=RuntimeError("Тестовый сбой API"),
        ):
            output = self._run_cli(
                [
                    "update-rates",
                    "help",
                ]
            )

        self.assertIn("Доступные команды", output)


if __name__ == "__main__":
    unittest.main()
