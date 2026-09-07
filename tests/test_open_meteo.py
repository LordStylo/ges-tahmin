from __future__ import annotations

import unittest

from ges_forecast.open_meteo import _canonical_query_value


class CacheKeyNormalizationTests(unittest.TestCase):
    def test_equivalent_integral_float_is_canonicalized(self) -> None:
        self.assertEqual(_canonical_query_value(20.0), "20")
        self.assertEqual(_canonical_query_value(20), 20)
