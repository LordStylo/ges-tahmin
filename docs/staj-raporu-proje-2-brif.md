# Staj raporu için Proje 2 brifi: GES Saatlik Üretim Tahmin Motoru

Bu dosya, staj raporuna ikinci projeyi ekleyecek yapay zekâya verilecek gerçek-proje bağlamıdır. Metni rapor diline dönüştürürken yalnızca aşağıdaki doğrulanmış bilgilere dayan. Kurum, ekip, tarih, kişisel gözlem veya donanım özellikleri bilinmiyorsa **uydurma**; `[DOLDURULACAK]` alanlarını kullanıcıya sor ya da olduğu gibi bırak.

## Kısa proje özeti

Proje, fotovoltaik güneş enerji santrallerinin (GES) saatlik elektrik üretimini tahmin eden, yerel çalışan bir Python web uygulamasıdır. Kullanıcı saha konumu, panel sayısı ve gücü, AC inverter kapasitesi, panel eğimi/yönü, saha yaşı, montaj tipi ve kayıp parametrelerini girer. Sistem Open-Meteo'dan saatlik meteorolojik verileri alır; bunları fiziksel üretim modeliyle işleyerek saatlik kW, kWh, hücre sıcaklığı, ışınım ve kırpma kaybı üretir.

Uygulamanın ikinci önemli çıktısı üç gerçek test sahasını tek işlemde karşılaştıran Ek A kabul ekranıdır. Bu ekranda DC/AC oranı, toplam ve spesifik üretim, kırpma kaybı, yaşlanma kaybı, tepe zaman, aynı gün üretim eğrileri ve aylık kırpma dağılımı birlikte incelenebilir.

## Doğrulanmış proje kapsamı

- Saatlik kWh ve ortalama AC kW tahmini.
- Panel düzlemi ışınımı (GTI), hava sıcaklığı, hücre sıcaklığı, rüzgâr ve bulutluluk kullanımı.
- DC kurulu güç, sıcaklık düzeltmesi, yaşlanma, DC kayıpları, inverter verimi, AC kapasite kırpması ve AC/trafo kayıplarından oluşan on adımlı fiziksel hesap zinciri.
- Kırpma kaybının hem kWh hem de seçili dönemin kırpma öncesi AC enerjisine oranı olarak gösterimi.
- Open-Meteo tahmin, geçmiş meteoroloji, geocoding ve opsiyonel rakım verisi entegrasyonu.
- Aynı sorguları yerel SQLite önbelleğinden servis etme; taze veri için 60 dakikalık önbellek, ağ kesintisinde eski önbelleğe geri düşme.
- Tahminleri UUID sürümüyle saklama; eski tahmini ezmeme ve tahmin geçmişi ekranı.
- CSV ve Excel dışa aktarımı.
- Gerçekleşen üretim CSV'si yükleme ve tahmin doğruluk analizi: MAE, RMSE, ortalama sapma, normalize MAE, saat/hava tipi kırılımı ve önceki gün üretimi tabanı.
- Tek saha için eğim/azimut senaryo karşılaştırması.
- Ek A için üç saha karşılaştırması ve her saha sonucuna ait ayrı gerçekleşen üretim/analiz bağlantısı.

## Ek A test sahaları

| Saha | Enlem, boylam | Panel adedi | Panel gücü | Eğim | Yaş | AC anlaşma gücü |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Saha 1 | 37.075739, 36.804529 | 91.327 | 550 Wp | 20° | 2 yıl | 39.700 kW |
| Saha 2 | 40.862088, 33.094728 | 17.854 | 550 Wp | 25° | 3 yıl | 7.500 kW |
| Saha 3 | 38.275934, 39.741377 | 7.123 | 550 Wp | 20° | 1 yıl | 3.500 kW |

Üç sahada panel yönü güneydir (pusula azimutu 180°). Uygulama bu değeri Open-Meteo'nun azimut referansına dönüştürür. Varsayılan çalışma kabulü arazi montajı ve görünür/ayarlanabilir kayıp katsayılarıdır.

## Uygulama mimarisi ve çalışma akışı

