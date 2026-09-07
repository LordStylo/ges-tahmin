from __future__ import annotations

import csv
import html
import io
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlencode

from .analytics import evaluate_forecast
from .comparison import TEST_SITES, calculate_metrics
from .domain import LossFactors, MountType, SiteConfig, ValidationError
from .exporters import to_csv, to_xlsx
from .model import ForecastEngine
from .open_meteo import OpenMeteoClient
from .storage import Repository


def create_app(data_directory: Path) -> Callable:
    repository = Repository(data_directory / "ges_forecast.sqlite3")
    weather_client = OpenMeteoClient(repository)
    engine = ForecastEngine()

    def app(environ: dict[str, Any], start_response: Callable) -> list[bytes]:
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "/")
        query = parse_qs(environ.get("QUERY_STRING", ""))
        try:
            if method == "GET" and path == "/":
                return _html(start_response, _layout("Yeni tahmin", _forecast_form()))
            if method == "GET" and path == "/history":
                return _html(
                    start_response,
                    _layout("Tahmin geçmişi", _history_view(repository.list_forecasts())),
                )
            if method == "GET" and path == "/comparison":
                forecast_ids = query.get("forecast_id", [])
                if not forecast_ids:
                    return _html(start_response, _layout("Üç saha karşılaştırması", _comparison_form()))
                forecasts = [repository.get_forecast(forecast_id) for forecast_id in forecast_ids]
                if len(forecasts) != 3 or any(forecast is None for forecast in forecasts):
                    raise ValidationError("Karşılaştırma için üç geçerli tahmin sürümü gerekir.")
                return _html(start_response, _layout("Üç saha karşılaştırması", _comparison_view(forecasts)))
            if method == "POST" and path == "/comparison":
                form = _parse_form(environ)
                forecast_ids = _run_test_site_comparison(form, weather_client, engine, repository)
                return _redirect(start_response, f"/comparison?{urlencode([('forecast_id', value) for value in forecast_ids])}")
            if method == "POST" and path == "/forecast":
                form = _parse_form(environ)
                site = _site_from_form(form)
                days = _integer(form, "forecast_days", 7)
                start_date, end_date = form.get("historical_start_date", "").strip(), form.get("historical_end_date", "").strip()
                if bool(start_date) != bool(end_date):
                    raise ValidationError("Geçmiş doğrulama için başlangıç ve bitiş tarihi birlikte girilmelidir.")
                result = weather_client.historical(site, start_date, end_date) if start_date else weather_client.forecast(site, days)
                hours = engine.forecast(site, result.hours)
                site_id, forecast_id = repository.save_forecast(site, hours, result.source, result.age_minutes)
                scenario_id = ""
                scenario_tilt = form.get("scenario_tilt_deg", "").strip()
                if scenario_tilt:
                    scenario_site = replace(
                        site,
                        name=f"{site.name} - senaryo",
                        tilt_deg=float(scenario_tilt),
                        azimuth_compass_deg=float(form.get("scenario_azimuth_compass_deg") or site.azimuth_compass_deg),
                    )
                    scenario_result = weather_client.historical(scenario_site, start_date, end_date) if start_date else weather_client.forecast(scenario_site, days)
                    scenario_hours = engine.forecast(scenario_site, scenario_result.hours)
                    _, scenario_id = repository.save_forecast(
                        scenario_site, scenario_hours, scenario_result.source, scenario_result.age_minutes
                    )
                return _redirect(start_response, f"/forecast/{forecast_id}" + (f"?scenario_id={scenario_id}" if scenario_id else ""))
            if method == "GET" and path.startswith("/forecast/"):
                forecast_id = path.rsplit("/", 1)[-1]
                forecast = repository.get_forecast(forecast_id)
                if forecast is None:
                    return _html(start_response, _layout("Bulunamadı", "<p>Tahmin bulunamadı.</p>"), "404 Not Found")
                scenario = repository.get_forecast(query.get("scenario_id", [""])[0])
                scenario_html = _scenario_summary_from_records(forecast, scenario) if scenario else ""
                return _html(start_response, _layout("Tahmin sonucu", _forecast_result(forecast, scenario_html)))
            if method == "GET" and path == "/export.csv":
                return _export(start_response, repository, query, "csv")
            if method == "GET" and path == "/export.xlsx":
                return _export(start_response, repository, query, "xlsx")
            if method == "GET" and path == "/actuals":
                forecast = _required_forecast(repository, query)
                return _html(start_response, _layout("Gerçekleşen üretim", _actuals_form(forecast)))
            if method == "POST" and path == "/actuals":
                form = _parse_form(environ)
                forecast = repository.get_forecast(form["forecast_id"])
                if forecast is None:
                    raise ValidationError("Tahmin bulunamadı.")
                count = repository.save_actuals(forecast["site_id"], _parse_actual_csv(form["actuals_csv"]))
                return _redirect(start_response, f"/analysis?forecast_id={forecast['id']}&saved={count}")
            if method == "GET" and path == "/analysis":
                forecast = _required_forecast(repository, query)
                actuals = repository.get_actuals(forecast["site_id"])
                report = evaluate_forecast(forecast["hours"], actuals, forecast["site"]["panel_count"] * forecast["site"]["panel_power_wp"] / 1000)
                return _html(start_response, _layout("Doğruluk analizi", _analysis_view(forecast, report)))
            if method == "GET" and path == "/api/locations":
                locations = weather_client.geocode(query.get("query", [""])[0])
                return _json(start_response, {"results": locations})
            if method == "GET" and path == "/health":
                return _json(start_response, {"status": "ok"})
            return _html(start_response, _layout("Bulunamadı", "<p>Sayfa bulunamadı.</p>"), "404 Not Found")
        except (ValidationError, ValueError) as exc:
            return _html(start_response, _layout("Girdi hatası", f"<p class='error'>{html.escape(str(exc))}</p><p><a href='/'>Forma dön</a></p>"), "400 Bad Request")
        except RuntimeError as exc:
            return _html(start_response, _layout("Veri kaynağı hatası", f"<p class='error'>{html.escape(str(exc))}</p>"), "503 Service Unavailable")

    return app


