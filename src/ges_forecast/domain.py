from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ValidationError(ValueError):
    """Kullanıcıya açıklanabilecek alan doğrulama hatası."""


class MountType(StrEnum):
    GROUND = "ground"
    ROOF = "roof"
    TRACKER = "tracker"


@dataclass(frozen=True, slots=True)
class LossFactors:
    """Her değer yüzde olarak girilir; modelde 0-1 katsayısına çevrilir."""

    soiling_pct: float = 2.0
    reflection_pct: float = 2.0
    mismatch_pct: float = 2.0
    dc_cable_pct: float = 1.5
    shading_pct: float = 0.0
    ac_cable_pct: float = 1.0
    transformer_pct: float = 1.0
    availability_pct: float = 0.0
    snow_pct: float = 0.0

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if not 0 <= value < 100:
                raise ValidationError(f"{name} 0 ile 100 arasında olmalıdır.")

    def dc_multiplier(self) -> float:
        self.validate()
        return _multiplier(
            self.soiling_pct,
            self.reflection_pct,
            self.mismatch_pct,
            self.dc_cable_pct,
            self.shading_pct,
        )

    def ac_multiplier(self) -> float:
        self.validate()
        return _multiplier(
            self.ac_cable_pct,
            self.transformer_pct,
            self.availability_pct,
            self.snow_pct,
        )


def _multiplier(*percentages: float) -> float:
    result = 1.0
    for value in percentages:
        result *= 1 - value / 100
    return result


@dataclass(frozen=True, slots=True)
class SiteConfig:
    name: str
    latitude_deg: float
    longitude_deg: float
    panel_count: int
    panel_power_wp: float
    ac_capacity_kw: float
    tilt_deg: float
    # Pusula konvansiyonu: Kuzey=0, Doğu=90, Güney=180, Batı=270.
    azimuth_compass_deg: float
    age_years: int
    timezone: str = "auto"
    elevation_m: float | None = None
    temperature_coefficient_per_c: float = -0.004
    noct_c: float = 45.0
    first_year_degradation_pct: float = 2.0
    annual_degradation_pct: float = 0.55
    inverter_nominal_efficiency: float = 0.98
    mount_type: MountType = MountType.GROUND
    losses: LossFactors = field(default_factory=LossFactors)

    @property
    def dc_capacity_kwp(self) -> float:
        return self.panel_count * self.panel_power_wp / 1000

    @property
    def dc_ac_ratio(self) -> float:
        return self.dc_capacity_kwp / self.ac_capacity_kw

    def validate(self) -> None:
        if not self.name.strip():
            raise ValidationError("Saha adı boş bırakılamaz.")
        if not -90 <= self.latitude_deg <= 90:
            raise ValidationError("Enlem -90 ile 90 derece arasında olmalıdır.")
        if not -180 <= self.longitude_deg <= 180:
            raise ValidationError("Boylam -180 ile 180 derece arasında olmalıdır.")
        if self.panel_count <= 0:
            raise ValidationError("Panel adedi pozitif olmalıdır.")
        if self.panel_power_wp <= 0:
            raise ValidationError("Panel tekil gücü pozitif olmalıdır.")
        if self.ac_capacity_kw <= 0:
            raise ValidationError("Toplam AC güç pozitif olmalıdır.")
        if not 0 <= self.tilt_deg <= 90:
            raise ValidationError("Panel eğim açısı 0 ile 90 derece arasında olmalıdır.")
        if not 0 <= self.azimuth_compass_deg < 360:
            raise ValidationError("Azimut 0 ile 359.999 derece arasında olmalıdır.")
        if self.age_years < 0:
            raise ValidationError("Saha yaşı negatif olamaz.")
        if self.temperature_coefficient_per_c > 0:
            raise ValidationError("Panel sıcaklık katsayısı negatif veya sıfır olmalıdır.")
        if not 0.85 <= self.inverter_nominal_efficiency <= 1:
            raise ValidationError("İnverter nominal verimi 0.85 ile 1 arasında olmalıdır.")
        if self.ac_capacity_kw > self.dc_capacity_kwp * 1.5:
            raise ValidationError(
                "AC kurulu güç DC kurulu güce göre gerçekçi olmayan derecede büyük. "
                "Panel sayısı, panel gücü veya AC gücü alanlarını kontrol edin."
            )
        self.losses.validate()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["mount_type"] = self.mount_type.value
        return result


@dataclass(frozen=True, slots=True)
class WeatherHour:
    timestamp: datetime
    global_tilted_irradiance_w_m2: float
    air_temperature_c: float
    wind_speed_m_s: float | None
    cloud_cover_pct: float | None = None

    def validate(self) -> None:
        if self.global_tilted_irradiance_w_m2 < 0:
            raise ValidationError("Eğik yüzey ışınımı negatif olamaz.")


@dataclass(frozen=True, slots=True)
class ForecastHour:
    timestamp: datetime
    average_ac_power_kw: float
    energy_kwh: float
    global_tilted_irradiance_w_m2: float
    air_temperature_c: float
    cell_temperature_c: float
    dc_capacity_kwp: float
    dc_power_before_losses_kw: float
    dc_power_after_losses_kw: float
    inverter_efficiency: float
    ac_power_before_clipping_kw: float
    clipping_loss_kwh: float
    ac_power_after_losses_kw: float
    aging_multiplier: float
    temperature_multiplier: float
    dc_loss_multiplier: float
    ac_loss_multiplier: float
    cloud_cover_pct: float | None

