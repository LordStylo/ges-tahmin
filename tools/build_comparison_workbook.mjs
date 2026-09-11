import { execFileSync } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = process.argv[2];
const forecastIds = process.argv.slice(3);
if (!outputDir || forecastIds.length !== 3) {
  throw new Error("Kullanım: node build_comparison_workbook.mjs <çıktı-klasörü> <3-tahmin-id>");
}

const python = process.env.BUNDLED_PYTHON;
if (!python) throw new Error("BUNDLED_PYTHON ortam değişkeni gerekli.");

const readForecasts = String.raw`
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from ges_forecast.storage import Repository

repository = Repository(Path.cwd() / "data" / "ges_forecast.sqlite3")
records = []
for forecast_id in json.loads(sys.argv[1]):
    forecast = repository.get_forecast(forecast_id)
    if forecast is None:
        raise ValueError(f"Tahmin bulunamadı: {forecast_id}")
    records.append(forecast)
print(json.dumps(records, ensure_ascii=False))
`;

const records = JSON.parse(execFileSync(python, ["-c", readForecasts, JSON.stringify(forecastIds)], { encoding: "utf8" }));
records.sort((left, right) => left.name.localeCompare(right.name, "tr"));

const colors = ["#155EEF", "#16A34A", "#7C3AED"];
const dark = "#12376D";
const pale = "#EDF4FF";
const line = "#D9E2EE";
const inputFill = "#FFF4CC";
const font = "Arial";

const number = (value, digits = 1) => Number(Number(value).toFixed(digits));
const dayOf = (timestamp) => timestamp.slice(0, 10);
const hourOf = (timestamp) => `${timestamp.slice(8, 10)}.${timestamp.slice(5, 7)} ${timestamp.slice(11, 16)}`;
const displayDate = (isoDate) => `${isoDate.slice(8, 10)}.${isoDate.slice(5, 7)}.${isoDate.slice(0, 4)}`;
const dcCapacity = (record) => record.site.panel_count * record.site.panel_power_wp / 1000;
const totals = (record) => {
  const energy = record.hours.reduce((sum, hour) => sum + hour.energy_kwh, 0);
  const preClip = record.hours.reduce((sum, hour) => sum + hour.ac_power_before_clipping_kw, 0);
  const clipping = record.hours.reduce((sum, hour) => sum + hour.clipping_loss_kwh, 0);
  const peak = record.hours.reduce((best, hour) => hour.average_ac_power_kw > best.average_ac_power_kw ? hour : best, record.hours[0]);
  return { energy, preClip, clipping, peak };
};