def _forecast_form() -> str:
    location_fields = "".join([
        _input("name", "Saha adı", "Saha 1", "text", "", "Tahminleri ayırt etmek için kısa ve açıklayıcı bir ad.", True),
        _input("latitude_deg", "Enlem", "37.075739", "number", "min='-90' max='90' step='0.000001'", "Konumdan otomatik doldurulabilir.", True),
        _input("longitude_deg", "Boylam", "36.804529", "number", "min='-180' max='180' step='0.000001'", "Konumdan otomatik doldurulabilir.", True),
        _input("elevation_m", "Rakım (m)", "", "number", "step='1'", "İsteğe bağlı; konum araması sonuç verirse otomatik dolar.", False),
    ])
    equipment_fields = "".join([
        _input("panel_count", "Panel adedi", "91327", "number", "min='1' step='1'", "DC kurulu güç bununla hesaplanır.", True),
        _input("panel_power_wp", "Panel tekil gücü (Wp)", "550", "number", "min='0.1' step='0.1'", "Panelin etiket gücü.", True),
        _input("ac_capacity_kw", "Toplam AC güç (kW)", "39700", "number", "min='0.1' step='0.1'", "İnverterlerin toplam çıkış sınırı; kırpma bu değerde olur.", True),
        _input("age_years", "Saha yaşı (yıl)", "2", "number", "min='0' step='1'", "Yaşlanma düzeltmesi için kullanılır.", True),
    ])
    geometry_fields = "".join([
        _input("tilt_deg", "Panel eğimi (°)", "20", "number", "min='0' max='90' step='0.1'", "0° yatay, 90° dikeydir.", True),
        _input("azimuth_compass_deg", "Panel azimutu (°)", "180", "number", "min='0' max='359.999' step='0.1'", "Pusula referansı: Kuzey 0°, Doğu 90°, Güney 180°.", True),
        _input("forecast_days", "Tahmin ufku (gün)", "7", "number", "min='1' max='16' step='1'", "Open-Meteo en fazla 16 günlük tahmin sunar.", True),
        "<label class='field'><span>Montaj tipi</span><select name='mount_type'><option value='ground'>Arazi</option><option value='roof'>Çatı</option><option value='tracker'>İzleyici</option></select><small>Soğuma davranışını etkiler.</small></label>",
    ])
    advanced_fields = "".join([
        _input("temperature_coefficient_per_c", "Sıcaklık katsayısı (1/°C)", "-0.004", "number", "max='0' step='0.0001'", "Panel ısındıkça üretim düşer; negatif olmalıdır.", False),
        _input("soiling_pct", "Kirlenme kaybı (%)", "2", "number", "min='0' max='99' step='0.1'", "Varsayılan: %2.", False),
        _input("shading_pct", "Gölgeleme kaybı (%)", "0", "number", "min='0' max='99' step='0.1'", "Varsayılan: %0.", False),
        _input("dc_cable_pct", "DC kablo kaybı (%)", "1.5", "number", "min='0' max='99' step='0.1'", "Varsayılan: %1,5.", False),
        _input("ac_cable_pct", "AC kablo kaybı (%)", "1", "number", "min='0' max='99' step='0.1'", "Varsayılan: %1.", False),
        _input("transformer_pct", "Trafo kaybı (%)", "1", "number", "min='0' max='99' step='0.1'", "Varsayılan: %1.", False),
        _input("scenario_tilt_deg", "Senaryo eğimi (°)", "", "number", "min='0' max='90' step='0.1'", "Temel tahminle karşılaştırmak için isteğe bağlıdır.", False),
        _input("scenario_azimuth_compass_deg", "Senaryo azimutu (°)", "", "number", "min='0' max='359.999' step='0.1'", "Boş bırakılırsa temel azimut korunur.", False),
        _input("historical_start_date", "Geçmiş başlangıç", "", "date", "", "Doğruluk doğrulaması için bitiş tarihiyle birlikte girin.", False),
        _input("historical_end_date", "Geçmiş bitiş", "", "date", "", "Tahmin yerine geçmiş meteoroloji serisi kullanılır.", False),
    ])
    return f"""
    <section class='intro-card'><div><p class='eyebrow'>Adım adım tahmin</p><h3>Önce sahayı tanımlayın, modeli gerektiğinde detaylandırın.</h3><p>Temel alanlar yeterlidir. Gelişmiş kayıplar ve senaryo ayarları varsayılan değerleriyle kapalı başlar.</p></div><div class='source-note'><b>Veri kaynağı</b><span>Open-Meteo · saatlik ışınım, sıcaklık ve rüzgâr</span><a href='/comparison' style='color:white;font-size:.84rem'>Üç saha karşılaştır →</a><a href='/history' style='color:white;font-size:.84rem'>Tahmin geçmişi →</a></div></section>
    <form method='post' action='/forecast' class='forecast-form'>
      <section class='form-section'><div class='section-title'><span class='step'>1</span><div><h3>Konum ve saha kimliği</h3><p>Konumu aratarak koordinat ve rakımı otomatik doldurabilirsiniz.</p></div></div>
        <div class='location-search'><label class='field grow'><span>İl / ilçe ara</span><input id='location-query' placeholder='Örn. Kahramanmaraş, Türkiye' autocomplete='off'><small id='location-status'>Koordinat girmeyi tercih ederseniz bu adımı atlayın.</small></label><button class='secondary' type='button' onclick='findLocation()'>Konumu bul</button></div>
        <div class='form-grid'>{location_fields}</div>
      </section>
      <section class='form-section'><div class='section-title'><span class='step'>2</span><div><h3>Kurulu güç</h3><p>Bu bilgiler DC/AC oranını ve inverter kırpma sınırını belirler.</p></div></div><div class='form-grid'>{equipment_fields}</div></section>
      <section class='form-section'><div class='section-title'><span class='step'>3</span><div><h3>Panel yerleşimi ve tahmin</h3><p>Azimut her zaman pusula yönüdür; güney yönü 180°'dir.</p></div></div><div class='form-grid'>{geometry_fields}</div></section>
      <aside class='estimator' aria-live='polite'><div><span>Hesaplanan DC kurulu güç</span><strong id='dc-capacity'>—</strong></div><div><span>DC / AC oranı</span><strong id='dc-ac-ratio'>—</strong></div><p id='ratio-guidance'>Panel ve AC güç değerlerini girin.</p></aside>
      <details class='advanced'><summary><span>Gelişmiş model, senaryo ve geçmiş doğrulama</span><small>İsteğe bağlı · varsayılanlar güvenli başlangıç değerleriyle kullanılır</small></summary><div class='form-grid advanced-grid'>{advanced_fields}</div></details>
      <div class='submit-row'><div><b>Tahmin üretmeye hazır</b><span>İstek önce yerel önbelleği kontrol eder; aynı sorgu tekrar servise gönderilmez.</span></div><button class='primary' type='submit'>Tahmin üret <span aria-hidden='true'>→</span></button></div>
    </form>
    <script>
      function estimate() {{
        const count=Number(document.getElementById('panel_count').value)||0;
        const panel=Number(document.getElementById('panel_power_wp').value)||0;
        const ac=Number(document.getElementById('ac_capacity_kw').value)||0;
        const dc=count*panel/1000; const ratio=ac ? dc/ac : 0;
        document.getElementById('dc-capacity').textContent=dc ? dc.toLocaleString('tr-TR',{{maximumFractionDigits:1}})+' kWp' : '—';
        document.getElementById('dc-ac-ratio').textContent=ratio ? ratio.toFixed(3) : '—';
        document.getElementById('ratio-guidance').textContent=!ratio ? 'Panel ve AC güç değerlerini girin.' : ratio < 1 ? 'DC/AC oranı 1’in altında; panel veya AC gücü kontrol edin.' : ratio > 1.5 ? 'Yüksek DC/AC oranı: kırpma davranışını özellikle inceleyin.' : 'Oran izlenebilir durumda; kırpma kaybı sonuçta ayrıca raporlanacak.';
      }}
      async function findLocation() {{
        const status=document.getElementById('location-status'); const q=document.getElementById('location-query').value.trim();
        if(q.length<2) {{status.textContent='Arama için en az iki karakter girin.'; return;}}
        status.textContent='Konum aranıyor…';
        try {{const r=await fetch('/api/locations?query='+encodeURIComponent(q)); const d=await r.json(); if(!d.results?.length) {{status.textContent='Konum bulunamadı; koordinatları manuel girebilirsiniz.'; return;}} const x=d.results[0]; document.getElementById('latitude_deg').value=x.latitude; document.getElementById('longitude_deg').value=x.longitude; document.getElementById('elevation_m').value=x.elevation ?? ''; status.textContent=x.name+' seçildi · '+(x.elevation ?? 'rakım bilinmiyor')+' m · '+(x.timezone ?? 'saat dilimi bilinmiyor');}} catch(_) {{status.textContent='Konum servisine ulaşılamadı; koordinatları manuel girebilirsiniz.';}}
      }}
      ['panel_count','panel_power_wp','ac_capacity_kw'].forEach(id=>document.getElementById(id).addEventListener('input',estimate)); estimate();
    </script>"""


