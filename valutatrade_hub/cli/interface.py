"""Консольный интерфейс приложения ValutaTrade Hub."""

import shlex
from getpass import getpass

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    buy,
    get_rate,
    login,
    register,
    sell,
    show_portfolio,
    show_rates,
)
from valutatrade_hub.core.utils import convert_currency
from valutatrade_hub.logging_config import parser_console_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage, _parse_timestamp
from valutatrade_hub.parser_service.updater import RatesUpdater

HELP_TEXT = """
Доступные команды:
  register --username NAME --password PASSWORD
  login --username NAME --password PASSWORD
  logout
  whoami
  show-portfolio [--base CODE]
  buy --currency CODE --amount NUMBER
  sell --currency CODE --amount NUMBER
  get-rate --from CODE --to CODE
  update-rates [--source coingecko|exchangerate]
  show-rates [--currency CODE] [--top N] [--base CODE]
  help
  exit

Команды также поддерживают интерактивный ввод без аргументов.
Для просмотра справки по команде: help <команда>.
"""


COMMAND_OPTIONS = {
    "register": {"--username", "--password"},
    "login": {"--username", "--password"},
    "show-portfolio": {"--base"},
    "buy": {"--currency", "--amount"},
    "sell": {"--currency", "--amount"},
    "get-rate": {"--from", "--to"},
    "update-rates": {"--source"},
    "show-rates": {"--currency", "--top", "--base"},
}


def _parse_options(args: list[str], allowed: set[str]) -> dict[str, str]:
    """Разбирает именованные аргументы и проверяет их корректность."""
    if len(args) % 2:
        raise ValueError("Каждому аргументу необходимо передать значение")

    options = {}

    for index in range(0, len(args), 2):
        name = args[index]
        value = args[index + 1]

        if name not in allowed:
            raise ValueError(f"Неизвестный аргумент: {name}")

        if name in options:
            raise ValueError(f"Аргумент {name} указан повторно")

        if value.startswith("--"):
            raise ValueError(f"Не указано значение аргумента {name}")

        options[name] = value

    return options


def _get_value(
    options: dict[str, str],
    name: str,
    prompt: str,
    *,
    password: bool = False,
) -> str:
    """Получает аргумент команды или запрашивает его интерактивно."""
    if name in options:
        return options[name]

    if password:
        return getpass(prompt)

    return input(prompt).strip()


def _print_portfolio(user_id: int, username: str, base: str) -> None:
    """Показывает кошельки и стоимость портфеля в выбранной валюте."""
    base_code = get_currency(base).code
    portfolio = show_portfolio(user_id)

    print(f"\nПортфель пользователя '{username}' (база: {base_code})")

    if not portfolio.wallets:
        print("Ваш портфель пока пуст.")
        return

    rates = _get_portfolio_rates(portfolio, base_code)

    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс", f"Стоимость ({base_code})"]

    for code, wallet in sorted(portfolio.wallets.items()):
        if wallet.balance == 0:
            value = 0.0
        else:
            value = convert_currency(
                wallet.balance,
                code,
                base_code,
                rates,
            )

        table.add_row(
            [
                code,
                f"{wallet.balance:.8f}",
                f"{value:,.2f}",
            ]
        )

    print(table)

    total = portfolio.get_total_value(
        base_currency=base_code,
        rates=rates,
    )

    print(f"ИТОГО: {total:,.2f} {base_code}")


def _get_portfolio_rates(portfolio, base_code: str) -> dict[str, float]:
    """Получает необходимые курсы к USD для оценки портфеля."""
    codes = {code for code, wallet in portfolio.wallets.items() if wallet.balance > 0}
    codes.add(base_code)

    return {
        f"{code}_USD": get_rate(code, "USD") for code in sorted(codes) if code != "USD"
    }


def _rate_updated_at(source: str, target: str) -> str | None:
    """Возвращает время самого старого курса, участвующего в расчёте."""
    if source == target:
        return None

    pairs = RatesStorage().load_rates()["pairs"]
    timestamps = []

    for code in (source, target):
        if code == "USD":
            continue

        details = pairs.get(f"{code}_USD")

        if not isinstance(details, dict):
            return None

        try:
            timestamps.append(_parse_timestamp(details["updated_at"]))
        except (KeyError, TypeError, ValueError):
            return None

    if not timestamps:
        return None

    oldest = min(timestamps)
    return oldest.strftime("%Y-%m-%d %H:%M:%S UTC")


def _print_rate(source: str, target: str) -> None:
    """Выводит прямой и обратный курсы с временем обновления."""
    source_code = get_currency(source).code
    target_code = get_currency(target).code

    rate = get_rate(source_code, target_code)
    reverse = 1 / rate
    updated_at = _rate_updated_at(source_code, target_code)

    timestamp = f" (обновлено: {updated_at})" if updated_at else ""

    print(f"Курс {source_code}→{target_code}: {rate:.12g}{timestamp}")
    print(f"Обратный курс {target_code}→{source_code}: {reverse:.12g}")