```text
Kullanıcı formu / üç saha ekranı
            |
            v
Open-Meteo veri katmanı ----> SQLite hava önbelleği
            |
            v
Fiziksel GES üretim modeli
            |
            v
SQLite tahmin sürümleri ----> sonuç, geçmiş, CSV/Excel, analiz ekranları
```

Üç saha karşılaştırmasında farklı konum ve panel eğimleri nedeniyle her saha için ayrı meteoroloji sorgusu hazırlanır. Bu üç sorgu paralel yürütülür. Aynı saha-parametre-dönem sorgusu tekrar edilirse önbellek kullanıldığı için yeni dış API isteği yapılmaz. Her sahaya ait sonuç ayrı bir tahmin sürümü olarak saklanır; karşılaştırma ekranı bu üç sürümü birlikte sunar.

Yıllık kırpma kabul testi için uygulamada `Tamamlanmış takvim yılı` modu bulunur. Kısa dönem tahmin sonucu yıllık veri gibi etiketlenmez. 2025 yılı için yapılan gerçek çalışma her saha için 8.760 saat üretti; kırpma yüzdesi sıralaması Saha 2 (%0,490), Saha 1 (%0,001), Saha 3 (%0,000) olarak gözlendi. Bu sayı, belirli yıl ve model varsayımları için örnek doğrulama sonucudur; genel/garantili üretim değeri diye yazılmamalıdır.

## SORU-3 için rapor yazım girdisi

### Çalışmanın tanımı ve amacı

Rapor, GES sahalarının saatlik üretimini meteorolojik tahminlerle fiziksel model üzerinden tahmin eden, sonuçları izlenebilir biçimde saklayan ve saha karşılaştırmasını destekleyen bir uygulamanın geliştirildiğini anlatmalıdır. Amaç; saha tasarım ve işletme kararlarında kullanılabilecek şekilde üretim tahmini, inverter kırpması, yaşlanma etkisi ve kayıp bileşenlerini görünür kılmak; tahminleri daha sonra gerçekleşen üretimle karşılaştırabilecek altyapıyı oluşturmaktır.

Üç saha karşılaştırması özelinde amaç; salt toplam kWh karşılaştırması yerine kurulu güç farkını kWh/kWp ile normalize etmek, DC/AC oranı-kırpma ilişkisini incelemek, yaşlanma etkisini ayırmak ve konuma/eğime bağlı üretim eğrisi farklarını aynı ekranda göstermekti.

### Uygulama yöntemi

1. Saha parametreleri kullanıcı formundan veya Ek A sabit test setinden alındı.
2. Open-Meteo API'den saatlik GTI, sıcaklık, rüzgâr ve bulutluluk verisi çekildi.
3. Aynı sorguların tekrarında API limitini korumak için SQLite önbellek kontrol edildi.
4. Her saat için fiziksel model aşağıdaki sırayla uygulandı:
   1. DC kurulu güç hesabı: panel adedi × panel gücü.
   2. GTI'nin panel düzlemindeki ışınım girdisi olarak kullanımı.
   3. NOCT ve rüzgâr soğutmasıyla hücre sıcaklığı hesabı.
   4. Negatif sıcaklık katsayısı ile güç düzeltmesi.
   5. İlk yıl ve sonraki yıllar için ayrı yaşlanma katsayısı.
   6. Kirlenme, yansıma, uyumsuzluk, DC kablo ve gölgeleme kayıpları.
   7. Yük oranına bağlı inverter verimi.
   8. AC kapasitesine göre kırpma ve kayıp enerjinin hesaplanması.
   9. AC kablo, trafo, kullanılabilirlik ve kar kayıpları.
   10. Saatlik ortalama güçten kWh enerji hesabı.
5. Hesaplanan saatlik ara değerler ve sonuçlar UUID sürümüyle SQLite veritabanına kaydedildi.
6. Sonuçlar grafik, günlük/saatlik tablolar, CSV/Excel dışa aktarımı ve tahmin geçmişi aracılığıyla kullanıcıya sunuldu.
7. Gerçekleşen üretim verisi sağlandığında CSV yükleme ekranı üzerinden doğruluk metrikleri hesaplandı.

### Çözümleme ve tasarım aşamaları

