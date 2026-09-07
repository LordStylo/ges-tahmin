from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from ges_forecast.domain import SiteConfig, WeatherHour
from ges_forecast.model import ForecastEngine
from ges_forecast.storage import Repository


class VersioningTests(unittest.TestCase):
    def test_same_hour_forecasts_are_stored_as_distinct_versions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Repository(Path(directory) / "app.sqlite3")
            site = SiteConfig("Saha", 37, 36, 100, 550, 40, 20, 180, 2)
            hour = ForecastEngine().forecast_hour(site, WeatherHour(datetime(2026, 1, 1, 12), 700, 20, 2))
            _, first = repository.save_forecast(site, [hour], "test", 0)
            _, second = repository.save_forecast(site, [hour], "test", 0)
            self.assertNotEqual(first, second)
            self.assertEqual(len(repository.get_forecast(first)["hours"]), 1)  # type: ignore[index]
            self.assertEqual(len(repository.get_forecast(second)["hours"]), 1)  # type: ignore[index]
            history = repository.list_forecasts()
            self.assertEqual({item["id"] for item in history}, {first, second})
            self.assertTrue(all(item["hour_count"] == 1 for item in history))
            self.assertTrue(all(item["name"] == "Saha" for item in history))