def _comparison_form() -> str:
    previous_year = date.today().year - 1
    return f"""<style>
      .button-link{{display:inline-block;padding:.55rem .75rem;border:1px solid rgba(255,255,255,.3);border-radius:.55rem;color:white;white-space:nowrap}}.button-link:hover{{background:rgba(255,255,255,.12);text-decoration:none}}
      .comparison-hero{{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;background:linear-gradient(135deg,#12376d,#155eef);color:white;border-radius:1rem;padding:1.35rem 1.45rem;margin-bottom:1.2rem;box-shadow:0 14px 30px rgba(19,55,109,.15)}}.comparison-hero p{{color:#dbeafe;margin:.3rem 0 0}}.comparison-hero h3{{font-size:1.35rem}}.comparison-panel{{background:#fff;border:1px solid #d9e2ee;border-radius:.9rem;padding:1.2rem;box-shadow:0 5px 18px rgba(16,35,63,.04);margin-top:1rem}}.test-site-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem}}.test-site{{border:1px solid #d9e2ee;border-radius:.75rem;padding:.9rem}}.test-site p{{margin:.2rem 0;font-size:.84rem}}.comparison-form{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;align-items:end}}.comparison-form label{{display:grid;gap:.32rem;font-weight:750;font-size:.9rem}}.comparison-form small{{font-weight:500;color:#5b6b82;font-size:.77rem}}.comparison-form button{{height:fit-content}}@media(max-width:760px){{.test-site-grid,.comparison-form{{grid-template-columns:1fr}}.comparison-hero{{flex-direction:column}}}}
    </style>
    <section class='comparison-hero'><div><p class='eyebrow'>Ek A kabul testi</p><h3>Üç gerçek saha, tek işlem ve izlenebilir sonuç.</h3><p>Ham saha değerleri sabittir. Güney yönü (180°), arazi montajı ve varsayılan kayıp katsayıları tüm sahalarda açıkça uygulanır.</p></div><a class='button-link light-link' href='/history'>Tahmin geçmişi</a></section>
    <section class='comparison-panel'><div class='panel-heading'><div><h3>Ek A test sahaları</h3><p>Kurulu DC güç ve DC/AC oranları uygulama tarafından hesaplanır.</p></div></div><div class='test-site-grid'>{''.join(_test_site_card(site) for site in TEST_SITES)}</div></section>
    <section class='comparison-panel'><h3>Karşılaştırma dönemi</h3><p>Yıllık kırpma kaybı için tamamlanmış takvim yılı seçin. Gelecek tahmin seçeneği kısa dönem operasyon görünümü içindir.</p><form class='comparison-form' method='post' action='/comparison'><label><span>Çalışma türü</span><select name='mode'><option value='forecast'>Gelecek tahmini</option><option value='annual'>Tamamlanmış takvim yılı</option></select><small>Her saha için yalnızca bir meteoroloji isteği yapılır; tekrar çalıştırmalarda yerel önbellek kullanılır.</small></label><label><span>Tahmin günü / yıl</span><input name='forecast_days' type='number' min='1' max='16' value='7'><small>Yıllık modda aşağıdaki yıl kullanılır.</small></label><label><span>Yıllık karşılaştırma yılı</span><input name='historical_year' type='number' min='1940' max='{previous_year}' value='{previous_year}'><small>1 Ocak - 31 Aralık aralığı hesaplanır.</small></label><button class='primary' type='submit'>Üç sahayı karşılaştır →</button></form></section>"""


def _test_site_card(site: SiteConfig) -> str:
    return f"""<article class='test-site'><b>{html.escape(site.name)}</b><p>{site.latitude_deg:.6f}, {site.longitude_deg:.6f}</p><p>{site.panel_count:,} panel · {site.panel_power_wp:.0f} Wp</p><p>{site.tilt_deg:.0f}° eğim · {site.age_years} yıl · {site.ac_capacity_kw:,.0f} kW AC</p></article>"""


