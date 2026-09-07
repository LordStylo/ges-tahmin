from __future__ import annotations

import unittest
from dataclasses import asdict
from datetime import datetime

from ges_forecast.app import _comparison_view
from ges_forecast.comparison import TEST_SITES, calculate_metrics
from ges_forecast.domain import WeatherHour
from ges_forecast.model import ForecastEngine


class TestSiteComparisonTests(unittest.TestCase):
    def test_appendix_sites_have_distinct_dc_ac_ratios_above_one(self) -> None:
        ratios = [site.dc_ac_ratio for site in TEST_SITES]
        self.assertTrue(all(ratio > 1 for ratio in ratios))
        self.assertEqual(len(set(ratios)), 3)

    def test_clipping_and_aging_metrics_follow_the_expected_order(self) -> None:
        weather = [WeatherHour(datetime(2025, 6, 21, hour), 1300, 25, 2) for hour in range(10, 15)]
        engine = ForecastEngine()
        metrics = [calculate_metrics(site.dc_capacity_kwp, engine.forecast(site, weather)) for site in TEST_SITES]

        self.assertGreater(metrics[1].clipping_loss_pct, metrics[0].clipping_loss_pct)
        self.assertGreater(metrics[0].clipping_loss_pct, metrics[2].clipping_loss_pct)
        self.assertLess(metrics[2].aging_loss_pct, metrics[0].aging_loss_pct)
        self.assertLess(metrics[0].aging_loss_pct, metrics[1].aging_loss_pct)
        self.assertIn("2025-06", metrics[0].monthly_clipping_kwh)

    def test_comparison_view_has_required_acceptance_outputs(self) -> None:
        weather = [WeatherHour(datetime(2025, 6, 21, hour), 1300, 25, 2) for hour in range(10, 15)]
        engine = ForecastEngine()
        records = []
        for index, site in enumerate(TEST_SITES, start=1):
            hours = []
            for hour in engine.forecast(site, weather):
                row = asdict(hour)
                row["timestamp"] = hour.timestamp.isoformat()
                hours.append(row)
            records.append({"id": str(index) * 8, "name": site.name, "site": site.to_dict(), "hours": hours})

        page = _comparison_view(records)
        self.assertIn("DC/AC", page)
        self.assertIn("Spesifik üretim", page)
        self.assertIn("Kırpma kaybının aylara dağılımı", page)
        self.assertIn("Aynı gün için üretim eğrileri", page)
