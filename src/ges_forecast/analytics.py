from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True, slots=True)
class AccuracyReport:
    matched_hours: int
    mae_kwh: float
    rmse_kwh: float
    mean_bias_kwh: float
    normalized_mae_pct_dc: float
    baseline_mae_kwh: float | None
    hourly_mae_kwh: dict[int, float]
    weather_group_mae_kwh: dict[str, float]


def evaluate_forecast(
    forecast_hours: list[dict[str, Any]], actuals_by_timestamp: dict[str, float], dc_capacity_kwp: float
) -> AccuracyReport:
    pairs: list[tuple[dict[str, Any], float]] = [
        (hour, actuals_by_timestamp[hour["timestamp"]])
        for hour in forecast_hours
        if hour["timestamp"] in actuals_by_timestamp
    ]
    if not pairs:
        raise ValueError("Bu tahminle eşleşen gerçekleşen üretim kaydı bulunamadı.")

    errors = [hour["energy_kwh"] - actual for hour, actual in pairs]
    hourly_errors: dict[int, list[float]] = defaultdict(list)
    weather_errors: dict[str, list[float]] = defaultdict(list)
    baseline_errors: list[float] = []
    for hour, actual in pairs:
        timestamp = datetime.fromisoformat(hour["timestamp"])
        hourly_errors[timestamp.hour].append(abs(hour["energy_kwh"] - actual))
        weather_errors[_weather_group(hour.get("cloud_cover_pct"))].append(abs(hour["energy_kwh"] - actual))
        prior = (timestamp - timedelta(days=1)).isoformat()
        if prior in actuals_by_timestamp:
            baseline_errors.append(abs(actuals_by_timestamp[prior] - actual))

    mae = sum(abs(error) for error in errors) / len(errors)
    return AccuracyReport(
        matched_hours=len(pairs),
        mae_kwh=mae,
        rmse_kwh=math.sqrt(sum(error * error for error in errors) / len(errors)),
        mean_bias_kwh=sum(errors) / len(errors),
        normalized_mae_pct_dc=mae / dc_capacity_kwp * 100,
        baseline_mae_kwh=sum(baseline_errors) / len(baseline_errors) if baseline_errors else None,
        hourly_mae_kwh={hour: sum(values) / len(values) for hour, values in sorted(hourly_errors.items())},
        weather_group_mae_kwh={group: sum(values) / len(values) for group, values in weather_errors.items()},
    )


def _weather_group(cloud_cover_pct: float | None) -> str:
    if cloud_cover_pct is None:
        return "bilinmiyor"
    if cloud_cover_pct < 20:
        return "açık"
    if cloud_cover_pct < 70:
        return "parçalı bulutlu"
    return "kapalı"