def _run_test_site_comparison(
    form: dict[str, str], weather_client: OpenMeteoClient, engine: ForecastEngine, repository: Repository
) -> list[str]:
    mode = form.get("mode", "forecast")
    if mode == "forecast":
        days = _integer(form, "forecast_days", 7)
        fetch_weather = lambda site: weather_client.forecast(site, days)
    elif mode == "annual":
        year = _integer(form, "historical_year", date.today().year - 1)
        if not 1940 <= year < date.today().year:
            raise ValidationError("Yıllık karşılaştırma için tamamlanmış bir takvim yılı seçin.")
        start_date, end_date = f"{year}-01-01", f"{year}-12-31"
        fetch_weather = lambda site: weather_client.historical(site, start_date, end_date)
    else:
        raise ValidationError("Geçersiz karşılaştırma türü.")

    with ThreadPoolExecutor(max_workers=len(TEST_SITES)) as executor:
        weather_results = list(executor.map(fetch_weather, TEST_SITES))

    forecast_ids: list[str] = []
    for site, result in zip(TEST_SITES, weather_results, strict=True):
        hours = engine.forecast(site, result.hours)
        _, forecast_id = repository.save_forecast(site, hours, result.source, result.age_minutes)
        forecast_ids.append(forecast_id)
    return forecast_ids


def _comparison_view(forecasts: list[dict[str, Any] | None]) -> str:
    records = [forecast for forecast in forecasts if forecast is not None]
    rows: list[tuple[dict[str, Any], Any]] = []
    for forecast in records:
        dc_capacity = forecast["site"]["panel_count"] * forecast["site"]["panel_power_wp"] / 1000
        rows.append((forecast, calculate_metrics(dc_capacity, forecast["hours"])))

    metrics_rows = "".join(
        f"""<tr><td><b>{html.escape(forecast['name'])}</b><small>Sürüm {forecast['id'][:8]}</small></td><td>{dc_capacity:,.1f}</td><td>{forecast['site']['ac_capacity_kw']:,.1f}</td><td>{dc_capacity / forecast['site']['ac_capacity_kw']:.3f}</td><td>{metrics.total_energy_kwh:,.1f}</td><td>{metrics.specific_yield_kwh_per_kwp:.3f}</td><td>{metrics.clipping_loss_kwh:,.1f}<small>%{metrics.clipping_loss_pct:.3f}</small></td><td>%{metrics.aging_loss_pct:.3f}</td><td>{html.escape(metrics.peak_timestamp or '—')}</td><td class='table-actions'><a href='/forecast/{forecast['id']}'>Aç</a><a href='/actuals?forecast_id={forecast['id']}'>Gerçekleşen</a><a href='/analysis?forecast_id={forecast['id']}'>Analiz</a></td></tr>"""
        for (forecast, metrics), dc_capacity in ((row, row[0]['site']['panel_count'] * row[0]['site']['panel_power_wp'] / 1000) for row in rows)
    )
    curve_day = _comparison_curve_day(records)
    monthly_rows = _monthly_clipping_rows(rows)
    by_age = sorted(rows, key=lambda row: row[0]["site"]["age_years"])
    return f"""<style>
      .button-link{{display:inline-block;padding:.55rem .75rem;border:1px solid rgba(255,255,255,.3);border-radius:.55rem;color:white;white-space:nowrap}}.button-link:hover{{background:rgba(255,255,255,.12);text-decoration:none}}.comparison-hero,.comparison-panel{{background:#fff;border:1px solid #d9e2ee;border-radius:.9rem;padding:1.2rem;box-shadow:0 5px 18px rgba(16,35,63,.04);margin-bottom:1rem}}.comparison-hero{{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;background:linear-gradient(135deg,#12376d,#155eef);color:white}}.comparison-hero p{{color:#dbeafe;margin:.3rem 0 0}}.comparison-hero h3{{font-size:1.35rem}}.comparison-table td small{{display:block;color:#5b6b82;font-size:.76rem;margin-top:.15rem}}.comparison-table .table-actions{{white-space:nowrap}}.table-actions a{{margin-left:.55rem;font-size:.82rem}}.table-actions a:first-child{{margin-left:0}}.comparison-note{{font-size:.86rem;background:#edf4ff;border-radius:.65rem;padding:.75rem 1rem}}@media(max-width:560px){{.comparison-hero{{flex-direction:column}}}}
    </style><section class='comparison-hero'><div><p class='eyebrow'>Karşılaştırma tamamlandı</p><h3>Üç saha aynı çalışma içinde hesaplandı.</h3><p>{len(records[0]['hours'])} saat · Her sonuç ayrı sürüm olarak kaydedildi.</p></div><a class='button-link light-link' href='/comparison'>Yeni karşılaştırma</a></section>
    <section class='comparison-panel'><div class='panel-heading'><div><h3>Kurulu güç, üretim ve kayıp karşılaştırması</h3><p>Kırpma yüzdesi, kırpma öncesi AC enerjiye göre hesaplanır. Yıllık modda bu değer yıllık kayıptır.</p></div></div><div class='scroll'><table class='comparison-table'><thead><tr><th>Saha</th><th>DC (kWp)</th><th>AC (kW)</th><th>DC/AC</th><th>Enerji (kWh)</th><th>Spesifik üretim<br>kWh/kWp</th><th>Kırpma kaybı</th><th>Yaşlanma kaybı</th><th>Tepe zaman</th><th>İşlem</th></tr></thead><tbody>{metrics_rows}</tbody></table></div><p class='comparison-note'>Yaşlanma sıralaması: <b>{html.escape(by_age[0][0]['name'])}</b> ({by_age[0][0]['site']['age_years']} yıl) en düşük; <b>{html.escape(by_age[-1][0]['name'])}</b> ({by_age[-1][0]['site']['age_years']} yıl) en yüksek yaşlanma kaybına sahiptir. İlk yıl ve takip eden yıllar modelde ayrı katsayılarla hesaplanır.</p></section>
    <section class='comparison-panel'><div class='panel-heading'><div><h3>Aynı gün için üretim eğrileri</h3><p>{html.escape(curve_day)} gününün üç saha eğrisi. Tepe saatlerdeki kayma, konum, eğim ve hava koşullarının bileşik etkisini görünür kılar.</p></div></div>{_comparison_svg_chart(records, curve_day)}</section>
    <section class='comparison-panel'><div class='panel-heading'><div><h3>Kırpma kaybının aylara dağılımı</h3><p>Yıllık modda tepe ayı ve nedenini değerlendirmek için kullanın; kısa tahminde yalnızca kapsanan aylar görünür.</p></div></div><div class='scroll'><table class='comparison-table'><thead><tr><th>Ay</th><th>{html.escape(records[0]['name'])}</th><th>{html.escape(records[1]['name'])}</th><th>{html.escape(records[2]['name'])}</th></tr></thead><tbody>{monthly_rows}</tbody></table></div></section>"""


def _comparison_curve_day(records: list[dict[str, Any]]) -> str:
    daily_energy: dict[str, float] = {}
    for record in records:
        for hour in record["hours"]:
            day = hour["timestamp"][:10]
            daily_energy[day] = daily_energy.get(day, 0.0) + hour["energy_kwh"]
    return max(daily_energy, key=daily_energy.get) if daily_energy else ""