function header(sheet, range) {
  range.format = {
    fill: dark,
    font: { name: font, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#FFFFFF" },
  };
  range.format.rowHeight = 30;
}

function title(sheet, titleText, context) {
  sheet.showGridLines = false;
  sheet.getRange("A1:J1").values = [[titleText, "", "", "", "", "", "", "", "", ""]];
  sheet.getRange("A1:J1").format = { font: { name: font, size: 16, bold: true, color: dark } };
  sheet.getRange("A2:J2").values = [[context, "", "", "", "", "", "", "", "", ""]];
  sheet.getRange("A2:J2").format = { font: { name: font, size: 10, italic: true, color: "#5B6B82" } };
  sheet.getRange("A3:J3").format.borders = { bottom: { style: "thin", color: line } };
}

function styleData(sheet, range, numberFormat = "#,##0.0") {
  range.format = { font: { name: font, size: 10, color: "#10233F" }, verticalAlignment: "center" };
  range.format.numberFormat = numberFormat;
  range.format.borders = { bottom: { style: "thin", color: line } };
}

function addLineChart(sheet, sourceRange, titleText, position, seriesColors) {
  const chart = sheet.charts.add("line", sourceRange);
  chart.title = titleText;
  chart.titleTextStyle.typeface = font;
  chart.titleTextStyle.fontSize = 13;
  chart.legend = { position: "top", textStyle: { typeface: font, fontSize: 10 } };
  chart.xAxis = { axisType: "textAxis", textStyle: { typeface: font, fontSize: 9 } };
  chart.yAxis = { numberFormatCode: "#,##0", numberFormatSourceLinked: false, textStyle: { typeface: font, fontSize: 9 } };
  chart.setPosition(position[0], position[1]);
  chart.series.items.forEach((series, index) => { series.fill = seriesColors[index % seriesColors.length]; });
  return chart;
}

function dailyMatrix(record) {
  const values = new Map();
  for (const hour of record.hours) {
    const day = dayOf(hour.timestamp);
    const current = values.get(day) || { energy: 0, clipping: 0, peak: hour };
    current.energy += hour.energy_kwh;
    current.clipping += hour.clipping_loss_kwh;
    if (hour.average_ac_power_kw > current.peak.average_ac_power_kw) current.peak = hour;
    values.set(day, current);
  }
  return [...values.entries()].map(([day, value]) => [day, value]);
}

const workbook = Workbook.create();
const overview = workbook.worksheets.add("Karşılaştırma Özeti");
title(overview, "Üç Saha Saatlik Üretim Tahmin Karşılaştırması", "7 günlük Open-Meteo tahmini · 07.09.2026–13.09.2026 · enerji birimi kWh");
overview.tabColor = dark;

overview.getRange("A5:J5").values = [["Saha", "DC (kWp)", "AC limit (kW)", "DC/AC", "Toplam enerji (kWh)", "Spesifik üretim\n(kWh/kWp)", "Kırpma (kWh)", "Kırpma oranı", "Net AC tepe (kW)", "Tepe zamanı"]];
header(overview, overview.getRange("A5:J5"));
const summaryRows = records.map((record) => {
  const total = totals(record);
  const dc = dcCapacity(record);
  return [record.name, number(dc, 1), record.site.ac_capacity_kw, number(dc / record.site.ac_capacity_kw, 3), number(total.energy), number(total.energy / dc, 3), number(total.clipping), total.preClip ? total.clipping / total.preClip : 0, number(total.peak.average_ac_power_kw), total.peak.timestamp.replace("T", " ")];
});
overview.getRange(`A6:J${5 + summaryRows.length}`).values = summaryRows;
styleData(overview, overview.getRange(`A6:J${5 + summaryRows.length}`));
overview.getRange(`B6:C${5 + summaryRows.length}`).format.numberFormat = "#,##0.0";
overview.getRange(`D6:D${5 + summaryRows.length}`).format.numberFormat = "0.000";
overview.getRange(`E6:G${5 + summaryRows.length}`).format.numberFormat = "#,##0.0";
overview.getRange(`H6:H${5 + summaryRows.length}`).format.numberFormat = "0.000%";
overview.getRange(`I6:I${5 + summaryRows.length}`).format.numberFormat = "#,##0.0";

const allDays = [...new Set(records.flatMap((record) => record.hours.map((hour) => dayOf(hour.timestamp))))].sort();
const dailyMaps = records.map((record) => new Map(dailyMatrix(record)));
overview.getRange("A11:D11").values = [["Tarih", ...records.map((record) => `${record.name} günlük enerji (kWh)` )]];
header(overview, overview.getRange("A11:D11"));
const overviewDailyRows = allDays.map((day) => [displayDate(day), ...dailyMaps.map((daily) => number(daily.get(day)?.energy || 0))]);
overview.getRange(`A12:D${11 + overviewDailyRows.length}`).values = overviewDailyRows;
styleData(overview, overview.getRange(`A12:D${11 + overviewDailyRows.length}`));
overview.getRange(`B12:D${11 + overviewDailyRows.length}`).format.numberFormat = "#,##0.0";
addLineChart(overview, overview.getRange(`A11:D${11 + overviewDailyRows.length}`), "Sahalara göre günlük tahmini üretim (kWh)", ["F11", "N27"], colors);

overview.getRange("A22:D22").values = [["Saha", "Koordinat", "Panel ve eğim", "Tahmin sürümü"]];
header(overview, overview.getRange("A22:D22"));
const identityRows = records.map((record) => [record.name, `${record.site.latitude_deg.toFixed(6)}, ${record.site.longitude_deg.toFixed(6)}`, `${record.site.panel_count.toLocaleString("tr-TR")} × ${record.site.panel_power_wp} Wp · ${record.site.tilt_deg}°`, record.id]);
overview.getRange(`A23:D${22 + identityRows.length}`).values = identityRows;
styleData(overview, overview.getRange(`A23:D${22 + identityRows.length}`, "@"));
overview.getRange(`D23:D${22 + identityRows.length}`).format.font = { name: font, size: 9, color: "#5B6B82" };
overview.getRange("A27:D28").values = [["Yarın için not", "07.09.2026 saatlik gerçekleşen kWh verisini “Gerçekleşen 07.09” sekmesindeki sarı alanlara girin.", "", ""], ["Model notu", "Net üretim AC limitinden sonradır; kırpma öncesi AC, limit nedeniyle kesilen gücü gösterir.", "", ""]];
overview.getRange("A27:A28").format = { fill: pale, font: { name: font, bold: true, color: dark }, verticalAlignment: "top" };
overview.getRange("B27:D28").format = { fill: pale, font: { name: font, color: "#10233F" }, wrapText: true, verticalAlignment: "top" };
overview.getRange("A27:D28").format.borders = { preset: "outside", style: "thin", color: "#BFD6FF" };
overview.getRange("A27:D28").format.rowHeight = 40;
overview.getRange("A:A").format.columnWidth = 20;
overview.getRange("B:B").format.columnWidth = 22;
overview.getRange("C:C").format.columnWidth = 25;
overview.getRange("D:D").format.columnWidth = 23;
overview.getRange("E:J").format.columnWidth = 17;

const hourly = workbook.worksheets.add("Saatlik Karşılaştırma");
title(hourly, "Saatlik Üç Saha Karşılaştırması", "Aynı zaman damgasındaki net tahmin üretimi; her sütun bir saatlik enerji (kWh). Ayrıntı ve saha grafikleri ilgili sekmelerde.");
hourly.tabColor = "#155EEF";
hourly.getRange("A5:D5").values = [["Tarih-saat", ...records.map((record) => `${record.name} net üretim (kWh)`)]];
header(hourly, hourly.getRange("A5:D5"));
const hourlyIndex = new Map(records.map((record) => [record.name, new Map(record.hours.map((hour) => [hour.timestamp, hour]))]));
const timestamps = [...new Set(records.flatMap((record) => record.hours.map((hour) => hour.timestamp)))].sort();
const hourlyRows = timestamps.map((timestamp) => [hourOf(timestamp), ...records.map((record) => number(hourlyIndex.get(record.name).get(timestamp)?.energy_kwh || 0))]);
hourly.getRange(`A6:D${5 + hourlyRows.length}`).values = hourlyRows;
styleData(hourly, hourly.getRange(`A6:D${5 + hourlyRows.length}`));
hourly.getRange(`B6:D${5 + hourlyRows.length}`).format.numberFormat = "#,##0.0";
hourly.freezePanes.freezeRows(5);
addLineChart(hourly, hourly.getRange(`A5:D${5 + hourlyRows.length}`), "Saatlik net üretim karşılaştırması (kWh)", ["F5", "N24"], colors);
hourly.getRange("A:A").format.columnWidth = 16;
hourly.getRange("B:D").format.columnWidth = 22;

const actual = workbook.worksheets.add("Gerçekleşen 07.09");
title(actual, "07.09.2026 Gerçekleşen–Tahmin Karşılaştırması", "Şirketten gelecek saatlik kWh değerlerini sarı sütunlara girin. Fark ve yüzde hata otomatik hesaplanır.");
actual.tabColor = "#F59E0B";
const actualHeaders = ["Saat"];
for (const record of records) actualHeaders.push(`${record.name} tahmin`, `${record.name} gerçek`, `${record.name} fark`, `${record.name} hata`);
actual.getRange("A5:M5").values = [actualHeaders];
header(actual, actual.getRange("A5:M5"));
const actualDay = "2026-09-07";
const actualHours = timestamps.filter((timestamp) => timestamp.startsWith(actualDay));
const actualRows = actualHours.map((timestamp) => {
  const row = [timestamp.slice(11, 16)];
  for (const record of records) {
    row.push(number(hourlyIndex.get(record.name).get(timestamp)?.energy_kwh || 0), null, null, null);
  }
  return row;
});
actual.getRange(`A6:M${5 + actualRows.length}`).values = actualRows;
styleData(actual, actual.getRange(`A6:M${5 + actualRows.length}`));
for (let site = 0; site < records.length; site += 1) {
  const forecastCol = String.fromCharCode(66 + site * 4);
  const realCol = String.fromCharCode(67 + site * 4);
  const differenceCol = String.fromCharCode(68 + site * 4);
  const errorCol = String.fromCharCode(69 + site * 4);
  actual.getRange(`${realCol}6:${realCol}${5 + actualRows.length}`).format.fill = inputFill;
  actual.getRange(`${realCol}6:${realCol}${5 + actualRows.length}`).format.font = { name: font, color: "#7C5700" };
  actual.getRange(`${differenceCol}6`).formulas = [[`=IF(${realCol}6=\"\",\"\",${realCol}6-${forecastCol}6)`]];
  actual.getRange(`${differenceCol}6:${differenceCol}${5 + actualRows.length}`).fillDown();
  actual.getRange(`${errorCol}6`).formulas = [[`=IF(${realCol}6=\"\",\"\",(${realCol}6-${forecastCol}6)/${forecastCol}6)`]];
  actual.getRange(`${errorCol}6:${errorCol}${5 + actualRows.length}`).fillDown();
  actual.getRange(`${forecastCol}6:${differenceCol}${5 + actualRows.length}`).format.numberFormat = "#,##0.0";
  actual.getRange(`${errorCol}6:${errorCol}${5 + actualRows.length}`).format.numberFormat = "0.0%";
}
actual.freezePanes.freezeRows(5);
addLineChart(actual, actual.getRange(`A5:C${5 + actualRows.length}`), "Saha 1: tahmin ve gerçekleşen (kWh)", ["O5", "W22"], [colors[0], "#F59E0B"]);
actual.getRange("A:A").format.columnWidth = 11;
actual.getRange("B:M").format.columnWidth = 15;

for (const [index, record] of records.entries()) {
  const sheet = workbook.worksheets.add(record.name);
  title(sheet, `${record.name} — Saatlik Tahmin`, `${record.site.latitude_deg.toFixed(6)}, ${record.site.longitude_deg.toFixed(6)} · ${record.site.ac_capacity_kw.toLocaleString("tr-TR")} kW AC limit · ${record.site.age_years} yıl saha yaşı`);
  sheet.tabColor = colors[index];
  const total = totals(record);
  const dc = dcCapacity(record);
  sheet.getRange("A5:F5").values = [["DC güç (kWp)", "AC limit (kW)", "DC/AC", "Toplam enerji (kWh)", "Kırpma (kWh)", "Net AC tepe (kW)"]];
  header(sheet, sheet.getRange("A5:F5"));
  sheet.getRange("A6:F6").values = [[number(dc), record.site.ac_capacity_kw, number(dc / record.site.ac_capacity_kw, 3), number(total.energy), number(total.clipping), number(total.peak.average_ac_power_kw)]];
  styleData(sheet, sheet.getRange("A6:F6"));
  sheet.getRange("A6:B6").format.numberFormat = "#,##0.0";
  sheet.getRange("C6:C6").format.numberFormat = "0.000";
  sheet.getRange("D6:F6").format.numberFormat = "#,##0.0";
  sheet.getRange("A9:G9").values = [["Tarih-saat", "Net üretim (kWh)", "Net AC güç (kW)", "Kırpma öncesi AC (kW)", "Kırpma kaybı (kWh)", "GTI (W/m²)", "Hava sıcaklığı (°C)"]];
  header(sheet, sheet.getRange("A9:G9"));
  const siteRows = record.hours.map((hour) => [hour.timestamp.replace("T", " "), number(hour.energy_kwh), number(hour.average_ac_power_kw), number(hour.ac_power_before_clipping_kw), number(hour.clipping_loss_kwh), number(hour.global_tilted_irradiance_w_m2), number(hour.air_temperature_c)]);
  sheet.getRange(`A10:G${9 + siteRows.length}`).values = siteRows;
  styleData(sheet, sheet.getRange(`A10:G${9 + siteRows.length}`));
  sheet.getRange(`B10:G${9 + siteRows.length}`).format.numberFormat = "#,##0.0";
  sheet.freezePanes.freezeRows(9);
  addLineChart(sheet, sheet.getRange(`A9:D${9 + siteRows.length}`), `${record.name}: net üretim ve AC limit etkisi`, ["I5", "R24"], [colors[index], "#64748B", "#F59E0B"]);
  sheet.getRange("I26:M26").values = [["Tarih", "Günlük toplam (kWh)", "Net AC tepe (kW)", "Tepe saat", "Kırpma (kWh)"]];
  header(sheet, sheet.getRange("I26:M26"));
  const dailyRows = dailyMatrix(record).map(([day, value]) => [displayDate(day), number(value.energy), number(value.peak.average_ac_power_kw), value.peak.timestamp.slice(11, 16), number(value.clipping)]);
  sheet.getRange(`I27:M${26 + dailyRows.length}`).values = dailyRows;
  styleData(sheet, sheet.getRange(`I27:M${26 + dailyRows.length}`));
  sheet.getRange(`J27:K${26 + dailyRows.length}`).format.numberFormat = "#,##0.0";
  sheet.getRange(`M27:M${26 + dailyRows.length}`).format.numberFormat = "#,##0.0";
  sheet.getRange("A:A").format.columnWidth = 20;
  sheet.getRange("B:G").format.columnWidth = 18;
  sheet.getRange("I:M").format.columnWidth = 18;
}

await fs.mkdir(outputDir, { recursive: true });
const workbookSummary = await workbook.inspect({ kind: "workbook,sheet,table,drawing", maxChars: 12000, tableMaxRows: 5, tableMaxCols: 8 });
console.log(workbookSummary.ndjson);
const formulas = await workbook.inspect({ kind: "formula", maxChars: 12000, options: { maxResults: 200 } });
console.log(formulas.ndjson);
for (const sheet of workbook.worksheets.items) {
  const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(outputDir, `${sheet.name.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir, "uc-saha-karsilastirma_2026-09-07.xlsx"));
