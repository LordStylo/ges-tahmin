# GES Saatlik Üretim Tahmin Motoru

Yerel çalışan Python 3 uygulaması, GES için Open-Meteo destekli saatlik üretim tahmini üretir. Model ve veri erişimi birbirinden ayrıdır; fiziksel model ağa ihtiyaç duymadan doğrudan test edilebilir.

## Çalıştırma

Bundled Python ile:

```powershell
$env:PYTHONPATH = "src"
& 'C:\Users\Staj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m ges_forecast
```

Arayüz: `http://127.0.0.1:8080`. Testler için:

```powershell
$env:PYTHONPATH = "src"
& 'C:\Users\Staj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -v
```

## Mimari

`open_meteo.py` yalnızca veri çekme/önbelleklemeden, `model.py` yalnızca fiziksel hesaplamadan, `app.py` yalnızca yerel arayüzden sorumludur. `storage.py` SQLite'ta ham API yanıtını, her tahmin sürümünü, saatlik ara değerleri ve gerçekleşen üretimi ayrı tutar. Aynı hedef saat için yapılan tahminler yeni UUID ile kaydedilir; önceki tahmin silinmez. Arayüzdeki **Tahmin geçmişi** bağlantısı tüm sürümleri; oluşturulma zamanı, tahmin aralığı, veri kaynağı ve sonuç/CSV/analiz kısayollarıyla gösterir.

Saha ve kayıp faktörü örnekleri [config/sites.example.json](config/sites.example.json) içindedir. Yeni saha eklemek için bu dosyaya alan eklenir; model kodu değiştirilmez.

## Ek A: üç saha kabul ekranı

`/comparison` ekranı PDF'deki Saha 1, Saha 2 ve Saha 3 ham girdilerini sabit test seti olarak içerir. Tek işlemde üç farklı konum için meteoroloji alınır, her sonuç ayrı tahmin sürümü olarak saklanır ve DC/AC, toplam/spesifik üretim, kırpma, yaşlanma, aynı gün üretim eğrileri ve aylık kırpma dağılımı birlikte gösterilir. Yıllık kırpma karşılaştırması için tamamlanmış takvim yılı seçilir; kısa dönem tahmin sonuçları yıllık olarak etiketlenmez.

## Model zinciri

1. `panel_count × panel_power_wp / 1000` ile DC kurulu güç (kWp).
2. Open-Meteo'nun `global_tilted_irradiance` alanı ile panel düzlemi ışınımı (W/m²).
3. NOCT + rüzgâr soğutması ile hücre sıcaklığı.
4. Negatif sıcaklık katsayısı ile sıcaklık düzeltmesi.
5. İlk yıl ve takip eden yıllar için ayrı yaşlanma düzeltmesi.
6. Ayrı ayarlanabilir DC kayıpları.
7. Yük oranına bağlı inverter verimi.
8. AC kapasiteye kırpma ve kayıp enerji raporu.
9. Ayrı ayarlanabilir AC, trafo, kullanılabilirlik ve kar kayıpları.
10. Saatlik ortalama kW × 1 saat = kWh.

Arayüzdeki azimut pusula referansıdır: Kuzey=0°, Doğu=90°, Güney=180°. Veri katmanı bunu Open-Meteo'nun Güney=0° referansına dönüştürür; böylece yön tersine çevrilmez.

## Veri kaynağı, önbellek ve lisans

Tahmin istekleri en fazla 60 dakika taze önbellekten servis edilir. Ağ erişimi kesilirse aynı sorgunun son önbellek verisi kullanılır ve veri yaşı sonuçta gösterilir. API yanıtındaki saatlik ışınım değeri önceki saatin ortalamasıdır; model bu semantiği enerji hesabında bir saatlik ortalama güç olarak kullanır.

Open-Meteo verisi CC BY 4.0 ile sunulur; arayüz Open-Meteo/Copernicus atfını gösterir. Ticari kullanım için güncel Open-Meteo koşulları ayrıca ürünleşme kararı öncesinde hukuki incelemeye tabidir.

Savunma/rapor için birincil araştırma kaynakları:

- [Forecast API: GTI, azimut ve saatlik zaman semantiği](https://open-meteo.com/en/docs)
- [Historical Weather API: geriye dönük saatlik seri](https://open-meteo.com/en/docs/historical-weather-api)
- [Geocoding API: şehir/ilçe, koordinat, rakım ve saat dilimi](https://open-meteo.com/en/docs/geocoding-api)
- [Open-Meteo lisansı ve atıf koşulları](https://open-meteo.com/en/licence)

## Kapsam ve sonraki girdi

Uygulama tahmin, CSV/Excel dışa aktarımı, senaryo karşılaştırması ve gerçekleşen üretim CSV'sinden MAE, RMSE, ortalama sapma, normalize MAE, saat/hava tipi kırılımları ile "dünün üretimi" taban karşılaştırmasını içerir. Gerçekleşen üretim veri seti henüz proje klasöründe olmadığı için tam doğruluk raporu, bu CSV sağlandığında çalışacaktır.