def _comparison_svg_chart(records: list[dict[str, Any]], day: str) -> str:
    series = [[hour for hour in record["hours"] if hour["timestamp"].startswith(day)] for record in records]
    values = [hour["energy_kwh"] for hours in series for hour in hours]
    if not values:
        return "<p>Seçili gün için saatlik veri yok.</p>"
    width, height, maximum = 900, 260, max(max(values), 1)
    colors = ("#155eef", "#f59e0b", "#0f9d72")
    lines = "".join(
        f"<polyline fill='none' stroke='{color}' stroke-width='3' points='{' '.join(f'{index * width / max(len(hours)-1, 1):.1f},{height - hour['energy_kwh'] / maximum * (height-24):.1f}' for index, hour in enumerate(hours))}'/>"
        for hours, color in zip(series, colors, strict=True)
    )
    legend = " · ".join(f"<span style='color:{color}'>●</span> {html.escape(record['name'])}" for record, color in zip(records, colors, strict=True))
    return f"<svg class='chart' viewBox='0 0 {width} {height}' role='img' aria-label='Üç sahanın aynı gün üretim eğrileri'>{lines}</svg><p class='legend'>{legend}</p>"


def _monthly_clipping_rows(rows: list[tuple[dict[str, Any], Any]]) -> str:
    months = sorted({month for _, metrics in rows for month in metrics.monthly_clipping_kwh})
    return "".join(
        f"<tr><td>{month}</td>{''.join(f'<td>{metrics.monthly_clipping_kwh.get(month, 0.0):,.1f} kWh</td>' for _, metrics in rows)}</tr>"
        for month in months
    ) or "<tr><td colspan='4'>Kırpma verisi yok.</td></tr>"


def _input(name: str, label: str, value: str, input_type: str, attributes: str, hint: str, required: bool) -> str:
    required_attribute = " required" if required else ""
    value_attribute = "" if input_type == "date" else f" value='{value}'"
    return f"<label class='field'><span>{label}</span><input id='{name}' name='{name}' type='{input_type}'{value_attribute} {attributes}{required_attribute}><small>{hint}</small></label>"


def _forecast_result(forecast: dict[str, Any], scenario_html: str) -> str:
    hours = forecast["hours"]
    total = sum(h["energy_kwh"] for h in hours)
    peak = max((h["average_ac_power_kw"] for h in hours), default=0)
    clipping = sum(h["clipping_loss_kwh"] for h in hours)
    warning = ""
    if forecast["weather_source"] == "stale_cache":
        warning = f"<p class='warning'>Open-Meteo erişilemedi. Önbellekteki veri kullanıldı; veri yaşı: {forecast['weather_age_minutes']:.0f} dakika.</p>"
    hourly_rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(_format(value))}</td>" for value in (
            h["timestamp"], h["energy_kwh"], h["average_ac_power_kw"], h["global_tilted_irradiance_w_m2"],
            h["air_temperature_c"], h["cell_temperature_c"], h["clipping_loss_kwh"],
        )) + "</tr>" for h in hours
    )
    daily_rows = "".join(f"<tr><td>{day}</td><td>{values['energy_kwh']:.1f}</td><td>{values['peak_kw']:.1f}</td><td>{values['clipping_kwh']:.1f}</td></tr>" for day, values in _daily_summary(hours).items())
    source_label = {
        "fresh_cache": "Önbellekten güncel veri",
        "open_meteo": "Canlı veri alındı",
        "stale_cache": "Eski önbellek verisi",
    }.get(forecast["weather_source"], "Yerel doğrulama verisi")
    return f"""<section class='result-hero'><div><p class='eyebrow'>Tahmin tamamlandı</p><h3>{html.escape(forecast['name'])}</h3><p>{len(hours)} saatlik hesaplama · Tahmin sürümü: <code>{forecast['id'][:8]}</code></p></div><div class='result-status'><b>{source_label}</b><span>Veri yaşı: {forecast['weather_age_minutes']:.0f} dakika</span></div></section>{warning}
    <section class='cards metric-cards'><div><b>Toplam enerji</b><span>{total:.1f} <small>kWh</small></span></div><div><b>Tepe güç</b><span>{peak:.1f} <small>kW</small></span></div><div><b>Kırpma kaybı</b><span>{clipping:.1f} <small>kWh</small></span></div><div><b>DC / AC</b><span>{forecast['site']['panel_count'] * forecast['site']['panel_power_wp'] / 1000 / forecast['site']['ac_capacity_kw']:.3f}</span></div></section>
    <nav class='action-links'><a href='/comparison'>Üç saha karşılaştır</a><a href='/history'>Tahmin geçmişi</a><a href='/export.csv?forecast_id={forecast['id']}'>CSV indir</a><a href='/export.xlsx?forecast_id={forecast['id']}'>Excel indir</a><a href='/actuals?forecast_id={forecast['id']}'>Gerçekleşen üretim yükle</a><a href='/analysis?forecast_id={forecast['id']}'>Doğruluk analizi</a></nav>
    <section class='chart-panel'><div class='panel-heading'><div><h3>Gün içi üretim profili</h3><p>Enerji ve eğik yüzey ışınımı aynı zaman ekseninde gösterilir.</p></div><span class='source-badge'>{html.escape(forecast['weather_source'])}</span></div>{_svg_chart(hours)}</section>
    <details class='details-panel' open><summary>Günlük özet <span>{len(_daily_summary(hours))} gün</span></summary><div class='scroll'><table><thead><tr><th>Tarih</th><th>Enerji (kWh)</th><th>Tepe güç (kW)</th><th>Kırpma (kWh)</th></tr></thead><tbody>{daily_rows}</tbody></table></div></details>
    {scenario_html}
    <details class='details-panel'><summary>Saatlik hesap ayrıntıları <span>{len(hours)} satır</span></summary><p class='details-note'>GTI, sıcaklıklar ve kırpma bu tabloda izlenebilir; CSV/Excel çıktısı daha fazla ara değeri içerir.</p><div class='scroll'><table><thead><tr><th>Zaman</th><th>Enerji (kWh)</th><th>Güç (kW)</th><th>GTI (W/m²)</th><th>Hava (°C)</th><th>Hücre (°C)</th><th>Kırpma (kWh)</th></tr></thead><tbody>{hourly_rows}</tbody></table></div></details>
    <p class='attribution'>Kaynak: {html.escape(forecast['weather_source'])}. Open-Meteo verisi CC BY 4.0; Open-Meteo ve Copernicus atfı gereklidir.</p>"""


