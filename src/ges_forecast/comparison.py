from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .domain import ForecastHour, SiteConfig


TEST_SITES: tuple[SiteConfig, ...] = (
    SiteConfig("Saha 1", 37.075739, 36.804529, 91327, 550, 39700, 20, 180, 2),
    SiteConfig("Saha 2", 40.862088, 33.094728, 17854, 550, 7500, 25, 180, 3),
    SiteConfig("Saha 3", 38.275934, 39.741377, 7123, 550, 3500, 20, 180, 1),
)


@dataclass(frozen=True, slots=True)
class ComparisonMetrics:
    total_energy_kwh: float
    specific_yield_kwh_per_kwp: float
    clipping_loss_kwh: float
    clipping_loss_pct: float
    aging_loss_pct: float
    peak_timestamp: str | None
    monthly_clipping_kwh: dict[str, float]


def calculate_metrics(dc_capacity_kwp: float, hours: Iterable[ForecastHour | dict[str, Any]]) -> ComparisonMetrics:
    """Bir saha için seçili tahmin/doğrulama döneminin karşılaştırma metrikleri."""
    values = list(hours)
    total_energy = sum(_value(item, "energy_kwh") for item in values)
    clipping_loss = sum(_value(item, "clipping_loss_kwh") for item in values)
    unclipped_energy = sum(_value(item, "ac_power_before_clipping_kw") for item in values)
    peak = max(values, key=lambda item: _value(item, "energy_kwh"), default=None)
    monthly_clipping: dict[str, float] = {}
    for item in values:
        timestamp = _value(item, "timestamp")
        month = timestamp.strftime("%Y-%m") if hasattr(timestamp, "strftime") else str(timestamp)[:7]
        monthly_clipping[month] = monthly_clipping.get(month, 0.0) + _value(item, "clipping_loss_kwh")

    return ComparisonMetrics(
        total_energy_kwh=total_energy,
        specific_yield_kwh_per_kwp=total_energy / dc_capacity_kwp if dc_capacity_kwp else 0.0,
        clipping_loss_kwh=clipping_loss,
        clipping_loss_pct=clipping_loss / unclipped_energy * 100 if unclipped_energy else 0.0,
        aging_loss_pct=(1 - _value(values[0], "aging_multiplier")) * 100 if values else 0.0,
        peak_timestamp=_timestamp_text(_value(peak, "timestamp")) if peak else None,
        monthly_clipping_kwh=monthly_clipping,
    )


def _value(item: ForecastHour | dict[str, Any], field: str) -> Any:
    return item[field] if isinstance(item, dict) else getattr(item, field)


def _timestamp_text(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
