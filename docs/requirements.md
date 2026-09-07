# PDF gereksinim izlenebilirliği

| PDF gereksinimi | Uygulamadaki karşılık |
| --- | --- |
| Saatlik kWh ve kW, günlük toplam/tepe | `ForecastHour`, sonuç özeti ve tablo |
| Ara değer görünürlüğü | GTI, hava/hücre sıcaklığı, DC/AC güç, inverter verimi, kırpma kaybı; dışa aktarımda tam ara değer seti |
| Grafik ve CSV/Excel | Yerel SVG grafik, `/export.csv`, `/export.xlsx` |
| Senaryo | Formdaki isteğe bağlı senaryo eğim/azimut alanları |
| Girdi doğrulama | `SiteConfig.validate()` |
| 10 adımlı zincir | `ForecastEngine.forecast_hour()` içindeki sıralı adımlar |
| Ayrı yapılandırılabilir kayıplar | `LossFactors`, form ve `config/sites.example.json` |
| Open-Meteo cache/offline davranışı | `OpenMeteoClient` ve `weather_cache` |
| SQLite + tahmin sürümleme | `Repository` tabloları, UUID sürümleri ve `/history` geçmiş ekranı |
| Ek A üç saha kabul testleri | `/comparison`: üç saha tek işlemde hesaplanır; DC/AC, kWh/kWp, kırpma/yaşlanma karşılaştırması, aynı gün eğrisi ve aylık kırpma dağılımı gösterilir |
| Yerel web arayüz | WSGI arayüzü (`app.py`) |
| Birim testleri | gece, sıcaklık, yaşlanma, kırpma, doğrulama ve sürümleme testleri |
| Doğruluk analizi | `analytics.py`, gerçekleşen üretim CSV ekranı |

## Açık bağımlılık

PDF, doğruluk analizi için saatlik gerçekleşen üretim verisinin ayrıca sağlanacağını söylüyor. Bu veri klasörde henüz yoktur; uygulama hazır olduğunda arayüzden `timestamp,energy_kwh` CSV'si yüklenir. Gerçek verisiz sayısal doğruluk sonucu iddia edilmez.