def _daily_summary(hours: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    days: dict[str, dict[str, float]] = {}
    for hour in hours:
        day = hour["timestamp"][:10]
        values = days.setdefault(day, {"energy_kwh": 0.0, "peak_kw": 0.0, "clipping_kwh": 0.0})
        values["energy_kwh"] += hour["energy_kwh"]
        values["peak_kw"] = max(values["peak_kw"], hour["average_ac_power_kw"])
        values["clipping_kwh"] += hour["clipping_loss_kwh"]
    return days


def _svg_chart(hours: list[dict[str, Any]]) -> str:
    if not hours:
        return ""
    width, height = 900, 240
    max_energy = max(max(h["energy_kwh"] for h in hours), 1)
    max_gti = max(max(h["global_tilted_irradiance_w_m2"] for h in hours), 1)
    def points(key: str, maximum: float) -> str:
        return " ".join(f"{i * width / max(len(hours)-1, 1):.1f},{height - h[key] / maximum * (height-20):.1f}" for i, h in enumerate(hours))
    return f"<svg class='chart' viewBox='0 0 {width} {height}' role='img' aria-label='Enerji ve ışınım eğrileri'><polyline fill='none' stroke='#1d4ed8' stroke-width='3' points='{points('energy_kwh', max_energy)}'/><polyline fill='none' stroke='#f59e0b' stroke-width='3' points='{points('global_tilted_irradiance_w_m2', max_gti)}'/></svg><p class='legend'>Mavi: enerji (kWh) · Turuncu: eğik yüzey ışınımı (W/m²)</p>"


def _scenario_summary(base: list[Any], scenario: list[Any], scenario_id: str) -> str:
    base_total = sum(item.energy_kwh for item in base)
    scenario_total = sum(item.energy_kwh for item in scenario)
    return f"<section><h2>Senaryo karşılaştırması</h2><p>Senaryo toplamı: {scenario_total:.1f} kWh; temel senaryoya farkı: {scenario_total-base_total:+.1f} kWh. <a href='/forecast/{scenario_id}'>Senaryoyu aç</a></p></section>"


def _scenario_summary_from_records(base: dict[str, Any], scenario: dict[str, Any]) -> str:
    base_total = sum(item["energy_kwh"] for item in base["hours"])
    scenario_total = sum(item["energy_kwh"] for item in scenario["hours"])
    return f"<section><h2>Senaryo karşılaştırması</h2><p>Senaryo toplamı: {scenario_total:.1f} kWh; temel senaryoya farkı: {scenario_total-base_total:+.1f} kWh. <a href='/forecast/{scenario['id']}'>Senaryoyu aç</a></p></section>"


def _actuals_form(forecast: dict[str, Any]) -> str:
    return f"""<p>CSV biçimi: <code>timestamp,energy_kwh</code>. Zaman damgası tahmin tablosundaki ISO değerleriyle aynı olmalıdır.</p>
    <form method='post' action='/actuals'><input type='hidden' name='forecast_id' value='{forecast['id']}'><label>Gerçekleşen üretim CSV metni<textarea name='actuals_csv' rows='14' required>timestamp,energy_kwh
</textarea></label><button>Kaydet ve analiz et</button></form>"""


def _history_view(items: list[dict[str, Any]]) -> str:
    styles = """<style>
      .history-hero{display:flex;gap:1rem;justify-content:space-between;align-items:flex-start;background:linear-gradient(135deg,#12376d,#155eef);color:white;border-radius:1rem;padding:1.35rem 1.45rem;margin-bottom:1.2rem;box-shadow:0 14px 30px rgba(19,55,109,.15)}
      .history-hero p{color:#dbeafe;margin:.3rem 0 0}.history-hero h3{font-size:1.35rem}.button-link{display:inline-block;padding:.55rem .75rem;border:1px solid #d9e2ee;border-radius:.55rem;background:#fff;color:#12376d;font-size:.87rem}.light-link{background:rgba(255,255,255,.13);border-color:rgba(255,255,255,.3);color:white;white-space:nowrap}.history-panel,.empty-state{background:#fff;border:1px solid #d9e2ee;border-radius:.9rem;padding:1.2rem;box-shadow:0 5px 18px rgba(16,35,63,.04)}.history-count{background:#eef3fb;color:#12376d;padding:.3rem .55rem;border-radius:999px;font-size:.75rem;font-weight:800;white-space:nowrap}.history-table td small{display:block;color:#5b6b82;font-size:.76rem;margin-top:.15rem}.history-table .table-actions{white-space:nowrap}.table-actions a{margin-left:.55rem;font-size:.82rem}.table-actions a:first-child{margin-left:0}@media(max-width:560px){.history-hero{flex-direction:column}.history-hero .button-link{width:100%;text-align:center}}
    </style>"""
    if not items:
        return f"""{styles}<section class='empty-state'><p class='eyebrow'>Henüz kayıt yok</p><h3>İlk tahmininizi oluşturun.</h3><p>Her tahmin ayrı bir sürüm olarak SQLite'a kaydedilir. Böylece aynı saat için zaman içinde üretilen tahminleri karşılaştırabilirsiniz.</p><a class='button-link' href='/'>Yeni tahmin oluştur</a></section>"""

    rows = "".join(
        f"""<tr><td><b>{html.escape(item['name'])}</b><small>Sürüm {item['id'][:8]}</small></td>
        <td>{_format_history_timestamp(item['generated_at_utc'])}</td>
        <td>{html.escape(str(item['first_hour_local'] or '—'))}<small>{html.escape(str(item['last_hour_local'] or '—'))}</small></td>
        <td>{item['hour_count']} saat</td>
        <td><span class='source-badge'>{html.escape(item['weather_source'])}</span></td>
        <td class='table-actions'><a href='/forecast/{item['id']}'>Aç</a><a href='/export.csv?forecast_id={item['id']}'>CSV</a><a href='/analysis?forecast_id={item['id']}'>Analiz</a></td></tr>"""
        for item in items
    )
    return f"""{styles}<section class='history-hero'><div><p class='eyebrow'>Sürümlü kayıtlar</p><h3>Her tahmin korunur, üzerine yazılmaz.</h3><p>En yeni {len(items)} kayıt gösteriliyor. Sonuçları açabilir, dışa aktarabilir veya gerçekleşen üretimle analiz edebilirsiniz.</p></div><a class='button-link light-link' href='/'>+ Yeni tahmin</a></section>
    <section class='history-panel'><div class='panel-heading'><div><h3>Kayıtlı tahminler</h3><p>Oluşturulma zamanı UTC'dir; tahmin aralığı uygulanan yerel saat dilimindedir.</p></div><span class='history-count'>{len(items)} sürüm</span></div><div class='scroll'><table class='history-table'><thead><tr><th>Saha / sürüm</th><th>Oluşturulma</th><th>Tahmin aralığı</th><th>Kapsam</th><th>Veri kaynağı</th><th>İşlem</th></tr></thead><tbody>{rows}</tbody></table></div></section>"""


def _format_history_timestamp(value: str) -> str:
    return value.replace("T", " ").replace("+00:00", " UTC")


def _analysis_view(forecast: dict[str, Any], report: Any) -> str:
    baseline = "Yeterli önceki gün verisi yok." if report.baseline_mae_kwh is None else f"{report.baseline_mae_kwh:.3f} kWh"
    return f"""<section class='cards'><div><b>Eşleşen saat</b><span>{report.matched_hours}</span></div><div><b>MAE</b><span>{report.mae_kwh:.3f} kWh</span></div><div><b>RMSE</b><span>{report.rmse_kwh:.3f} kWh</span></div><div><b>Ortalama sapma</b><span>{report.mean_bias_kwh:+.3f} kWh</span></div><div><b>Normalize MAE</b><span>{report.normalized_mae_pct_dc:.3f}% DC</span></div><div><b>Dünkü üretim tabanı MAE</b><span>{baseline}</span></div></section>
    <h2>Saat ve hava tipi kırılımı</h2><pre>{html.escape(str({'saatlik_mae_kwh': report.hourly_mae_kwh, 'hava_tipi_mae_kwh': report.weather_group_mae_kwh}))}</pre>"""


def _site_from_form(form: dict[str, str]) -> SiteConfig:
    losses = LossFactors(
        soiling_pct=_number(form, "soiling_pct", 2), reflection_pct=_number(form, "reflection_pct", 2),
        mismatch_pct=_number(form, "mismatch_pct", 2), dc_cable_pct=_number(form, "dc_cable_pct", 1.5),
        shading_pct=_number(form, "shading_pct", 0), ac_cable_pct=_number(form, "ac_cable_pct", 1),
        transformer_pct=_number(form, "transformer_pct", 1), availability_pct=_number(form, "availability_pct", 0), snow_pct=_number(form, "snow_pct", 0),
    )
    site = SiteConfig(
        name=form["name"], latitude_deg=_number(form, "latitude_deg"), longitude_deg=_number(form, "longitude_deg"),
        panel_count=_integer(form, "panel_count"), panel_power_wp=_number(form, "panel_power_wp"),
        ac_capacity_kw=_number(form, "ac_capacity_kw"), tilt_deg=_number(form, "tilt_deg"),
        azimuth_compass_deg=_number(form, "azimuth_compass_deg"), age_years=_integer(form, "age_years"),
        temperature_coefficient_per_c=_number(form, "temperature_coefficient_per_c", -0.004),
        elevation_m=_optional_number(form, "elevation_m"),
        mount_type=MountType(form.get("mount_type", "ground")), losses=losses,
    )
    site.validate()
    return site


def _parse_form(environ: dict[str, Any]) -> dict[str, str]:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    raw = environ["wsgi.input"].read(length).decode("utf-8")
    return {key: values[0] for key, values in parse_qs(raw, keep_blank_values=True).items()}


def _parse_actual_csv(value: str) -> list[tuple[str, float]]:
    rows = csv.DictReader(io.StringIO(value))
    result: list[tuple[str, float]] = []
    for index, row in enumerate(rows, start=2):
        try:
            result.append((row["timestamp"].strip(), float(row["energy_kwh"])))
        except (KeyError, AttributeError, ValueError) as exc:
            raise ValidationError(f"CSV satır {index}: timestamp ve energy_kwh alanları zorunludur.") from exc
    if not result:
        raise ValidationError("CSV en az bir gerçekleşen üretim satırı içermelidir.")
    return result


def _required_forecast(repository: Repository, query: dict[str, list[str]]) -> dict[str, Any]:
    forecast_id = query.get("forecast_id", [""])[0]
    forecast = repository.get_forecast(forecast_id)
    if forecast is None:
        raise ValidationError("Tahmin bulunamadı.")
    return forecast


def _export(start_response: Callable, repository: Repository, query: dict[str, list[str]], kind: str) -> list[bytes]:
    forecast = _required_forecast(repository, query)
    payload = to_csv(forecast) if kind == "csv" else to_xlsx(forecast)
    content_type = "text/csv; charset=utf-8" if kind == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    start_response("200 OK", [("Content-Type", content_type), ("Content-Disposition", f"attachment; filename=tahmin.{kind}"), ("Content-Length", str(len(payload)))])
    return [payload]


def _number(form: dict[str, str], key: str, default: float | None = None) -> float:
    value = form.get(key, "")
    if value == "" and default is not None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValidationError(f"{key} sayısal olmalıdır.") from exc


def _integer(form: dict[str, str], key: str, default: int | None = None) -> int:
    value = form.get(key, "")
    if value == "" and default is not None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValidationError(f"{key} tam sayı olmalıdır.") from exc


def _optional_number(form: dict[str, str], key: str) -> float | None:
    value = form.get(key, "").strip()
    return None if not value else _number(form, key)


def _format(value: Any) -> str:
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def _layout(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)} | GES Tahmin</title><style>:root{{--ink:#10233f;--muted:#5b6b82;--line:#d9e2ee;--surface:#fff;--canvas:#f5f8fc;--brand:#155eef;--brand-dark:#12376d;--accent:#f59e0b;--success:#027a48}}*{{box-sizing:border-box}}body{{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:1240px;margin:0 auto;padding:0 1.1rem 3rem;color:var(--ink);background:linear-gradient(180deg,#f4f8ff 0,white 460px);line-height:1.5}}header{{display:flex;justify-content:space-between;align-items:center;padding:1.35rem 0;border-bottom:1px solid var(--line);margin-bottom:2rem}}header h1{{font-size:1.1rem;margin:0;color:var(--brand-dark);letter-spacing:-.02em}}header p{{margin:0}}a{{color:var(--brand-dark);font-weight:700;text-decoration:none}}a:hover{{text-decoration:underline}}h2{{font-size:1.9rem;letter-spacing:-.04em;margin:0 0 1.25rem}}h3{{margin:.05rem 0 .25rem;font-size:1.1rem;letter-spacing:-.02em}}p{{color:var(--muted)}}input,select,textarea,button{{font:inherit}}input,select,textarea{{width:100%;padding:.7rem .75rem;border:1px solid #bdc9d8;border-radius:.55rem;background:white;color:var(--ink)}}input:focus,select:focus,textarea:focus{{outline:3px solid #bfd6ff;border-color:var(--brand)}}button{{border:0;border-radius:.55rem;padding:.75rem 1rem;background:var(--brand-dark);color:white;cursor:pointer;font-weight:800;white-space:nowrap}}button:hover{{background:#0c2b57}}.primary{{background:var(--brand);font-size:1rem;padding:.9rem 1.2rem}}.secondary{{background:#eaf1ff;color:var(--brand-dark)}}.intro-card,.result-hero{{display:flex;gap:1rem;justify-content:space-between;align-items:flex-start;background:linear-gradient(135deg,#12376d,#155eef);color:white;border-radius:1rem;padding:1.35rem 1.45rem;margin-bottom:1.2rem;box-shadow:0 14px 30px rgba(19,55,109,.15)}}.intro-card p,.result-hero p{{color:#dbeafe;margin:.3rem 0 0}}.intro-card h3,.result-hero h3{{font-size:1.35rem}}.eyebrow{{font-size:.74rem!important;text-transform:uppercase;letter-spacing:.1em;font-weight:800;color:#bfdbfe!important;margin:0!important}}.source-note,.result-status{{display:grid;gap:.2rem;min-width:185px;padding:.75rem .9rem;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.2);border-radius:.7rem;font-size:.86rem}}.forecast-form{{display:grid;gap:1rem}}.form-section,.advanced,.chart-panel,.details-panel{{background:var(--surface);border:1px solid var(--line);border-radius:.9rem;padding:1.2rem;box-shadow:0 5px 18px rgba(16,35,63,.04)}}.section-title{{display:flex;gap:.75rem;align-items:flex-start;margin-bottom:1rem}}.section-title p{{margin:.1rem 0 0;font-size:.88rem}}.step{{display:grid;place-items:center;flex:0 0 1.8rem;height:1.8rem;border-radius:50%;background:#e8f0ff;color:var(--brand);font-weight:900}}.form-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem}}.field{{display:grid;gap:.32rem;font-weight:750;font-size:.9rem}}.field small{{font-weight:500;color:var(--muted);font-size:.77rem;line-height:1.32}}.location-search{{display:flex;gap:.7rem;align-items:end;margin-bottom:1rem}}.location-search .grow{{flex:1}}.estimator{{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;background:#edf4ff;border:1px solid #c8dbff;border-radius:.9rem;padding:.9rem 1rem}}.estimator div{{display:grid;gap:.1rem}}.estimator span{{color:var(--muted);font-size:.82rem;font-weight:700}}.estimator strong{{font-size:1.25rem;color:var(--brand-dark)}}.estimator p{{grid-column:1/-1;margin:.15rem 0 0;font-size:.85rem}}.advanced summary,.details-panel summary{{cursor:pointer;display:flex;justify-content:space-between;gap:1rem;font-weight:850;color:var(--brand-dark)}}.advanced summary small,.details-panel summary span{{font-weight:600;color:var(--muted);font-size:.8rem}}.advanced-grid{{padding-top:1rem}}.submit-row{{display:flex;justify-content:space-between;gap:1rem;align-items:center;padding:1rem 0 0}}.submit-row div{{display:grid;gap:.15rem}}.submit-row span{{font-size:.86rem;color:var(--muted)}}.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem;margin:1rem 0}}.cards div{{background:#edf4ff;padding:1rem;border-radius:.75rem;border:1px solid #d7e5ff}}.cards b{{font-size:.83rem;color:var(--muted)}}.cards span{{display:block;font-size:1.35rem;font-weight:850;color:var(--brand-dark)}}.cards small{{font-size:.82rem}}.action-links{{display:flex;flex-wrap:wrap;gap:.6rem;margin:1rem 0}}.action-links a{{padding:.55rem .75rem;border:1px solid var(--line);border-radius:.55rem;background:#fff;font-size:.87rem}}.chart-panel{{margin:1rem 0}}.panel-heading{{display:flex;justify-content:space-between;gap:1rem;align-items:start;margin-bottom:.85rem}}.panel-heading p{{margin:.15rem 0 0;font-size:.86rem}}.source-badge{{background:#eef3fb;color:var(--brand-dark);padding:.3rem .55rem;border-radius:999px;font-size:.75rem;font-weight:800}}.chart{{width:100%;height:auto;background:linear-gradient(#fbfdff,#f5f8fc);border:1px solid var(--line);border-radius:.55rem}}.legend,.warning,.details-note,.attribution{{font-size:.84rem}}.legend{{margin:.6rem 0 0}}.warning{{padding:.75rem 1rem;background:#fff7d6;border:1px solid #f4d991;border-radius:.65rem;color:#744c00}}.details-panel{{margin-top:1rem}}.details-panel[open] summary{{margin-bottom:1rem}}.details-note{{margin:-.2rem 0 1rem}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:.86rem;min-width:720px}}th,td{{padding:.55rem .65rem;border-bottom:1px solid var(--line);text-align:right}}th{{background:#edf4ff;color:var(--brand-dark);font-size:.78rem;position:sticky;top:0}}th:first-child,td:first-child{{text-align:left}}.error{{padding:.8rem 1rem;background:#ffe4e6;color:#991b1b;border-radius:.65rem}}pre{{white-space:pre-wrap;background:#f4f6f8;padding:1rem;border-radius:.65rem}}@media(max-width:850px){{.form-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:560px){{body{{padding:0 .8rem 2rem}}header{{margin-bottom:1.2rem}}.intro-card,.result-hero,.location-search,.submit-row{{flex-direction:column}}.form-grid,.cards,.estimator{{grid-template-columns:1fr}}.location-search button,.primary{{width:100%}}.source-note,.result-status{{width:100%}}h2{{font-size:1.55rem}}}}</style></head><body><header><h1>GES Saatlik Üretim Tahmin Motoru</h1><p><a href='/'>+ Yeni tahmin</a></p></header><main><h2>{html.escape(title)}</h2>{body}</main></body></html>"""


def _html(start_response: Callable, content: str, status: str = "200 OK") -> list[bytes]:
    payload = content.encode("utf-8")
    start_response(status, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(payload)))])
    return [payload]


def _json(start_response: Callable, data: Any) -> list[bytes]:
    import json
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    start_response("200 OK", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(payload)))])
    return [payload]


def _redirect(start_response: Callable, location: str) -> list[bytes]:
    start_response("303 See Other", [("Location", location)])
    return [b""]
