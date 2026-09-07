from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .domain import SiteConfig, ValidationError, WeatherHour
from .storage import Repository

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


@dataclass(frozen=True, slots=True)
class WeatherFetchResult:
    hours: list[WeatherHour]
    source: str
    age_minutes: float
    attribution: str = "Weather data by Open-Meteo.com (CC BY 4.0); includes Copernicus-derived sources."


class OpenMeteoClient:
    def __init__(self, repository: Repository, timeout_seconds: int = 12) -> None:
        self.repository = repository
        self.timeout_seconds = timeout_seconds

    def forecast(self, site: SiteConfig, days: int = 7) -> WeatherFetchResult:
        if not 1 <= days <= 16:
            raise ValidationError("Tahmin günü 1 ile 16 arasında olmalıdır.")
        query = {
            "latitude": site.latitude_deg,
            "longitude": site.longitude_deg,
            "hourly": "global_tilted_irradiance,temperature_2m,wind_speed_10m,cloud_cover",
            "tilt": site.tilt_deg,
            "azimuth": compass_to_open_meteo_azimuth(site.azimuth_compass_deg),
            "timezone": site.timezone,
            "forecast_days": days,
            "wind_speed_unit": "ms",
        }
        if site.elevation_m is not None:
            query["elevation"] = site.elevation_m
        return self._cached_json_to_weather(FORECAST_URL, query)

    def historical(self, site: SiteConfig, start_date: str, end_date: str) -> WeatherFetchResult:
        """Doğruluk doğrulaması için geçmiş saatlik meteoroloji/GTI serisi."""
        query = {
            "latitude": site.latitude_deg,
            "longitude": site.longitude_deg,
            "hourly": "global_tilted_irradiance,temperature_2m,wind_speed_10m,cloud_cover",
            "tilt": site.tilt_deg,
            "azimuth": compass_to_open_meteo_azimuth(site.azimuth_compass_deg),
            "timezone": site.timezone,
            "start_date": start_date,
            "end_date": end_date,
            "wind_speed_unit": "ms",
        }
        if site.elevation_m is not None:
            query["elevation"] = site.elevation_m
        return self._cached_json_to_weather(ARCHIVE_URL, query)

    def geocode(self, name: str) -> list[dict[str, Any]]:
        if len(name.strip()) < 2:
            raise ValidationError("Konum araması en az iki karakter olmalıdır.")
        payload = self._request_json(GEOCODING_URL, {"name": name, "count": 10, "language": "tr"})
        return list(payload.get("results", []))

    def elevation(self, latitude_deg: float, longitude_deg: float) -> float:
        payload = self._request_json(ELEVATION_URL, {"latitude": latitude_deg, "longitude": longitude_deg})
        return float(payload["elevation"][0])

    def _cached_json_to_weather(self, base_url: str, query: dict[str, Any]) -> WeatherFetchResult:
        canonical_query = {key: _canonical_query_value(value) for key, value in query.items()}
        source_url = f"{base_url}?{urlencode(canonical_query)}"
        key = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
        cached = self.repository.cache_get(key)
        now = datetime.now(UTC)
        if cached:
            payload, fetched_at, _ = cached
            age_minutes = (now - fetched_at).total_seconds() / 60
            if age_minutes < 60:
                return WeatherFetchResult(_parse_weather(payload), "fresh_cache", age_minutes)
        try:
            payload = self._request_json(base_url, canonical_query)
            self.repository.cache_put(key, payload, source_url)
            return WeatherFetchResult(_parse_weather(payload), "open_meteo", 0.0)
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            if cached:
                payload, fetched_at, _ = cached
                age_minutes = (now - fetched_at).total_seconds() / 60
                return WeatherFetchResult(_parse_weather(payload), "stale_cache", age_minutes)
            raise RuntimeError(
                "Open-Meteo'ya ulaşılamadı ve bu sorgu için önbellekte veri yok. "
                "Bağlantıyı kontrol edin veya daha önce başarıyla çekilmiş veriyi kullanın."
            ) from exc

    def _request_json(self, base_url: str, query: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{base_url}?{urlencode(query)}",
            headers={"User-Agent": "GES-Uretim-Tahmin-Motoru/0.1 (local educational project)"},
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310: fixed HTTPS endpoints
            return json.loads(response.read().decode("utf-8"))


def compass_to_open_meteo_azimuth(compass_deg: float) -> float:
    """Kuzey=0 pusula açısını Open-Meteo'nun Güney=0 açısına çevirir."""
    return ((compass_deg - 180 + 180) % 360) - 180


def _canonical_query_value(value: Any) -> Any:
    """20 ile 20.0 gibi eşdeğer girdi biçimlerini aynı önbellek anahtarına indirger."""
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else format(value, ".12g")
    return value


def _parse_weather(payload: dict[str, Any]) -> list[WeatherHour]:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        reason = payload.get("reason", "Saatlik veri dönmedi.")
        raise ValueError(f"Open-Meteo yanıtı geçersiz: {reason}")
    required = ("time", "global_tilted_irradiance", "temperature_2m", "wind_speed_10m")
    if any(key not in hourly for key in required):
        raise ValueError("Open-Meteo yanıtında model için zorunlu bir saatlik alan eksik.")
    timezone_name = payload.get("timezone", "UTC")
    cloud_cover = hourly.get("cloud_cover", [None] * len(hourly["time"]))
    return [
        WeatherHour(
            timestamp=datetime.fromisoformat(timestamp),
            global_tilted_irradiance_w_m2=float(gti or 0),
            air_temperature_c=float(temp or 0),
            wind_speed_m_s=float(wind) if wind is not None else None,
            cloud_cover_pct=float(cloud) if cloud is not None else None,
        )
        for timestamp, gti, temp, wind, cloud in zip(
            hourly["time"],
            hourly["global_tilted_irradiance"],
            hourly["temperature_2m"],
            hourly["wind_speed_10m"],
            cloud_cover,
            strict=True,
        )
    ]
