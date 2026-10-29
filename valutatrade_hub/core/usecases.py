"""Бизнес-операции приложения ValutaTrade Hub."""

from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.infra.database import DatabaseManager


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
            return Portfolio.from_dict(portfolio_data)

    raise ValueError(f"Портфель пользователя с ID {user_id} не найден")
