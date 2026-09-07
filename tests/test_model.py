from __future__ import annotations

import unittest
from datetime import datetime

from ges_forecast.domain import LossFactors, SiteConfig, ValidationError, WeatherHour
from ges_forecast.model import ForecastEngine
from ges_forecast.open_meteo import compass_to_open_meteo_azimuth


def site(**changes: object) -> SiteConfig:
    values: dict[str, object] = {
        "name": "Test saha", "latitude_deg": 37.0, "longitude_deg": 36.0,
        "panel_count": 100, "panel_power_wp": 550, "ac_capacity_kw": 40,
        "tilt_deg": 20, "azimuth_compass_deg": 180, "age_years": 0,
        "losses": LossFactors(soiling_pct=0, reflection_pct=0, mismatch_pct=0, dc_cable_pct=0, shading_pct=0, ac_cable_pct=0, transformer_pct=0, availability_pct=0, snow_pct=0),
    }
    values.update(changes)
    return SiteConfig(**values)  # type: ignore[arg-type]


def weather(gti: float, air: float = 25) -> WeatherHour:
    return WeatherHour(datetime(2026, 7, 1, 12), gti, air, 0.0)


class ForecastEngineAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ForecastEngine()

    def test_night_has_exactly_zero_production(self) -> None:
        result = self.engine.forecast_hour(site(), weather(0))
        self.assertEqual(result.energy_kwh, 0)
        self.assertEqual(result.average_ac_power_kw, 0)

    def test_temperature_direction_is_lower_at_40c_than_15c(self) -> None:
        cool = self.engine.forecast_hour(site(), weather(800, 15))
        hot = self.engine.forecast_hour(site(), weather(800, 40))
        self.assertLess(hot.energy_kwh, cool.energy_kwh)

    def test_older_site_has_measurably_lower_production(self) -> None:
        new = self.engine.forecast_hour(site(age_years=0), weather(800))
        old = self.engine.forecast_hour(site(age_years=15), weather(800))
        self.assertLess(old.energy_kwh, new.energy_kwh)

    def test_clipping_limits_ac_power_and_reports_lost_energy(self) -> None:
        result = self.engine.forecast_hour(site(ac_capacity_kw=10), weather(1200, 10))
        self.assertEqual(result.average_ac_power_kw, 10)
        self.assertGreater(result.clipping_loss_kwh, 0)

    def test_rejects_invalid_tilt_and_unrealistic_ac_capacity(self) -> None:
        with self.assertRaises(ValidationError):
            site(tilt_deg=91).validate()
        with self.assertRaises(ValidationError):
            site(ac_capacity_kw=1000).validate()

    def test_azimuth_conversion_is_explicit(self) -> None:
        self.assertEqual(compass_to_open_meteo_azimuth(180), 0)
        self.assertEqual(compass_to_open_meteo_azimuth(90), -90)
        self.assertEqual(abs(compass_to_open_meteo_azimuth(0)), 180)

