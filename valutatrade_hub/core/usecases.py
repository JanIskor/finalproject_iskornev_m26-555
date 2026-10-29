"""Бизнес-операции приложения ValutaTrade Hub."""

from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import convert_currency
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager


@log_action
def register(
    username: str,
    password: str,
    db: DatabaseManager | None = None,
) -> User:
    """Регистрирует пользователя и создаёт для него пустой портфель."""
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")

    username = username.strip()
    database = db if db is not None else DatabaseManager()

    users_data = database.load_users()

    if any(user["username"].casefold() == username.casefold() for user in users_data):
        raise ValueError(f"Пользователь '{username}' уже существует")

    new_user_id = (
        max(
            (user["user_id"] for user in users_data),
            default=0,
        )
        + 1
    )

    user = User.create(
        user_id=new_user_id,
        username=username,
        password=password,
    )

    portfolio = Portfolio(user_id=user.user_id, user=user)

    portfolios_data = database.load_portfolios()

    updated_users = [*users_data, user.to_dict()]
    updated_portfolios = [*portfolios_data, portfolio.to_dict()]

    database.save_users(updated_users)

    try:
        database.save_portfolios(updated_portfolios)
    except Exception:
        database.save_users(users_data)
        raise

    return user


@log_action
def login(
    username: str,
    password: str,
    db: DatabaseManager | None = None,
) -> User:
    """Авторизует пользователя по имени и паролю."""
    error_message = "Неверное имя пользователя или пароль"

    if not isinstance(username, str) or not isinstance(password, str):
        raise ValueError(error_message)

    normalized_username = username.strip().casefold()
    database = db if db is not None else DatabaseManager()

    for user_data in database.load_users():
        if user_data["username"].casefold() != normalized_username:
            continue

        user = User.from_dict(user_data)

        if user.verify_password(password):
            return user

        break

    raise ValueError(error_message)


@log_action
def show_portfolio(
    user_id: int,
    db: DatabaseManager | None = None,
) -> Portfolio:
    """Загружает валютный портфель указанного пользователя."""
    if isinstance(user_id, bool) or not isinstance(user_id, int):
        raise TypeError("Идентификатор пользователя должен быть целым числом")

    if user_id <= 0:
        raise ValueError("Идентификатор пользователя должен быть положительным")

    database = db if db is not None else DatabaseManager()

    for portfolio_data in database.load_portfolios():
        if portfolio_data["user_id"] == user_id:
            user_data = next(
                (item for item in database.load_users() if item["user_id"] == user_id),
                None,
            )

            if user_data is None:
                raise ValueError(f"Пользователь с ID {user_id} не найден")

            user = User.from_dict(user_data)
            return Portfolio.from_dict(portfolio_data, user=user)

    raise ValueError(f"Портфель пользователя с ID {user_id} не найден")


@log_action(verbose=True)
def buy(
    user_id: int,
    currency_code: str,
    amount: float,
    db: DatabaseManager | None = None,
) -> Portfolio:
    """Покупает валюту, увеличивая баланс кошелька пользователя."""
    from valutatrade_hub.core.currencies import get_currency

    currency = get_currency(currency_code)
    database = db if db is not None else DatabaseManager()

    portfolio = show_portfolio(user_id, db=database)
    wallet = portfolio.add_currency(currency.code)
    wallet.deposit(amount)

    portfolios_data = database.load_portfolios()

    for index, portfolio_data in enumerate(portfolios_data):
        if portfolio_data["user_id"] == user_id:
            portfolios_data[index] = portfolio.to_dict()
            database.save_portfolios(portfolios_data)
            return portfolio

    raise ValueError(f"Портфель пользователя с ID {user_id} не найден")


@log_action(verbose=True)
def sell(
    user_id: int,
    currency_code: str,
    amount: float,
    db: DatabaseManager | None = None,
) -> Portfolio:
    """Продаёт валюту, уменьшая баланс кошелька пользователя."""
    from valutatrade_hub.core.currencies import get_currency

    currency = get_currency(currency_code)
    database = db if db is not None else DatabaseManager()

    portfolio = show_portfolio(user_id, db=database)
    wallet = portfolio.get_wallet(currency.code)
    wallet.withdraw(amount)

    portfolios_data = database.load_portfolios()

    for index, portfolio_data in enumerate(portfolios_data):
        if portfolio_data["user_id"] == user_id:
            portfolios_data[index] = portfolio.to_dict()
            database.save_portfolios(portfolios_data)
            return portfolio

    raise ValueError(f"Портфель пользователя с ID {user_id} не найден")


