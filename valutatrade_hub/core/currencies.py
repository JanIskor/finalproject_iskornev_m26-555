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