- Gereksinim çözümlemesi: PDF'deki saatlik tahmin, izlenebilir ara değerler, veri önbelleği, sürümleme, doğruluk analizi ve Ek A üç saha kabul testleri ayrıştırıldı.
- Alan modeli: `SiteConfig`, `LossFactors`, `WeatherHour` ve `ForecastHour` veri yapıları tanımlandı; tüm kritik saha ve kayıp girdileri doğrulandı.
- Katmanlı tasarım: meteoroloji erişimi, fiziksel model, veri deposu, analiz/ihracat ve web arayüzü ayrı modüllere ayrıldı.
- Veri entegrasyonu: Open-Meteo sorgu parametreleri, pusula azimutu dönüşümü ve önbellek anahtarı tasarlandı.
- Arayüz tasarımı: temel/gelişmiş saha girişi, canlı DC/AC göstergesi, sonuç kartları, grafikler, tahmin geçmişi ve üç saha karşılaştırma ekranı tasarlandı.
- Doğrulama: birim testleri ile gece üretimi, sıcaklık etkisi, yaşlanma, kırpma, girdi doğrulama, önbellek anahtarı, tahmin sürümleme ve üç saha karşılaştırma koşulları sınandı.

### Kullanılan geliştirme yazılımı ve araçları

Doğrulanmış araçlar:

- Python 3.
- Yerel WSGI tabanlı web uygulaması.
- SQLite.
- Open-Meteo Forecast, Historical Weather ve Geocoding API'leri.
- `unittest` ile birim testleri.
- `openpyxl` ile Excel dışa aktarımı.
- HTML, CSS ve SVG ile yerel arayüz ve grafik üretimi.
- PowerShell tabanlı yerel çalışma/doğrulama ortamı.
- Graphify ile kod tabanı ilişki ve mimari incelemesi.

Donanım için yalnızca şu güvenli ifade kullanılabilir: "Uygulama yerel bir iş istasyonu/bilgisayar üzerinde geliştirilmiş ve test edilmiştir." İşlemci, RAM, işletim sistemi sürümü veya şirket altyapısı bilgileri bilinmiyorsa eklenmemelidir. Gerekirse `[DOLDURULACAK: kullanılan bilgisayar/işletim sistemi]` alanı bırakılmalıdır.

### Elde edilen sonuçlar

- Kullanıcı tarafından girilen saha parametrelerinden saatlik üretim tahmini üretildi.
- Üretime etki eden ara değişkenler ile kırpma ve kayıp değerleri görünür hâle getirildi.
- Tahminler sürümlü biçimde saklandığı için aynı saat için üretilen farklı tahminler sonradan incelenebilir hâle geldi.
- Üç test sahası tek işlemle karşılaştırıldı; DC/AC, spesifik üretim, yaşlanma ve kırpma ilişkileri raporlandı.
- Gerçekleşen veri yüklenmesi durumunda tahmin doğruluğunu sayısal metriklerle değerlendirecek altyapı oluşturuldu.
- Son doğrulamada 11 birim test başarılı sonuç verdi.

## SORU-4 için rapor yazım girdisi

### Genel değerlendirme için güvenli anlatım

Bu çalışma, enerji üretim tahmininde yalnızca toplam kWh değerini vermenin yeterli olmadığını; girdi kalitesi, meteoroloji kaynağı, DC/AC oranı, inverter sınırı, yaşlanma ve kayıp varsayımlarının sonucu doğrudan etkilediğini göstermiştir. Katmanlı tasarım, veri kaynağı değişse dahi fiziksel modelin ve kullanıcı arayüzünün korunabilmesini sağlamıştır. Tahmin geçmişi ve ara değerlerin saklanması, sonuçların sonradan denetlenebilmesine katkı sunmuştur.

### Karşılaşılan teknik durumlar ve çözüm yaklaşımı

