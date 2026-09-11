# Graph Report - staj2  (2026-09-07)

## Corpus Check
- 64 files · ~361,250 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 320 nodes · 532 edges · 51 communities (16 shown, 6 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 38 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d0967a07`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Saatlik Üretim Tahmini
- app.py
- What You Must Do When Invoked
- SiteConfig
- Repository
- OpenMeteoClient
- look-mechanics.md
- ForecastEngineAcceptanceTests
- graphify reference: extra exports and benchmark
- GES Saatlik Üretim Tahmin Motoru
- ValidationError
- graphify reference: query, path, explain
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- PDF gereksinim izlenebilirliği
- extraction-spec.md
- ges-uretim-tahmin-motoru
- Staj raporu için Proje 2 brifi: GES Saatlik Üretim Tahmin Motoru
- build_comparison_workbook.mjs

## God Nodes (most connected - your core abstractions)
1. `SiteConfig` - 27 edges
2. `Repository` - 26 edges
3. `ForecastEngine` - 22 edges
4. `ValidationError` - 19 edges
5. `WeatherHour` - 16 edges
6. `OpenMeteoClient` - 14 edges
7. `ForecastHour` - 12 edges
8. `What You Must Do When Invoked` - 12 edges
9. `_comparison_view()` - 11 edges
10. `calculate_metrics()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Graphify Project Instructions` --references--> `Saatlik Üretim Tahmini`  [EXTRACTED]
  AGENTS.md → Stajyer_Projesi_Uretim_Tahmin_Motoru.pdf
- `ForecastEngineAcceptanceTests` --uses--> `ValidationError`  [INFERRED]
  tests/test_model.py → src/ges_forecast/domain.py
- `site()` --uses--> `LossFactors`  [INFERRED]
  tests/test_model.py → src/ges_forecast/domain.py
- `ForecastEngineAcceptanceTests` --uses--> `ForecastEngine`  [INFERRED]
  tests/test_model.py → src/ges_forecast/model.py
- `VersioningTests` --uses--> `Repository`  [INFERRED]
  tests/test_storage.py → src/ges_forecast/storage.py

## Import Cycles
- None detected.

## Communities (51 total, 6 thin omitted)

### Community 0 - "Saatlik Üretim Tahmini"
Cohesion: 0.15
Nodes (13): Graphify Project Instructions, Alternatif Akım (AC), Doğru Akım (DC), Enerji (Wh / kWh), Fiziksel Model, Güç (W / kW), Güneş Enerji Santrali (GES), Hava Durumu Verisi (+5 more)

### Community 1 - "app.py"
Cohesion: 0.10
Nodes (35): _acceptance_view(), _actuals_form(), _analysis_view(), _clipping_callout(), _comparison_curve_day(), _comparison_daily_rows(), _comparison_day_picker(), _comparison_form() (+27 more)

### Community 2 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 3 - "SiteConfig"
Cohesion: 0.14
Nodes (19): datetime, calculate_metrics(), ComparisonMetrics, Any, Bir saha için seçili tahmin/doğrulama döneminin karşılaştırma metrikleri., _timestamp_text(), _value(), ForecastHour (+11 more)

### Community 4 - "Repository"
Cohesion: 0.20
Nodes (8): Connection, _forecast_hour_to_dict(), Any, Path, En yeni tahmin sürümlerini, saatlik satırları yüklemeden listeler., Tahmin sürümlerini asla ezmeden saklayan SQLite deposu., Repository, _utc_now()

### Community 5 - "OpenMeteoClient"
Cohesion: 0.15
Nodes (11): _canonical_query_value(), compass_to_open_meteo_azimuth(), OpenMeteoClient, _parse_weather(), Any, Kuzey=0 pusula açısını Open-Meteo'nun Güney=0 açısına çevirir., 20 ile 20.0 gibi eşdeğer girdi biçimlerini aynı önbellek anahtarına indirger., Doğruluk doğrulaması için geçmiş saatlik meteoroloji/GTI serisi. (+3 more)

### Community 7 - "ForecastEngineAcceptanceTests"
Cohesion: 0.42
Nodes (3): ForecastEngineAcceptanceTests, site(), weather()

### Community 8 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 9 - "GES Saatlik Üretim Tahmin Motoru"
Cohesion: 0.25
Nodes (7): Ek A: üç saha kabul ekranı, GES Saatlik Üretim Tahmin Motoru, Kapsam ve sonraki girdi, Mimari, Model zinciri, Veri kaynağı, önbellek ve lisans, Çalıştırma

### Community 10 - "ValidationError"
Cohesion: 0.11
Nodes (19): AccuracyReport, evaluate_forecast(), Any, _weather_group(), _comparison_snapshot_export(), create_app(), _integer(), _number() (+11 more)

### Community 11 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 12 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 13 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 14 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 21 - "Staj raporu için Proje 2 brifi: GES Saatlik Üretim Tahmin Motoru"
Cohesion: 0.11
Nodes (17): Diğer yapay zekâya verilecek hazır istek, Doğrulanmış proje kapsamı, Ek A test sahaları, Elde edilen sonuçlar, Genel değerlendirme için güvenli anlatım, İşyerindeki özel durumlar ve aksaklıklar hakkında yazım kuralı, Karşılaşılan teknik durumlar ve çözüm yaklaşımı, Kullanılan geliştirme yazılımı ve araçları (+9 more)

### Community 22 - "build_comparison_workbook.mjs"
Cohesion: 0.09
Nodes (26): actual, actualHeaders, actualHours, actualRows, allDays, colors, dailyMaps, dailyMatrix() (+18 more)

## Knowledge Gaps
- **82 isolated node(s):** `ges-uretim-tahmin-motoru`, `forecastIds`, `readForecasts`, `records`, `colors` (+77 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 151 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Repository` connect `Repository` to `app.py`, `ValidationError`, `SiteConfig`, `OpenMeteoClient`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `SiteConfig` connect `SiteConfig` to `app.py`, `Repository`, `OpenMeteoClient`, `ForecastEngineAcceptanceTests`, `ValidationError`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `ForecastEngine` connect `SiteConfig` to `app.py`, `ValidationError`, `ForecastEngineAcceptanceTests`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `SiteConfig` (e.g. with `_test_site_card()` and `ForecastEngine`) actually correct?**
  _`SiteConfig` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `Repository` (e.g. with `_acceptance_view()` and `_export()`) actually correct?**
  _`Repository` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ForecastEngine` (e.g. with `_run_test_site_comparison()` and `ForecastHour`) actually correct?**
  _`ForecastEngine` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ValidationError` (e.g. with `OpenMeteoClient` and `ForecastEngineAcceptanceTests`) actually correct?**
  _`ValidationError` has 2 INFERRED edges - model-reasoned connections that need verification._