def _load_rates(
    required_currencies: tuple[str, ...] = (),
) -> dict[str, float]:
    """Загружает курсы, обновляя отсутствующие или устаревшие пары."""
    from datetime import datetime, timezone

    from valutatrade_hub.core.currencies import CryptoCurrency, get_currency
    from valutatrade_hub.core.exceptions import ApiRequestError
    from valutatrade_hub.infra.settings import SettingsLoader
    from valutatrade_hub.parser_service.api_clients import (
        CoinGeckoClient,
        ExchangeRateApiClient,
    )
    from valutatrade_hub.parser_service.storage import RatesStorage, _parse_timestamp
    from valutatrade_hub.parser_service.updater import RatesUpdater

    settings = SettingsLoader()
    storage = RatesStorage()
    data = storage.load_rates()
    now = datetime.now(timezone.utc)

    required_pairs = {f"{code}_USD" for code in required_currencies if code != "USD"}

    stale_pairs = set()

    for pair in required_pairs:
        details = data["pairs"].get(pair)

        if not isinstance(details, dict):
            stale_pairs.add(pair)
            continue

        try:
            timestamp = _parse_timestamp(details["updated_at"])
            age = (now - timestamp).total_seconds()
            if age < 0 or age > settings.rates_ttl_seconds:
                stale_pairs.add(pair)
        except (KeyError, TypeError, ValueError):
            stale_pairs.add(pair)

    if stale_pairs:
        clients = []

        for pair in sorted(stale_pairs):
            code = pair.removesuffix("_USD")
            currency = get_currency(code)

            if isinstance(currency, CryptoCurrency):
                if not any(isinstance(c, CoinGeckoClient) for c in clients):
                    clients.append(CoinGeckoClient())
            else:
                if not any(isinstance(c, ExchangeRateApiClient) for c in clients):
                    clients.append(ExchangeRateApiClient())

        try:
            RatesUpdater(clients=clients, storage=storage).run_update()
        except ApiRequestError:
            pass

        data = storage.load_rates()

        for pair in stale_pairs:
            details = data["pairs"].get(pair)

            if not isinstance(details, dict):
                raise ApiRequestError(
                    f"Не удалось получить актуальный курс {pair}",
                    source="RatesUpdater",
                )

            try:
                timestamp = _parse_timestamp(details["updated_at"])
                age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            except (KeyError, TypeError, ValueError) as exc:
                raise ApiRequestError(
                    f"Некорректная временная метка курса {pair}",
                    source="RatesUpdater",
                ) from exc

            if age < 0 or age > settings.rates_ttl_seconds:
                raise ApiRequestError(
                    f"Не удалось обновить устаревший курс {pair}",
                    source="RatesUpdater",
                )

    rates = {}

    for pair, details in data["pairs"].items():
        if not isinstance(details, dict) or "rate" not in details:
            raise ValueError(f"Некорректные данные валютной пары {pair}")

        rates[pair] = details["rate"]

    return rates


@log_action
def get_rate(
    from_currency: str,
    to_currency: str,
    rates: dict[str, float] | None = None,
) -> float:
    """Рассчитывает валютный курс через котировки относительно USD."""

    from valutatrade_hub.core.currencies import get_currency

    source = get_currency(from_currency).code
    target = get_currency(to_currency).code

    if source == target:
        return 1.0

    if rates is None:
        rates = _load_rates((source, target))

    if not isinstance(rates, dict):
        raise TypeError("Курсы валют должны быть словарём")

    result = convert_currency(1.0, source, target, rates)

    if result <= 0:
        raise ValueError("Не удалось рассчитать корректный валютный курс")

    return result


def show_rates(
    currency_code: str | None = None,
    top: int | None = None,
    base_currency: str = "USD",
) -> tuple[list[dict[str, object]], str | None]:
    """Возвращает курсы из кеша с фильтрацией и пересчётом базовой валюты."""
    import json
    import math

    from valutatrade_hub.core.currencies import CryptoCurrency, get_currency
    from valutatrade_hub.infra.settings import SettingsLoader

    base = get_currency(base_currency).code

    if currency_code is not None:
        currency_code = get_currency(currency_code).code

    if top is not None:
        if isinstance(top, bool) or not isinstance(top, int) or top <= 0:
            raise ValueError("'top' должен быть положительным целым числом")

    rates_file = SettingsLoader().rates_file

    try:
        with rates_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Не удалось прочитать кеш курсов: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Некорректный формат кеша курсов")

    pairs = data.get("pairs", {})

    if not isinstance(pairs, dict):
        raise ValueError("Некорректный формат валютных пар в кеше")

    if not pairs:
        raise ValueError(
            "Локальный кеш курсов пуст. Выполните 'update-rates', "
            "чтобы загрузить данные."
        )

    rates = {}

    for pair, details in pairs.items():
        if not isinstance(details, dict):
            raise ValueError(f"Некорректные данные для пары {pair}")

        value = details.get("rate")

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"Некорректный курс валютной пары {pair}")

        rates[pair] = float(value)

    if base != "USD" and f"{base}_USD" not in rates:
        raise ValueError(f"В кеше отсутствует курс {base}_USD")

    base_rate = get_rate(base, "USD", rates=rates)

    rows = []

    for pair, details in pairs.items():
        if not pair.endswith("_USD"):
            continue

        code = pair.removesuffix("_USD")

        try:
            currency = get_currency(code)
        except Exception:
            continue

        if currency_code is not None and code != currency_code:
            continue

        if top is not None and not isinstance(currency, CryptoCurrency):
            continue

        rows.append(
            {
                "pair": f"{code}_{base}",
                "rate": rates[pair] / base_rate,
                "updated_at": details.get("updated_at", "—"),
                "source": details.get("source", "—"),
                "usd_rate": rates[pair],
            }
        )

    if currency_code is not None and not rows:
        raise ValueError(f"Курс для '{currency_code}' не найден в кеше")

    if top is not None:
        rows.sort(key=lambda row: row["usd_rate"], reverse=True)
        rows = rows[:top]
    else:
        rows.sort(key=lambda row: row["pair"])

    for row in rows:
        del row["usd_rate"]

    return rows, data.get("last_refresh")
