"""Оркестрация обновления валютных курсов."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage

logger = logging.getLogger("valutatrade_hub.parser")


@dataclass(frozen=True)
class UpdateResult:
    """Результат обновления валютных курсов."""

    fetched_count: int
    saved_count: int
    last_refresh: str | None
    errors: tuple[str, ...]


class RatesUpdater:
    """Получает курсы из API и сохраняет успешные обновления."""

    def __init__(
        self,
        clients: list | None = None,
        storage: RatesStorage | None = None,
    ) -> None:
        self.clients = (
            clients
            if clients is not None
            else [CoinGeckoClient(), ExchangeRateApiClient()]
        )
        self.storage = storage if storage is not None else RatesStorage()

    def run_update(self) -> UpdateResult:
        """Обновляет курсы, сохраняя результаты доступных источников."""
        successful = []
        errors = []
        fetched_count = 0

        for client in self.clients:
            source = type(client).__name__

            try:
                rates = client.fetch_rates()

                if not rates:
                    raise ApiRequestError(
                        "Источник вернул пустой набор курсов",
                        source=source,
                    )

                successful.append((source, rates))
                fetched_count += len(rates)
                logger.info(
                    "Источник %s: получено %d курсов",
                    source,
                    len(rates),
                )
            except Exception as exc:
                message = (
                    str(exc)
                    if isinstance(exc, ApiRequestError)
                    else f"{source}: ошибка получения курсов"
                )
                errors.append(message)
                logger.exception("Ошибка обновления источника %s", source)

        if not successful:
            logger.error("Не удалось получить курсы ни от одного источника")
            raise ApiRequestError(
                "Все источники валютных курсов недоступны",
                source="RatesUpdater",
            )

        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        saved_count = 0

        for source, rates in successful:
            saved_count += self.storage.save_rates(
                rates,
                source=source,
                timestamp=timestamp,
            )

        last_refresh = self.storage.load_rates().get("last_refresh")

        logger.info(
            "Обновление завершено: получено=%d, сохранено=%d, ошибок=%d",
            fetched_count,
            saved_count,
            len(errors),
        )

        return UpdateResult(
            fetched_count=fetched_count,
            saved_count=saved_count,
            last_refresh=last_refresh,
            errors=tuple(errors),
        )
