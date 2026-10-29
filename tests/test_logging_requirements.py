"""Проверки логирования бизнес-операций."""

import logging
import unittest

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.decorators import log_action
from valutatrade_hub.logging_config import LOGGER_NAME


class ListHandler(logging.Handler):
    """Собирает записи логгера в память."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class LoggingRequirementsTests(unittest.TestCase):
    """Проверяет корректность и безопасность логирования."""

    def setUp(self):
        self.logger = logging.getLogger(LOGGER_NAME)
        self.old_level = self.logger.level
        self.old_disabled = self.logger.disabled

        self.handler = ListHandler()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)
        self.logger.disabled = False

        self.addCleanup(self.logger.removeHandler, self.handler)
        self.addCleanup(self.logger.setLevel, self.old_level)
        self.addCleanup(setattr, self.logger, "disabled", self.old_disabled)

    def messages(self):
        return [record.getMessage() for record in self.handler.records]

    def test_success_is_logged(self):
        @log_action
        def register(username, password):
            return username

        result = register("alice", "super-secret-password")

        self.assertEqual(result, "alice")

        messages = self.messages()

        self.assertEqual(
            sum("result=OK" in message for message in messages),
            1,
        )
        self.assertTrue(any("action=REGISTER" in message for message in messages))

    def test_error_is_logged_once(self):
        @log_action
        def sell(user_id, currency_code, amount):
            raise InsufficientFundsError("Недостаточно средств")

        with self.assertRaisesRegex(
            InsufficientFundsError,
            "Недостаточно средств",
        ):
            sell(1, "BTC", 2.0)

        errors = [
            record
            for record in self.handler.records
            if "result=ERROR" in record.getMessage()
        ]

        self.assertEqual(len(errors), 1)
        self.assertIn(
            "InsufficientFundsError",
            errors[0].getMessage(),
        )

    def test_password_is_not_logged(self):
        secret = "very-private-password-123"

        @log_action
        def login(username, password):
            raise ValueError("Неверный пароль")

        with self.assertRaises(ValueError):
            login("alice", secret)

        output = "\n".join(self.messages())

        self.assertNotIn(secret, output)
        self.assertNotIn("Неверный пароль", output)
        self.assertIn("result=ERROR", output)

    def test_unexpected_error_is_sanitized(self):
        secret = "private-api-key-123"

        @log_action
        def get_rate(from_currency, to_currency):
            raise RuntimeError(f"API key: {secret}")

        with self.assertRaisesRegex(RuntimeError, secret):
            get_rate("BTC", "USD")

        output = "\n".join(self.messages())

        self.assertNotIn(secret, output)
        self.assertIn("Внутренняя ошибка приложения", output)

    def test_verbose_balance_change(self):
        class Wallet:
            balance = 1.5

        class Portfolio:
            def get_wallet(self, currency_code):
                return Wallet()

        @log_action(verbose=True)
        def buy(user_id, currency_code, amount):
            return Portfolio()

        buy(1, "BTC", 0.5)

        output = "\n".join(self.messages())

        self.assertIn("balance_before=1", output)
        self.assertIn("balance_after=1.5", output)
        self.assertIn("result=OK", output)


if __name__ == "__main__":
    unittest.main()
