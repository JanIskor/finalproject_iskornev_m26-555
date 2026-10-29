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
