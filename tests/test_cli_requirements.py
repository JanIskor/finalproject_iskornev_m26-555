"""Регрессионные проверки требований к CLI."""

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from valutatrade_hub.cli.interface import _print_portfolio, _print_rate
from valutatrade_hub.core.models import Portfolio


class CLIRequirementsTests(unittest.TestCase):
    """Проверяет отображение курсов и оценку портфеля."""

    def test_rate_displays_oldest_timestamp(self):
        now = datetime.now(timezone.utc)
        btc_time = (now - timedelta(seconds=30)).isoformat()
        eur_time = (now - timedelta(seconds=10)).isoformat()

        cache = {
            "pairs": {
                "BTC_USD": {
                    "rate": 60000.0,
                    "updated_at": btc_time,
                    "source": "test",
                },
                "EUR_USD": {
                    "rate": 1.2,
                    "updated_at": eur_time,
                    "source": "test",
                },
            },
            "last_refresh": eur_time,
        }

        output = io.StringIO()

        with (
            patch(
                "valutatrade_hub.cli.interface.get_rate",
                return_value=50000.0,
            ),
            patch("valutatrade_hub.cli.interface.RatesStorage") as storage_class,
            redirect_stdout(output),
        ):
            storage_class.return_value.load_rates.return_value = cache
            _print_rate("BTC", "EUR")

        expected_time = now - timedelta(seconds=30)

        self.assertIn(
            expected_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            output.getvalue(),
        )
        self.assertIn("Обратный курс EUR→BTC: 2e-05", output.getvalue())

    def test_portfolio_reuses_rates(self):
        portfolio = Portfolio(1)
        portfolio.add_currency("BTC").deposit(0.5)
        portfolio.add_currency("EUR").deposit(100)

        calls = []

        def rate_side_effect(source, target):
            calls.append((source, target))
            return {"BTC": 60000.0, "EUR": 1.2}[source]

        output = io.StringIO()

        with (
            patch(
                "valutatrade_hub.cli.interface.show_portfolio",
                return_value=portfolio,
            ),
            patch(
                "valutatrade_hub.cli.interface.get_rate",
                side_effect=rate_side_effect,
            ),
            redirect_stdout(output),
        ):
            _print_portfolio(1, "alice", "USD")

        self.assertEqual(sorted(calls), [("BTC", "USD"), ("EUR", "USD")])
        self.assertIn("30,120.00 USD", output.getvalue())

    def test_zero_balance_does_not_need_rate(self):
        portfolio = Portfolio(1)
        portfolio.add_currency("BTC")

        output = io.StringIO()

        with (
            patch(
                "valutatrade_hub.cli.interface.show_portfolio",
                return_value=portfolio,
            ),
            patch(
                "valutatrade_hub.cli.interface.get_rate",
            ) as get_rate_mock,
            redirect_stdout(output),
        ):
            _print_portfolio(1, "alice", "USD")

        get_rate_mock.assert_not_called()
        self.assertIn("0.00 USD", output.getvalue())


if __name__ == "__main__":
    unittest.main()
