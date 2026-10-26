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

    def to_dict(self) -> dict:
        """Преобразует пользователя в словарь для сохранения."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Восстанавливает пользователя из сохранённого словаря."""
        if not isinstance(data, dict):
            raise TypeError("Данные пользователя должны быть словарём")

        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )


class Wallet:
    """Представляет кошелёк с балансом одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        """Создаёт кошелёк и проверяет начальный баланс."""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        code = currency_code.strip().upper()

        if not 2 <= len(code) <= 5 or not code.isascii() or not code.isalpha():
            raise ValueError("Код валюты должен содержать 2–5 латинских букв")

        self._currency_code = code
        self._balance = 0.0
        self.balance = balance

    @property
    def currency_code(self) -> str:
        """Возвращает код валюты."""
        return self._currency_code

    @property
    def balance(self) -> float:
        """Возвращает текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Устанавливает неотрицательный конечный баланс."""
        import math

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")

        if not math.isfinite(value):
            raise ValueError("Баланс должен быть конечным числом")

        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = float(value)

    @staticmethod
    def _validate_amount(amount: float) -> None:
        """Проверяет корректность суммы операции."""
        import math

        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма операции должна быть числом")

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма операции должна быть положительной и конечной")

    def deposit(self, amount: float) -> None:
        """Пополняет баланс кошелька."""
        self._validate_amount(amount)
        self.balance = self._balance + amount

    def withdraw(self, amount: float) -> None:
        """Списывает средства, если баланс достаточен."""
        from valutatrade_hub.core.exceptions import InsufficientFundsError

        self._validate_amount(amount)

        if amount > self._balance:
            raise InsufficientFundsError(
                f"Недостаточно {self._currency_code}: "
                f"доступно {self._balance}, требуется {amount}"
            )

        self.balance = self._balance - amount

    def get_balance_info(self) -> dict:
        """Возвращает код валюты и текущий баланс."""
        return {
            "currency_code": self._currency_code,
            "balance": self._balance,
        }

    def to_dict(self) -> dict:
        """Преобразует кошелёк в словарь для сохранения."""
        return self.get_balance_info()

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        """Восстанавливает кошелёк из сохранённых данных."""
        if not isinstance(data, dict):
            raise TypeError("Данные кошелька должны быть словарём")

        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"],
        )


class Portfolio:
    """Портфель валютных кошельков одного пользователя."""

    def __init__(self, user_id: int, user: User | None = None):
        """Создаёт портфель и при необходимости связывает его с пользователем."""
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise TypeError("Идентификатор пользователя должен быть целым числом")

        if user_id <= 0:
            raise ValueError("Идентификатор пользователя должен быть положительным")

        if user is not None:
            if not isinstance(user, User):
                raise TypeError("Пользователь должен быть объектом User")

            if user.user_id != user_id:
                raise ValueError(
                    "Идентификатор пользователя не совпадает с владельцем портфеля"
                )

        self._user_id = user_id
        self._user = user
        self._wallets: dict[str, Wallet] = {}

    @property
    def user_id(self) -> int:
        """Возвращает идентификатор владельца портфеля."""
        return self._user_id

    @property
    def user(self) -> User | None:
        """Возвращает пользователя, связанного с портфелем."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает копию словаря валютных кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет валютный кошелёк или возвращает существующий."""
        wallet = Wallet(currency_code)
        code = wallet.currency_code

        if code not in self._wallets:
            self._wallets[code] = wallet

        return self._wallets[code]

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает кошелёк указанной валюты."""
        if not isinstance(currency_code, str):
            raise TypeError("Код валюты должен быть строкой")

        code = currency_code.strip().upper()

        if code not in self._wallets:
            raise ValueError(f"Валюта {code} отсутствует в портфеле")

        return self._wallets[code]

    def get_total_value(
        self,
        base_currency: str = "USD",
        rates: dict[str, float] | None = None,
    ) -> float:
        """Рассчитывает общую стоимость портфеля в выбранной валюте."""
        import math

        if not isinstance(base_currency, str):
            raise TypeError("Базовая валюта должна быть строкой")

        base = base_currency.strip().upper()

        if not 2 <= len(base) <= 5 or not base.isascii() or not base.isalpha():
            raise ValueError("Некорректный код базовой валюты")

        if rates is None:
            rates = {"USD_USD": 1.0}

        if not isinstance(rates, dict):
            raise TypeError("Курсы валют должны быть словарём")

        def usd_rate(code: str) -> float:
            if code == "USD":
                return 1.0

            pair = f"{code}_USD"

            if pair not in rates:
                raise ValueError(f"Отсутствует курс валютной пары {pair}")

            rate = rates[pair]

            if isinstance(rate, bool) or not isinstance(rate, (int, float)):
                raise TypeError(f"Курс {pair} должен быть числом")

            if not math.isfinite(rate) or rate <= 0:
                raise ValueError(f"Курс {pair} должен быть положительным")

            return float(rate)

        total_usd = 0.0

        for wallet in self._wallets.values():
            if wallet.balance == 0:
                continue

            total_usd += wallet.balance * usd_rate(wallet.currency_code)

        if not math.isfinite(total_usd):
            raise ValueError("Стоимость портфеля превышает допустимый диапазон")

        result = total_usd / usd_rate(base)

        if not math.isfinite(result):
            raise ValueError("Результат конвертации превышает допустимый диапазон")

        return result

    def to_dict(self) -> dict:
        """Преобразует портфель в словарь для сохранения."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: {"balance": wallet.balance}
                for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        user: User | None = None,
    ) -> "Portfolio":
        """Восстанавливает портфель и связывает его с пользователем."""
        if not isinstance(data, dict):
            raise TypeError("Данные портфеля должны быть словарём")

        wallets_data = data["wallets"]

        if not isinstance(wallets_data, dict):
            raise TypeError("Кошельки должны быть представлены словарём")

        portfolio = cls(user_id=data["user_id"], user=user)

        for code, wallet_data in wallets_data.items():
            if not isinstance(wallet_data, dict):
                raise TypeError("Данные кошелька должны быть словарём")

            wallet = Wallet.from_dict(
                {
                    "currency_code": code,
                    "balance": wallet_data["balance"],
                }
            )

            if wallet.currency_code in portfolio._wallets:
                raise ValueError(f"Повторяющийся код валюты {wallet.currency_code}")

            portfolio._wallets[wallet.currency_code] = wallet

        return portfolio