| Durum / güçlük | Uygulanan yaklaşım |
| --- | --- |
| Haricî meteoroloji API'sine bağımlılık ve limit riski | Tekrarlanan aynı sorgular için SQLite önbelleği; taze veride 60 dakika önbellek, erişim sorunu olduğunda eski önbelleğe geri dönüş. |
| Farklı azimut referansları | Kullanıcının pusula referansındaki açısı Open-Meteo referansına açık bir dönüşümle çevrildi. |
| Saha güçleri çok farklı olduğunda toplam kWh karşılaştırmasının yanıltıcı olması | Spesifik üretim (kWh/kWp) ve DC/AC oranı karşılaştırma ekranına eklendi. |
| Yıllık kabul testi ile kısa dönem tahminin karıştırılma riski | Tamamlanmış takvim yılı için ayrı çalışma modu eklendi; kısa tahmin yıllık diye etiketlenmedi. |
| Aynı tahminin üzerine yazılmasıyla izlenebilirliğin kaybolması | Her tahmine UUID sürümü verildi ve tahmin geçmişi oluşturuldu. |
| Gerçekleşen üretim verisi olmadan doğruluk iddiası üretme riski | Uygulama doğruluk metriklerini destekler; ancak gerçek CSV sağlanmadıkça sayısal doğruluk iddiası yapılmaz. |

### İşyerindeki özel durumlar ve aksaklıklar hakkında yazım kuralı

İşyerinde bizzat gözlenmemiş bir aksaklığı rapora ekleme. Aşağıdaki alanlar ancak kullanıcı tarafından doğrulanırsa doldurulmalıdır:

- `[DOLDURULACAK: işyerinde karşılaşılan iş akışı, iletişim veya teknik altyapı durumu]`
- `[DOLDURULACAK: mühendis geri bildirimi veya talep edilen revizyon]`
- `[DOLDURULACAK: API limiti, veri erişimi veya gerçek üretim verisiyle ilgili kurum içi prosedür]`

Bu proje için güvenle yazılabilecek teknik gözlem şudur: Haricî API kullanımında çağrı sayısı, önbellek süresi ve erişim hatalarına karşı yedek davranış tasarlanmalıdır. Ücretsiz Open-Meteo katmanının ticari olmayan kullanım için günlük/saatlik/dakikalık limitleri vardır; bu nedenle önbellek ve kullanıcı tetiklemeli yıllık analiz yaklaşımı önemlidir.

### Çalışmadan nasıl faydalanıldığına dair rapor cümlesi taslağı

"Geliştirilen uygulama, GES sahalarına ilişkin üretim tahminini saatlik düzeyde inceleme, kayıp bileşenlerini ayırma, birden fazla sahayı normalize edilmiş metriklerle karşılaştırma ve tahmin sonuçlarını sürümlü olarak saklama imkânı sağlamıştır. Böylece saha parametrelerinin üretim ve inverter kırpması üzerindeki etkisi görünür hâle getirilmiş; gerçekleşen üretim verisi sağlandığında kullanılmak üzere doğruluk değerlendirme altyapısı hazırlanmıştır."

Bu cümle, projenin gerçekten kullanıma alındığını veya ticari karar verildiğini iddia etmez. İşyerinde fiilî kullanım olduysa, yalnızca kullanıcı tarafından doğrulanan kullanım senaryosu ayrıca eklenmelidir.

## Diğer yapay zekâya verilecek hazır istek

```text
Bu Markdown dosyasındaki doğrulanmış proje bilgilerini kullanarak staj raporunun ikinci proje bölümü için Türkçe, resmî ve birinci tekil şahıs anlatımıyla iki bölüm yaz:

1) SORU-3: Çalışmanın tanımı, amacı, uygulama yöntemi, çözümleme/tasarım aşamaları, kullanılan yazılım-donanım araçları ve sonuçlar.
2) SORU-4: Stajın genel değerlendirmesi, karşılaşılan teknik güçlükler, dikkat çeken noktalar ve çalışmanın işyerine olası katkısı.

Kuruma, şirkete, ekibe, kişilere, staj tarihine veya hiç gözlenmemiş işyeri aksaklıklarına ilişkin bilgi uydurma. [DOLDURULACAK] alanlarını koru. Gerçekleşen üretim CSV'si olmadan doğruluk başarısı iddia etme. 2025 için verilen kırpma yüzdelerini yalnızca örnek doğrulama sonucu ve belirli model varsayımlarının çıktısı olarak yaz. Metinde “geliştirdim”, “tasarladım”, “uyguladım”, “doğruladım” dilini kullan; ancak ticari kullanıma alındığını söyleme.
```
