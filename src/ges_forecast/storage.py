from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .domain import ForecastHour, SiteConfig


class Repository:
    """Tahmin sürümlerini asla ezmeden saklayan SQLite deposu."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS sites (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS weather_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    fetched_at_utc TEXT NOT NULL,
                    source_url TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS forecasts (
                    id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL REFERENCES sites(id),
                    generated_at_utc TEXT NOT NULL,
                    weather_source TEXT NOT NULL,
                    weather_age_minutes REAL NOT NULL,
                    model_version TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS forecast_hours (
                    forecast_id TEXT NOT NULL REFERENCES forecasts(id),
                    timestamp_local TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (forecast_id, timestamp_local)
                );
                CREATE TABLE IF NOT EXISTS actual_production (
                    site_id TEXT NOT NULL REFERENCES sites(id),
                    timestamp_local TEXT NOT NULL,
                    energy_kwh REAL NOT NULL CHECK(energy_kwh >= 0),
                    PRIMARY KEY (site_id, timestamp_local)
                );
                """
            )
            connection.commit()

    def cache_get(self, cache_key: str) -> tuple[dict[str, Any], datetime, str] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json, fetched_at_utc, source_url FROM weather_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["payload_json"]), _parse_utc(row["fetched_at_utc"]), row["source_url"]

    def cache_put(self, cache_key: str, payload: dict[str, Any], source_url: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """INSERT INTO weather_cache(cache_key, payload_json, fetched_at_utc, source_url)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(cache_key) DO UPDATE SET
                       payload_json=excluded.payload_json,
                       fetched_at_utc=excluded.fetched_at_utc,
                       source_url=excluded.source_url""",
                (cache_key, json.dumps(payload), _utc_now().isoformat(), source_url),
            )
            connection.commit()

    def save_forecast(
        self,
        site: SiteConfig,
        hours: list[ForecastHour],
        weather_source: str,
        weather_age_minutes: float,
    ) -> tuple[str, str]:
        site_id = str(uuid.uuid4())
        forecast_id = str(uuid.uuid4())
        now = _utc_now().isoformat()
        with closing(self._connect()) as connection:
            connection.execute(
                "INSERT INTO sites(id, name, config_json, created_at_utc) VALUES (?, ?, ?, ?)",
                (site_id, site.name, json.dumps(site.to_dict()), now),
            )
            connection.execute(
                """INSERT INTO forecasts(id, site_id, generated_at_utc, weather_source,
                   weather_age_minutes, model_version) VALUES (?, ?, ?, ?, ?, ?)""",
                (forecast_id, site_id, now, weather_source, weather_age_minutes, "0.1.0"),
            )
            connection.executemany(
                "INSERT INTO forecast_hours(forecast_id, timestamp_local, payload_json) VALUES (?, ?, ?)",
                [
                    (
                        forecast_id,
                        hour.timestamp.isoformat(),
                        json.dumps(_forecast_hour_to_dict(hour)),
                    )
                    for hour in hours
                ],
            )
            connection.commit()
        return site_id, forecast_id

    def get_forecast(self, forecast_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            header = connection.execute(
                """SELECT f.id, f.generated_at_utc, f.weather_source, f.weather_age_minutes,
                          f.model_version, s.id AS site_id, s.name, s.config_json
                     FROM forecasts f JOIN sites s ON s.id=f.site_id WHERE f.id=?""",
                (forecast_id,),
            ).fetchone()
            if header is None:
                return None
            rows = connection.execute(
                "SELECT payload_json FROM forecast_hours WHERE forecast_id=? ORDER BY timestamp_local",
                (forecast_id,),
            ).fetchall()
        return {
            **dict(header),
            "site": json.loads(header["config_json"]),
            "hours": [json.loads(row["payload_json"]) for row in rows],
        }

    def list_forecasts(self, limit: int = 100) -> list[dict[str, Any]]:
        """En yeni tahmin sürümlerini, saatlik satırları yüklemeden listeler."""
        if not 1 <= limit <= 500:
            raise ValueError("Geçmiş liste limiti 1 ile 500 arasında olmalıdır.")

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT f.id,
                       s.name,
                       f.generated_at_utc,
                       f.weather_source,
                       f.weather_age_minutes,
                       f.model_version,
                       COUNT(fh.timestamp_local) AS hour_count,
                       MIN(fh.timestamp_local) AS first_hour_local,
                       MAX(fh.timestamp_local) AS last_hour_local
                  FROM forecasts f
                  JOIN sites s ON s.id = f.site_id
             LEFT JOIN forecast_hours fh ON fh.forecast_id = f.id
              GROUP BY f.id
              ORDER BY f.generated_at_utc DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_actuals(self, site_id: str, actuals: list[tuple[str, float]]) -> int:
        with closing(self._connect()) as connection:
            connection.executemany(
                """INSERT INTO actual_production(site_id, timestamp_local, energy_kwh) VALUES (?, ?, ?)
                   ON CONFLICT(site_id, timestamp_local) DO UPDATE SET energy_kwh=excluded.energy_kwh""",
                [(site_id, timestamp, energy) for timestamp, energy in actuals],
            )
            connection.commit()
        return len(actuals)

    def get_actuals(self, site_id: str) -> dict[str, float]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT timestamp_local, energy_kwh FROM actual_production WHERE site_id=?",
                (site_id,),
            ).fetchall()
        return {row["timestamp_local"]: float(row["energy_kwh"]) for row in rows}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def _forecast_hour_to_dict(hour: ForecastHour) -> dict[str, Any]:
    return {
        "timestamp": hour.timestamp.isoformat(),
        "average_ac_power_kw": hour.average_ac_power_kw,
        "energy_kwh": hour.energy_kwh,
        "global_tilted_irradiance_w_m2": hour.global_tilted_irradiance_w_m2,
        "air_temperature_c": hour.air_temperature_c,
        "cell_temperature_c": hour.cell_temperature_c,
        "dc_capacity_kwp": hour.dc_capacity_kwp,
        "dc_power_before_losses_kw": hour.dc_power_before_losses_kw,
        "dc_power_after_losses_kw": hour.dc_power_after_losses_kw,
        "inverter_efficiency": hour.inverter_efficiency,
        "ac_power_before_clipping_kw": hour.ac_power_before_clipping_kw,
        "clipping_loss_kwh": hour.clipping_loss_kwh,
        "ac_power_after_losses_kw": hour.ac_power_after_losses_kw,
        "aging_multiplier": hour.aging_multiplier,
        "temperature_multiplier": hour.temperature_multiplier,
        "dc_loss_multiplier": hour.dc_loss_multiplier,
        "ac_loss_multiplier": hour.ac_loss_multiplier,
        "cloud_cover_pct": hour.cloud_cover_pct,
    }
