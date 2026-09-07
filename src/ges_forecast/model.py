from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from .domain import ForecastHour, MountType, SiteConfig, WeatherHour


class ForecastEngine:
    """İnternetten bağımsız, saatlik fiziksel üretim modeli.

    API'den gelen `global_tilted_irradiance_w_m2`, Open-Meteo'nun ilgili saatten
    önceki bir saat için ortalama GTI değeridir. Bu nedenle her model satırı 1
    saatlik ortalama güç ve aynı saatin enerjisini temsil eder.
    """

    def forecast(self, site: SiteConfig, weather: Iterable[WeatherHour]) -> list[ForecastHour]:
        site.validate()
        return [self.forecast_hour(site, item) for item in weather]

    def forecast_hour(self, site: SiteConfig, weather: WeatherHour) -> ForecastHour:
        site.validate()
        weather.validate()
        gti_w_m2 = max(0.0, weather.global_tilted_irradiance_w_m2)
        dc_capacity_kwp = site.dc_capacity_kwp  # Adım 1: kurulu DC güç.

        # Adım 2: GTI panel düzlemine taşınmış ışınım olarak veri katmanından gelir.
        cell_temperature_c = self._cell_temperature(site, weather, gti_w_m2)  # Adım 3.
        temperature_multiplier = max(
            0.0,
            1 + site.temperature_coefficient_per_c * (cell_temperature_c - 25),
        )  # Adım 4.
        aging_multiplier = self._aging_multiplier(site)  # Adım 5.

        dc_power_before_losses_kw = (
            dc_capacity_kwp * (gti_w_m2 / 1000) * temperature_multiplier * aging_multiplier
        )
        dc_loss_multiplier = site.losses.dc_multiplier()  # Adım 6.
        dc_power_after_losses_kw = dc_power_before_losses_kw * dc_loss_multiplier

        inverter_efficiency = self._inverter_efficiency(site, dc_power_after_losses_kw)  # Adım 7.
        ac_power_before_clipping_kw = dc_power_after_losses_kw * inverter_efficiency
        clipped_ac_power_kw = min(ac_power_before_clipping_kw, site.ac_capacity_kw)  # Adım 8.
        clipping_loss_kwh = max(0.0, ac_power_before_clipping_kw - clipped_ac_power_kw)

        ac_loss_multiplier = site.losses.ac_multiplier()  # Adım 9.
        average_ac_power_kw = max(0.0, clipped_ac_power_kw * ac_loss_multiplier)
        energy_kwh = average_ac_power_kw  # Adım 10: saatlik ortalama kW × 1 saat.

        return ForecastHour(
            timestamp=weather.timestamp,
            average_ac_power_kw=average_ac_power_kw,
            energy_kwh=energy_kwh,
            global_tilted_irradiance_w_m2=gti_w_m2,
            air_temperature_c=weather.air_temperature_c,
            cell_temperature_c=cell_temperature_c,
            dc_capacity_kwp=dc_capacity_kwp,
            dc_power_before_losses_kw=dc_power_before_losses_kw,
            dc_power_after_losses_kw=dc_power_after_losses_kw,
            inverter_efficiency=inverter_efficiency,
            ac_power_before_clipping_kw=ac_power_before_clipping_kw,
            clipping_loss_kwh=clipping_loss_kwh,
            ac_power_after_losses_kw=average_ac_power_kw,
            aging_multiplier=aging_multiplier,
            temperature_multiplier=temperature_multiplier,
            dc_loss_multiplier=dc_loss_multiplier,
            ac_loss_multiplier=ac_loss_multiplier,
            cloud_cover_pct=weather.cloud_cover_pct,
        )

    @staticmethod
    def _aging_multiplier(site: SiteConfig) -> float:
        if site.age_years == 0:
            return 1.0
        first_year = 1 - site.first_year_degradation_pct / 100
        following_years = max(0, site.age_years - 1)
        return first_year * (1 - site.annual_degradation_pct / 100) ** following_years

    @staticmethod
    def _cell_temperature(site: SiteConfig, weather: WeatherHour, gti_w_m2: float) -> float:
        mount_adjustment_c = {
            MountType.GROUND: 0.0,
            MountType.ROOF: 3.0,
            MountType.TRACKER: -1.0,
        }[site.mount_type]
        wind_m_s = max(0.0, weather.wind_speed_m_s or 0.0)
        # NOCT yaklaşımı: rüzgârla soğuma, ışınımla hücre ısınması.
        irradiance_rise_c = ((site.noct_c - 20) / 800) * gti_w_m2
        cooled_rise_c = irradiance_rise_c / (1 + 0.04 * wind_m_s)
        return weather.air_temperature_c + cooled_rise_c + mount_adjustment_c

    @staticmethod
    def _inverter_efficiency(site: SiteConfig, dc_power_kw: float) -> float:
        if dc_power_kw <= 0:
            return 0.0
        load_ratio = min(1.0, dc_power_kw / max(site.dc_capacity_kwp, 0.001))
        part_load_penalty = 0.04 * (1 - load_ratio) ** 2
        return max(0.90, min(site.inverter_nominal_efficiency, site.inverter_nominal_efficiency - part_load_penalty))
