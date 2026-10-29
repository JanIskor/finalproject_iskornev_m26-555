"""Хранение актуальных и исторических валютных курсов."""

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def _parse_timestamp(value: str) -> datetime:
    """Преобразует ISO 8601 в UTC и проверяет наличие часового пояса."""
    if not isinstance(value, str):
        raise ValueError("Временная метка должна быть строкой")

    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Некорректная временная метка") from exc

    if timestamp.tzinfo is None:
        raise ValueError("Временная метка должна содержать часовой пояс")

    return timestamp.astimezone(timezone.utc)


def _utc_timestamp() -> str:
    """Возвращает текущее время в формате ISO 8601 UTC."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, default):
    """Читает JSON, используя значение по умолчанию при отсутствии файла."""
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _atomic_write_json(path: Path, data) -> None:
    """Атомарно заменяет JSON-файл после успешной записи."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


class RatesStorage:
    """Сохраняет котировки и историю их обновлений."""

    def __init__(
        self,
        rates_file: Path | None = None,
        history_file: Path | None = None,
    ) -> None:
        settings = SettingsLoader()
        self.rates_file = rates_file or settings.rates_file
        self.history_file = history_file or settings.exchange_rates_file

    def load_rates(self) -> dict:
        """Возвращает актуальные котировки с метаданными."""
        data = _read_json(
            self.rates_file,
            {"pairs": {}, "last_refresh": None},
        )

        if not isinstance(data, dict) or not isinstance(data.get("pairs"), dict):
            raise ValueError("Некорректная структура rates.json")

        return data

    def load_history(self) -> list[dict]:
        """Возвращает историю котировок."""
        data = _read_json(self.history_file, [])

        if not isinstance(data, list):
            raise ValueError("Некорректная структура exchange_rates.json")

        return data

    def save_rates(
        self,
        rates: dict[str, float],
        source: str,
        timestamp: str | None = None,
    ) -> int:
        """Сохраняет новые котировки и добавляет записи в историю."""
        if not isinstance(rates, dict):
            raise TypeError("Курсы должны быть словарём")

        if not isinstance(source, str) or not source.strip():
            raise ValueError("Источник курсов должен быть непустой строкой")

        timestamp = timestamp or _utc_timestamp()
        updated_at = _parse_timestamp(timestamp)
        normalized_timestamp = updated_at.isoformat().replace("+00:00", "Z")

        current = self.load_rates()
        history = self.load_history()

        pairs = current["pairs"].copy()
        existing_ids = {record["id"] for record in history}
        new_records = []
        saved_count = 0

        for pair, rate in rates.items():
            if not isinstance(pair, str) or pair.count("_") != 1:
                raise ValueError(f"Некорректная валютная пара: {pair}")

            if (
                isinstance(rate, bool)
                or not isinstance(rate, (int, float))
                or not math.isfinite(rate)
                or rate <= 0
            ):
                raise ValueError(f"Некорректный курс валютной пары {pair}")

            previous = pairs.get(pair)

            if previous is not None:
                previous_timestamp = _parse_timestamp(previous["updated_at"])

                if updated_at <= previous_timestamp:
                    continue

            base, quote = pair.split("_")
            record_id = f"{pair}_{normalized_timestamp}"

            if record_id in existing_ids:
                continue

            pairs[pair] = {
                "rate": float(rate),
                "updated_at": normalized_timestamp,
                "source": source,
            }

            new_records.append(
                {
                    "id": record_id,
                    "from_currency": base,
                    "to_currency": quote,
                    "rate": float(rate),
                    "timestamp": normalized_timestamp,
                    "source": source,
                    "meta": {},
                }
            )
            existing_ids.add(record_id)
            saved_count += 1

        if not saved_count:
            return 0

        last_refresh = current.get("last_refresh")

        if last_refresh is None or updated_at > _parse_timestamp(last_refresh):
            last_refresh = normalized_timestamp

        updated_cache = {
            "pairs": pairs,
            "last_refresh": last_refresh,
        }

        _atomic_write_json(self.history_file, history + new_records)
        _atomic_write_json(self.rates_file, updated_cache)

        return saved_count
