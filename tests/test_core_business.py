"""Проверки моделей и бизнес-операций Core Service."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.usecases import buy, login, register, sell, show_portfolio
from valutatrade_hub.core.utils import convert_currency
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


class UserTests(unittest.TestCase):
    """Проверки пользователя и хранения пароля."""

    def test_password_hash_and_verification(self):
        user = User.create(1, "alice", "secret123")

        self.assertNotEqual(user.hashed_password, "secret123")
        self.assertTrue(user.verify_password("secret123"))
        self.assertFalse(user.verify_password("incorrect"))
        self.assertNotIn("hashed_password", user.get_user_info())
        self.assertNotIn("salt", user.get_user_info())

    def test_password_change(self):
        user = User.create(1, "alice", "secret123")
        old_salt = user.salt

        user.change_password("newsecret")

        self.assertNotEqual(user.salt, old_salt)
        self.assertFalse(user.verify_password("secret123"))
        self.assertTrue(user.verify_password("newsecret"))

    def test_invalid_user_data(self):
        with self.assertRaises(ValueError):
            User.create(1, " ", "secret123")

        with self.assertRaises(ValueError):
            User.create(1, "alice", "123")

    def test_serialization(self):
        user = User.create(1, "alice", "secret123")
        restored = User.from_dict(user.to_dict())

        self.assertEqual(restored.user_id, user.user_id)
        self.assertEqual(restored.registration_date, user.registration_date)
        self.assertTrue(restored.verify_password("secret123"))


class WalletTests(unittest.TestCase):
    """Проверки операций с балансом."""

    def test_deposit_and_withdraw(self):
        wallet = Wallet("btc")
        wallet.deposit(0.5)
        wallet.withdraw(0.2)

        self.assertAlmostEqual(wallet.balance, 0.3)
        self.assertEqual(wallet.currency_code, "BTC")

    def test_insufficient_funds(self):
        wallet = Wallet("USD", 10)

        with self.assertRaises(InsufficientFundsError):
            wallet.withdraw(11)

        self.assertEqual(wallet.balance, 10)

    def test_invalid_amounts(self):
        wallet = Wallet("USD")

        for amount in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(amount=amount):
                with self.assertRaises((TypeError, ValueError)):
                    wallet.deposit(amount)

    def test_invalid_balance(self):
        wallet = Wallet("USD")

        for balance in (-1, float("nan"), float("inf"), "100"):
            with self.subTest(balance=balance):
                with self.assertRaises((TypeError, ValueError)):
                    wallet.balance = balance


class PortfolioTests(unittest.TestCase):
    """Проверки портфеля и конвертации."""

    def test_unique_wallets_and_readonly_user(self):
        user = User.create(1, "alice", "secret123")
        portfolio = Portfolio(1, user=user)

        first = portfolio.add_currency("BTC")
        second = portfolio.add_currency("btc")

        self.assertIs(first, second)
        self.assertIs(portfolio.user, user)

        with self.assertRaises(AttributeError):
            portfolio.user = None

    def test_total_value(self):
        portfolio = Portfolio(1)
        portfolio.add_currency("BTC").deposit(0.5)
        portfolio.add_currency("EUR").deposit(100)

        rates = {"BTC_USD": 60_000, "EUR_USD": 1.2}

        self.assertAlmostEqual(
            portfolio.get_total_value("USD", rates),
            30_120,
        )
        self.assertAlmostEqual(
            portfolio.get_total_value("EUR", rates),
            25_100,
        )

    def test_conversion_and_missing_rate(self):
        rates = {"BTC_USD": 60_000, "EUR_USD": 1.2}

        self.assertAlmostEqual(
            convert_currency(1, "BTC", "EUR", rates),
            50_000,
        )

        with self.assertRaises(ValueError):
            convert_currency(1, "ETH", "USD", rates)

    def test_serialization(self):
        user = User.create(1, "alice", "secret123")
        portfolio = Portfolio(1, user=user)
        portfolio.add_currency("BTC").deposit(0.5)

        restored = Portfolio.from_dict(portfolio.to_dict(), user=user)

        self.assertIs(restored.user, user)
        self.assertEqual(restored.get_wallet("BTC").balance, 0.5)


class BusinessTests(unittest.TestCase):
    """Проверки регистрации, авторизации и торговли."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        settings = SettingsLoader()
        database = DatabaseManager()

        self.users_path = Path(self.temp_dir.name) / "users.json"
        self.portfolios_path = Path(self.temp_dir.name) / "portfolios.json"

        self.users_path.write_text("[]", encoding="utf-8")
        self.portfolios_path.write_text("[]", encoding="utf-8")

        patcher_users = patch.object(settings, "_data_dir", Path(self.temp_dir.name))
        patcher_users.start()
        self.addCleanup(patcher_users.stop)

        self.database = database

    def test_registration_login_and_portfolio_owner(self):
        user = register("alice", "secret123", db=self.database)

        self.assertEqual(
            login("alice", "secret123", db=self.database).user_id, user.user_id
        )

        with self.assertRaises(ValueError):
            register("ALICE", "another123", db=self.database)

        with self.assertRaises(ValueError):
            login("alice", "incorrect", db=self.database)

        portfolio = show_portfolio(user.user_id, db=self.database)

        self.assertIsInstance(portfolio.user, User)
        self.assertEqual(portfolio.user.user_id, user.user_id)

    def test_buy_sell_and_insufficient_funds(self):
        user = register("bob", "secret123", db=self.database)

        bought = buy(user.user_id, "BTC", 0.5, db=self.database)
        self.assertEqual(bought.get_wallet("BTC").balance, 0.5)

        sold = sell(user.user_id, "BTC", 0.2, db=self.database)
        self.assertAlmostEqual(sold.get_wallet("BTC").balance, 0.3)

        with self.assertRaises(InsufficientFundsError):
            sell(user.user_id, "BTC", 1, db=self.database)

        persisted = show_portfolio(user.user_id, db=self.database)
        self.assertAlmostEqual(persisted.get_wallet("BTC").balance, 0.3)


if __name__ == "__main__":
    unittest.main()
