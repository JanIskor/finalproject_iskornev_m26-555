"""Модели предметной области ValutaTrade Hub."""

import hashlib
import hmac
import secrets
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

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        """Вычисляет защищённый хеш пароля с индивидуальной солью."""
        if not isinstance(password, str):
            raise TypeError("Пароль должен быть строкой")

        if len(password) < 4:
            raise ValueError("Пароль должен содержать минимум 4 символа")

        salt_bytes = bytes.fromhex(salt)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_bytes,
            200_000,
        )
        return password_hash.hex()

    @classmethod
    def create(cls, user_id: int, username: str, password: str) -> "User":
        """Создаёт пользователя с безопасно сохранённым паролем."""
        salt = secrets.token_hex(16)
        hashed_password = cls.hash_password(password, salt)

        return cls(
            user_id=user_id,
            username=username,
            hashed_password=hashed_password,
            salt=salt,
        )

    def verify_password(self, password: str) -> bool:
        """Проверяет соответствие пароля сохранённому хешу."""
        if not isinstance(password, str):
            return False

        try:
            candidate_hash = self.hash_password(password, self._salt)
        except ValueError:
            return False

        return hmac.compare_digest(candidate_hash, self._hashed_password)

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль и генерирует новую индивидуальную соль."""
        new_salt = secrets.token_hex(16)
        new_hash = self.hash_password(new_password, new_salt)

        self._salt = new_salt
        self._hashed_password = new_hash
