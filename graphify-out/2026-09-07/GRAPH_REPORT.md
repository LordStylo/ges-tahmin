# Graph Report - staj2  (2026-09-07)

## Corpus Check
- 28 files · ~19,589 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 210 nodes · 380 edges · 21 communities (15 shown, 5 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 25 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Saatlik Üretim Tahmini
- app.py
- What You Must Do When Invoked
- SiteConfig
- Repository
- OpenMeteoClient
- create_app
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

## God Nodes (most connected - your core abstractions)
1. `SiteConfig` - 25 edges
2. `Repository` - 23 edges
3. `ForecastEngine` - 18 edges
4. `ValidationError` - 17 edges
5. `WeatherHour` - 13 edges
6. `OpenMeteoClient` - 13 edges
7. `What You Must Do When Invoked` - 12 edges
8. `ForecastEngineAcceptanceTests` - 10 edges
9. `/graphify` - 10 edges
10. `create_app()` - 9 edges

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

## Communities (21 total, 5 thin omitted)

### Community 0 - "Saatlik Üretim Tahmini"
Cohesion: 0.15
Nodes (13): Graphify Project Instructions, Alternatif Akım (AC), Doğru Akım (DC), Enerji (Wh / kWh), Fiziksel Model, Güç (W / kW), Güneş Enerji Santrali (GES), Hava Durumu Verisi (+5 more)

### Community 1 - "app.py"
Cohesion: 0.15
Nodes (20): _actuals_form(), _analysis_view(), _daily_summary(), _export(), _forecast_form(), _forecast_result(), _format(), _format_history_timestamp() (+12 more)

### Community 2 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 3 - "SiteConfig"
Cohesion: 0.17
Nodes (15): datetime, ForecastHour, MountType, Any, SiteConfig, WeatherHour, GES Saatlik Üretim Tahmin Motoru., ForecastEngine (+7 more)

### Community 4 - "Repository"
Cohesion: 0.24
Nodes (6): Connection, Any, Path, En yeni tahmin sürümlerini, saatlik satırları yüklemeden listeler., Tahmin sürümlerini asla ezmeden saklayan SQLite deposu., Repository

### Community 5 - "OpenMeteoClient"
Cohesion: 0.17
Nodes (9): _canonical_query_value(), compass_to_open_meteo_azimuth(), OpenMeteoClient, Any, Kuzey=0 pusula açısını Open-Meteo'nun Güney=0 açısına çevirir., 20 ile 20.0 gibi eşdeğer girdi biçimlerini aynı önbellek anahtarına indirger., Doğruluk doğrulaması için geçmiş saatlik meteoroloji/GTI serisi., WeatherFetchResult (+1 more)

### Community 6 - "create_app"
Cohesion: 0.27
Nodes (8): AccuracyReport, evaluate_forecast(), Any, _weather_group(), create_app(), Path, main(), ValueError

### Community 7 - "ForecastEngineAcceptanceTests"
Cohesion: 0.42
Nodes (3): ForecastEngineAcceptanceTests, site(), weather()

### Community 8 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 9 - "GES Saatlik Üretim Tahmin Motoru"
Cohesion: 0.29
Nodes (6): GES Saatlik Üretim Tahmin Motoru, Kapsam ve sonraki girdi, Mimari, Model zinciri, Veri kaynağı, önbellek ve lisans, Çalıştırma

### Community 10 - "ValidationError"
Cohesion: 0.19
Nodes (10): _integer(), _number(), _optional_number(), _parse_actual_csv(), _site_from_form(), LossFactors, _multiplier(), Kullanıcıya açıklanabilecek alan doğrulama hatası. (+2 more)

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

## Knowledge Gaps
- **53 isolated node(s):** `ges-uretim-tahmin-motoru`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)`, `Step 1 - Ensure graphify is installed` (+48 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 86 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Repository` connect `Repository` to `app.py`, `SiteConfig`, `OpenMeteoClient`, `create_app`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `SiteConfig` connect `SiteConfig` to `app.py`, `Repository`, `OpenMeteoClient`, `ForecastEngineAcceptanceTests`, `ValidationError`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `ValidationError` connect `ValidationError` to `app.py`, `SiteConfig`, `OpenMeteoClient`, `create_app`, `ForecastEngineAcceptanceTests`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `SiteConfig` (e.g. with `ForecastEngine` and `OpenMeteoClient`) actually correct?**
  _`SiteConfig` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Repository` (e.g. with `_export()` and `_required_forecast()`) actually correct?**
  _`Repository` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `ForecastEngine` (e.g. with `ForecastHour` and `MountType`) actually correct?**
  _`ForecastEngine` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ValidationError` (e.g. with `OpenMeteoClient` and `ForecastEngineAcceptanceTests`) actually correct?**
  _`ValidationError` has 2 INFERRED edges - model-reasoned connections that need verification._