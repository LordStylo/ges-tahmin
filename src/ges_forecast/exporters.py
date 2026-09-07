from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any

from openpyxl import Workbook

FIELDS = [
    ("timestamp", "Zaman"),
    ("energy_kwh", "Enerji (kWh)"),
    ("average_ac_power_kw", "Ortalama AC Güç (kW)"),
    ("global_tilted_irradiance_w_m2", "Eğik Yüzey Işınımı (W/m²)"),
    ("air_temperature_c", "Hava Sıcaklığı (°C)"),
    ("cell_temperature_c", "Hücre Sıcaklığı (°C)"),
    ("dc_power_after_losses_kw", "Kayıplar Sonrası DC Güç (kW)"),
    ("inverter_efficiency", "İnverter Verimi"),
    ("ac_power_before_clipping_kw", "Kırpma Öncesi AC Güç (kW)"),
    ("clipping_loss_kwh", "Kırpma Kaybı (kWh)"),
    ("ac_power_after_losses_kw", "AC Kayıplar Sonrası Güç (kW)"),
]


def to_csv(forecast: dict[str, Any]) -> bytes:
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([label for _, label in FIELDS])
    for hour in forecast["hours"]:
        writer.writerow([hour.get(key, "") for key, _ in FIELDS])
    return stream.getvalue().encode("utf-8-sig")


def to_xlsx(forecast: dict[str, Any]) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Saatlik Tahmin"
    sheet.append([label for _, label in FIELDS])
    for hour in forecast["hours"]:
        sheet.append([hour.get(key) for key, _ in FIELDS])
    sheet.freeze_panes = "A2"
    for column in sheet.columns:
        width = min(32, max(len(str(cell.value or "")) for cell in column) + 2)
        sheet.column_dimensions[column[0].column_letter].width = width
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()
