"""Консольный интерфейс приложения ValutaTrade Hub."""

from getpass import getpass

from prettytable import PrettyTable

from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    buy,
    login,
    register,
    sell,
    show_portfolio,
)


def run() -> None:
    """Запускает интерактивный интерфейс приложения."""
    current_user = None

    print("\n*** ValutaTrade Hub ***")
    print("Введите help для просмотра доступных команд.")

    while True:
        try:
            command = input("\nvalutatrade> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break

        if not command:
            continue

        if command in {"exit", "quit"}:
            print("До свидания!")
            break

        if command == "help":
            print(
                "\nДоступные команды:\n"
                "  register        Регистрация\n"
                "  login           Авторизация\n"
                "  logout          Выход из учётной записи\n"
                "  whoami          Текущий пользователь\n"
                "  show-portfolio  Просмотр портфеля\n"
                "  buy             Покупка валюты\n"
                "  sell            Продажа валюты\n"
                "  get-rate        Получение курса (скоро)\n"
                "  help            Список команд\n"
                "  exit            Завершение работы"
            )
            continue

        if command == "logout":
            if current_user is None:
                print("Вы ещё не авторизованы.")
            else:
                current_user = None
                print("Вы вышли из учётной записи.")
            continue

        if command == "whoami":
            if current_user is None:
                print("Вы ещё не авторизованы.")
            else:
                print(
                    f"Пользователь: {current_user.username} "
                    f"(ID: {current_user.user_id})"
                )
            continue

        if command in {"register", "login"}:
            try:
                username = input("Имя пользователя: ").strip()
                password = getpass("Пароль: ")

                if command == "register":
                    user = register(username, password)
                    print(f"Пользователь '{user.username}' успешно зарегистрирован.")
                    print("Для входа выполните команду login.")
                else:
                    current_user = login(username, password)
                    print(f"Вы вошли как {current_user.username}.")

            except (
                ValueError,
                TypeError,
                CurrencyNotFoundError,
                InsufficientFundsError,
            ) as exc:
                print(f"Ошибка: {exc}")
            except (EOFError, KeyboardInterrupt):
                print("\nОперация отменена.")

            continue

        if command in {"show-portfolio", "buy", "sell"}:
            if current_user is None:
                print("Для выполнения команды необходимо авторизоваться.")
                continue

            try:
                if command == "show-portfolio":
                    portfolio = show_portfolio(current_user.user_id)

                    if not portfolio.wallets:
                        print("Ваш портфель пока пуст.")
                        continue

                    table = PrettyTable()
                    table.field_names = ["Валюта", "Баланс"]

                    for code, wallet in sorted(portfolio.wallets.items()):
                        table.add_row([code, f"{wallet.balance:.8f}"])

                    print(table)
                    continue

                currency_code = input("Код валюты: ").strip().upper()
                amount = float(input("Количество: ").strip())

                if command == "buy":
                    portfolio = buy(
                        current_user.user_id,
                        currency_code,
                        amount,
                    )
                    action = "Куплено"
                else:
                    portfolio = sell(
                        current_user.user_id,
                        currency_code,
                        amount,
                    )
                    action = "Продано"

                balance = portfolio.get_wallet(currency_code).balance

                print(f"{action}: {amount:g} {currency_code}.")
                print(f"Текущий баланс: {balance:g} {currency_code}.")

            except (ValueError, TypeError) as exc:
                print(f"Ошибка: {exc}")
            except (EOFError, KeyboardInterrupt):
                print("\\nОперация отменена.")

            continue

        print(f"Неизвестная команда: {command}. Введите help.")
