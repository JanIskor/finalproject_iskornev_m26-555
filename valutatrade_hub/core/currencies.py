import math
from abc import ABC, abstractmethod


class Currency(ABC):
    """Абстрактная базовая модель валюты."""

    def __init__(self, code: str, name: str) -> None:
        if not isinstance(code, str):
            raise TypeError("Код валюты должен быть строкой")

        code = code.strip().upper()

        if not 2 <= len(code) <= 5 or not code.isascii() or not code.isalpha():
            raise ValueError("Код валюты должен содержать от 2 до 5 латинских букв")

        if not isinstance(name, str):
            raise TypeError("Название валюты должно быть строкой")

        name = name.strip()

        if not name:
            raise ValueError("Название валюты не может быть пустым")

        self._code = code
        self._name = name

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def get_info(self) -> dict:
        """Вернуть информацию о валюте."""


class FiatCurrency(Currency):
    """Модель фиатной валюты."""

    def __init__(self, code: str, name: str, country: str) -> None:
        super().__init__(code, name)

        if not isinstance(country, str):
            raise TypeError("Страна должна быть строкой")

        country = country.strip()

        if not country:
            raise ValueError("Страна не может быть пустой")

        self._country = country

    @property
    def country(self) -> str:
        return self._country

    def get_info(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "type": "fiat",
            "country": self.country,
        }


class CryptoCurrency(Currency):
    """Модель криптовалюты."""

    def __init__(
        self,
        code: str,
        name: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        super().__init__(code, name)

        if not isinstance(algorithm, str):
            raise TypeError("Алгоритм должен быть строкой")

        algorithm = algorithm.strip()

        if not algorithm:
            raise ValueError("Алгоритм не может быть пустым")

        if isinstance(market_cap, bool) or not isinstance(market_cap, (int, float)):
            raise TypeError("Рыночная капитализация должна быть числом")

        if not math.isfinite(market_cap) or market_cap < 0:
            raise ValueError(
                "Рыночная капитализация должна быть конечным неотрицательным числом"
            )

        self._algorithm = algorithm
        self._market_cap = float(market_cap)

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @property
    def market_cap(self) -> float:
        return self._market_cap

    def get_info(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "type": "crypto",
            "algorithm": self.algorithm,
            "market_cap": self.market_cap,
        }