def run() -> None:
    """Запускает интерактивный интерфейс приложения."""
    current_user = None

    print("\n*** ValutaTrade Hub ***")
    print("Введите help для просмотра доступных команд.")

    while True:
        try:
            line = input("\nvalutatrade> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break

        if not line:
            continue

        try:
            parts = shlex.split(line)
            command = parts[0].lower()
            args = parts[1:]

            if command in {"exit", "quit"}:
                if args:
                    raise ValueError("Команда exit не принимает аргументы")
                print("До свидания!")
                break

            if command == "help":
                if len(args) > 1:
                    raise ValueError("Укажите не более одной команды")
                if args and args[0] not in COMMAND_OPTIONS:
                    raise ValueError(f"Неизвестная команда: {args[0]}")
                if args:
                    print(f"\n{args[0]}: {sorted(COMMAND_OPTIONS[args[0]])}")
                else:
                    print(HELP_TEXT)
                continue

            if command in {"logout", "whoami"}:
                if args:
                    raise ValueError(f"Команда {command} не принимает аргументы")

                if current_user is None:
                    print("Вы ещё не авторизованы.")
                elif command == "logout":
                    current_user = None
                    print("Вы вышли из учётной записи.")
                else:
                    print(
                        f"Пользователь: {current_user.username} "
                        f"(ID: {current_user.user_id})"
                    )
                continue

            if command not in COMMAND_OPTIONS:
                print(f"Неизвестная команда: {command}. Введите help.")
                continue

            options = _parse_options(args, COMMAND_OPTIONS[command])

            if command in {"register", "login"}:
                username = _get_value(options, "--username", "Имя пользователя: ")
                password = _get_value(options, "--password", "Пароль: ", password=True)

                if command == "register":
                    user = register(username, password)
                    print(f"Пользователь '{user.username}' успешно зарегистрирован.")
                    print("Для входа выполните команду login.")
                else:
                    current_user = login(username, password)
                    print(f"Вы вошли как {current_user.username}.")
                continue

            if command in {"show-portfolio", "buy", "sell"}:
                if current_user is None:
                    print("Для выполнения команды необходимо авторизоваться.")
                    continue

                if command == "show-portfolio":
                    base = options.get("--base", "USD")
                    _print_portfolio(
                        current_user.user_id,
                        current_user.username,
                        base,
                    )
                    continue

                currency_code = _get_value(
                    options, "--currency", "Код валюты: "
                ).upper()
                amount = float(_get_value(options, "--amount", "Количество: "))

                if command == "buy":
                    portfolio = buy(current_user.user_id, currency_code, amount)
                    action = "Куплено"
                else:
                    portfolio = sell(current_user.user_id, currency_code, amount)
                    action = "Продано"

                balance = portfolio.get_wallet(currency_code).balance
                print(f"{action}: {amount:g} {currency_code}.")
                print(f"Текущий баланс: {balance:g} {currency_code}.")

                try:
                    rate = get_rate(currency_code, "USD")
                except (ValueError, TypeError, ApiRequestError):
                    print(
                        "Оценочная стоимость в USD недоступна: нет актуального курса."
                    )
                else:
                    description = (
                        "Оценочная стоимость покупки"
                        if command == "buy"
                        else "Оценочная выручка"
                    )
                    print(f"{description}: {amount * rate:,.2f} USD")
                continue

            if command == "show-rates":
                currency = options.get("--currency")
                base = options.get("--base", "USD")
                top_value = options.get("--top")

                if top_value is not None:
                    try:
                        top = int(top_value)
                    except ValueError as exc:
                        raise ValueError(
                            "'top' должен быть положительным целым числом"
                        ) from exc
                else:
                    top = None

                rows, last_refresh = show_rates(
                    currency_code=currency,
                    top=top,
                    base_currency=base,
                )

                print(f"Курсы из кеша (обновлено: {last_refresh or '—'}):")

                table = PrettyTable()
                table.field_names = ["Пара", "Курс", "Обновлено", "Источник"]

                for row in rows:
                    table.add_row(
                        [
                            row["pair"],
                            f"{row['rate']:.12g}",
                            row["updated_at"],
                            row["source"],
                        ]
                    )

                print(table)
                continue

            if command == "update-rates":
                source = options.get("--source", "all").lower()

                source_clients = {
                    "coingecko": CoinGeckoClient,
                    "exchangerate": ExchangeRateApiClient,
                }

                if source != "all" and source not in source_clients:
                    raise ValueError(
                        "Неизвестный источник. Используйте coingecko или exchangerate"
                    )

                clients = (
                    [CoinGeckoClient(), ExchangeRateApiClient()]
                    if source == "all"
                    else [source_clients[source]()]
                )

                with parser_console_logging():
                    result = RatesUpdater(clients=clients).run_update()

                if result.errors:
                    print(
                        "Обновление завершено с ошибками. "
                        "Подробности в logs/parser.log."
                    )
                else:
                    print("Обновление успешно завершено.")

                print(f"Получено курсов: {result.fetched_count}")
                print(f"Сохранено курсов: {result.saved_count}")
                print(f"Последнее обновление: {result.last_refresh}")
                continue

            if command == "get-rate":
                source = _get_value(options, "--from", "Исходная валюта: ")
                target = _get_value(options, "--to", "Целевая валюта: ")
                _print_rate(source, target)

        except InsufficientFundsError as exc:
            print(f"Ошибка: {exc}")
        except CurrencyNotFoundError as exc:
            print(f"Ошибка: Неизвестная валюта. {exc}")
        except ApiRequestError as exc:
            print(f"Ошибка: {exc}. Повторите попытку позже.")
        except (ValueError, TypeError) as exc:
            print(f"Ошибка: {exc}")
        except (EOFError, KeyboardInterrupt):
            print("\nОперация отменена.")
        except Exception:
            print("Ошибка: Внутренняя ошибка приложения. Повторите попытку позже.")
