"""Модели предметной области ValutaTrade Hub."""

from datetime import datetime, timezone


class User:
    """Представляет зарегистрированного пользователя приложения."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime | None = None,
    ) -> None:
        """Создаёт пользователя и проверяет корректность его данных."""
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise TypeError("Идентификатор пользователя должен быть целым числом")

        if user_id <= 0:
            raise ValueError("Идентификатор пользователя должен быть положительным")

        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        if not isinstance(hashed_password, str):
            raise TypeError("Хеш пароля должен быть строкой")

        if not isinstance(salt, str):
            raise TypeError("Соль пароля должна быть строкой")

        if registration_date is None:
            registration_date = datetime.now(timezone.utc)

        if not isinstance(registration_date, datetime):
            raise TypeError("Дата регистрации должна иметь тип datetime")

        if registration_date.tzinfo is None:
            raise ValueError("Дата регистрации должна содержать часовой пояс")

        self._user_id = user_id
        self._username = username.strip()
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Возвращает идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Возвращает имя пользователя."""
        return self._username

    @property
    def hashed_password(self) -> str:
        """Возвращает хеш пароля."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Возвращает соль пароля."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Возвращает дату регистрации."""
        return self._registration_date

    def get_user_info(self) -> dict:
        """Возвращает публичные сведения без пароля и соли."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }
