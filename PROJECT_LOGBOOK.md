# PROJECT LOGBOOK — NSE100 Fundamental Analysis

> **Last Updated:** 2026-04-27  
> **Active Branch:** `scrapper`  
> **Repository:** `Gurkiratsinghk/NSE100-fundamental-analysis`  
> **Purpose of this Document:** Capture the complete project state so development can resume in a new IDE instance with zero context loss.

---

## Table of Contents

1. [Logic Flow & Concepts](#1-logic-flow--concepts)
2. [Changelog & Architecture](#2-changelog--architecture)
3. [Technical Debt & Stability](#3-technical-debt--stability)
4. [Operational Impact](#4-operational-impact)
5. [Pending Tasks](#5-pending-tasks)

---

## 1. Logic Flow & Concepts

### 1.1 — Project Goal

Build an automated data pipeline that:
1. **Fetches** the live NIFTY 100 constituent list from NSE India's API.
2. **Scrapes** detailed financial fundamentals for each company from [ticker.finology.in](https://ticker.finology.in).
3. **Stores** all data in a structured SQLite database using SQLAlchemy ORM.
4. **Exports** the data as analysis-ready CSV files (long-form and wide-pivot).
5. Eventually **syncs** data to Supabase for cloud persistence and integrates CI/CD via GitHub Actions.

### 1.2 — End-to-End Pipeline Flow

```
main.py
  └─ run_full_ingest()                         [pipeline/ingest.py]
       ├─ 1. init_db()                         [data/db.py]
       │     • Validates existing DB file (PRAGMA check)
       │     • Backs up corrupt DBs automatically
       │     • Runs CREATE TABLE IF NOT EXISTS via SQLAlchemy
       │
       ├─ 2. fetch_and_update_nse100()          [scrapers/nse100_list.py]
       │     • Cookie handshake with nseindia.com homepage
       │     • GET /api/equity-stockIndices?index=NIFTY%20100
       │     • Upserts companies table (symbol, name, industry, ISIN)
       │     • Inserts new nse100_constituents rows
       │     • Marks removed companies (removed_date = today)
       │     • Does NOT delete removed companies — keeps them for scraping
       │
       ├─ 3. get_all_scrape_symbols()           [scrapers/nse100_list.py]
       │     • Returns ALL symbols ever seen (active + removed)
       │     • Prevents survivorship bias in historical data
       │
       └─ 4. run_scraper_for_symbols()          [scrapers/finology.py]
             • For each symbol:
             │  ├─ Fetch page HTML from ticker.finology.in/company/{SYMBOL}
             │  ├─ Parse #companyessentials div → key-value metrics
             │  ├─ Parse tables by fixed index position:
             │  │     Table 2 → Profit & Loss (annual)
             │  │     Table 3 → Balance Sheet
             │  │     Table 4 → Cash Flow Statement
             │  │     Table 5 → Promoter Shareholding
             │  │     Table 6 → Investor Shareholding
             │  ├─ Save essentials via UPSERT (always latest snapshot)
             │  └─ Save yearly data via INSERT-ONLY (historical preservation)
             └─ 2-second delay between requests (anti-bot courtesy)
```

### 1.3 — Database Schema (EAV Design)

The database uses an **Entity-Attribute-Value (EAV)** layout for financial data. This means new metrics that Finology adds to their page are captured automatically without any schema migration.

| Table | Purpose | Write Strategy |
|---|---|---|
| `companies` | Master registry — one row per symbol ever observed | Upsert (name, industry, ISIN updated on re-scrape) |
| `nse100_constituents` | Audit trail — tracks when each company entered/left the index | Insert new; set `removed_date` on removal |
| `company_essentials` | Snapshot metrics (Market Cap, P/E, ROE, etc.) | Upsert — always reflects most recent scrape |
| `yearly_financials` | Historical P&L, BS, CF, Shareholding rows | Insert-only — never overwrites existing rows |
| `rankings` | *(stub)* Future fundamental scoring | Not implemented |
| `portfolio` | *(stub)* Future portfolio construction | Not implemented |

**Unique constraints** prevent duplicates:
- `company_essentials`: `(company_id, metric_name)`
- `yearly_financials`: `(company_id, fiscal_year, source_table, metric_name)`

### 1.4 — Value Normalisation Rules

These rules were empirically confirmed via `unit.py` and `dump.txt` HTML inspection:

| Raw Format | Stored As | Rule |
|---|---|---|
| `₹ 5507.82 Cr.` | `55078200000.0` (float) | Cr suffix detected → multiply by 10,000,000 |
| `28.8 %` | `0.288` (float) | % suffix detected → divide by 100 |
| `₹ 333.89` | `333.89` (float) | Rs symbol stripped, no scaling |
| `75 %` (essentials %) | `0.75` (float) | Same % rule |
| `-` or `--` | `NULL` | Dash is null, not zero |
| Non-numeric text | Stored in `value_text` | Preserved as-is for dates, names, etc. |

A **critical guard** was added to skip essentials labels that look like numbers (e.g. `126869_54`), which Finology sometimes emits when their HTML structure is inconsistent.

### 1.5 — Cloudflare / Anti-Bot Bypass (GitHub Actions Context)

For CI/CD execution on GitHub-hosted runners, Finology's Cloudflare protection blocks datacenter IPs. A **hybrid cookie-handoff** approach was developed:

1. **SeleniumBase** (headless=False + pyvirtualdisplay/xvfb) launches a real browser.
2. The browser solves the Cloudflare Turnstile JS challenge via `sb.uc_gui_click_captcha()`.
3. The `cf_clearance` cookie is extracted and passed to a `curl_cffi` session.
4. All subsequent data requests use `curl_cffi` for speed, authenticated by the stolen cookie.

> **Note:** This logic lives on a separate branch/repo (`nse-unified-fundamentals`) and has **not** been merged into this repo's `scrapper` branch yet. See [Pending Tasks](#5-pending-tasks).

---

## 2. Changelog & Architecture

### 2.1 — File Inventory & Rationale

#### Core Package: `nse_project/`

| File | Size | Purpose | Status |
|---|---|---|---|
| `main.py` | 98 B | Entry point — calls `run_full_ingest()` | ✅ Stable |
| `requirements.txt` | 159 B | Python dependencies (requests, bs4, sqlalchemy, loguru, etc.) | ✅ Stable |
| `configs/default.yaml` | 2 B | Placeholder — not yet wired | ⚠️ Empty |
| `data/db.py` | 3.2 KB | SQLAlchemy engine, session factory, corrupt-DB recovery | ✅ Stable |
| `data/models.py` | 7.3 KB | ORM table definitions (Company, Essentials, Yearly, stubs) | ✅ Stable |
| `data/nse_fundamentals.db` | 3.7 MB | Live SQLite database with scraped data | ✅ Active |
| `scrapers/finology.py` | 21.2 KB | Main scraper: fetch, parse, persist Finology data | ✅ Stable, well-documented |
| `scrapers/nse100_list.py` | 12.2 KB | NSE API integration: constituent sync, removal tracking | ✅ Stable |
| `pipeline/ingest.py` | 2.8 KB | Orchestrator: init → list sync → scrape → summarize | ✅ Stable |
| `reports/export.py` | 6.2 KB | CSV export: raw tables, wide-pivot, essentials pivot | ✅ Stable |

#### Root-Level Utility Scripts

| File | Purpose | Status |
|---|---|---|
| `test_scraper.py` | Quick smoke test — scrapes one company and prints essentials | 🔧 Dev utility |
| `unit.py` | Deep HTML inspection of ABB's Finology page — confirmed table indices and essentials parsing | 🔧 Dev utility, foundational research |
| `fetch_html.py` | Dumps raw `#companyessentials` HTML to `dump.txt` for debugging | 🔧 Dev utility |
| `dump.txt` | Raw HTML output from `fetch_html.py` | 🔧 Debug artifact |
| `clean_db.py` | One-time cleanup script — deletes rows where numeric junk leaked into `metric_name` | 🔧 One-off fix (already run) |
| `query_db.py` | Diagnostic query for bad metric names in `company_essentials` | 🔧 One-off diagnostic |

#### Legacy Data

| File/Dir | Notes |
|---|---|
| `NSE data/companies.csv` | Original CSV import of NIFTY 100 from before the API approach |
| `NSE data/ind_nifty100list.csv` | Raw NSE CSV download — replaced by live API |
| `README.md` | Historical development log (Jan 2025 entries) — needs updating |

### 2.2 — Key Architectural Decisions

| Decision | Why This Approach | Alternative Considered |
|---|---|---|
| **EAV (key-value) schema** for financials | New metrics appear/disappear on Finology without notice — EAV stores them without schema changes | Wide-column table — rejected because columns would need manual migration for each new metric |
| **Insert-only for yearly data** | Historical rows must never be overwritten — each scrape adds only new fiscal years | Full upsert — rejected to prevent accidental data loss |
| **Upsert for essentials** | Essentials are a "latest snapshot" — P/E, Market Cap change daily | Insert-only would create unbounded row growth for volatile metrics |
| **Scrape removed companies** | Prevents survivorship bias; removed companies retain full fundamentals history | Skip removed — rejected to avoid data gaps |
| **`lxml` parser** for BeautifulSoup | Faster and more tolerant than `html.parser`; required for Finology's messy HTML | `html5lib` — slower; `html.parser` — chokes on edge cases |
| **Fixed table-index positions** | Finology's page structure is consistent; indices 2-6 confirmed via `unit.py` inspection | CSS class selectors — rejected because Finology's classes are not unique enough |
| **Loguru** for logging | Structured, colored output with severity levels; `.success()` method is convenient | stdlib `logging` — less ergonomic for CLI output |

### 2.3 — Git Branch Structure

| Branch | Purpose | State |
|---|---|---|
| `main` | Production-ready, merged features | Behind `scrapper` |
| `scrapper` *(active)* | Primary development branch with full scraping pipeline | ✅ Clean, up to date |
| `db-management` | Database-related changes (scaling, cleanup) | Merged/stale |
| `scrapper-copy` | Safety copy before risky changes | Stale |

---

## 3. Technical Debt & Stability

### 3.1 — Stability Matrix

| Component | Stability | Notes |
|---|---|---|
| `data/models.py` | 🟢 Production-ready | Well-structured ORM with constraints, relationships, docstrings |
| `data/db.py` | 🟢 Production-ready | Corrupt-DB recovery, context-managed sessions |
| `scrapers/finology.py` | 🟢 Production-ready | Comprehensive parsing with edge-case handling, well-documented |
| `scrapers/nse100_list.py` | 🟢 Production-ready | Full API integration with cookie handshake, removal tracking |
| `pipeline/ingest.py` | 🟢 Production-ready | Clean orchestration with summary statistics |
| `reports/export.py` | 🟢 Production-ready | Wide-pivot and raw export fully functional |
| `main.py` | 🟡 Minimal | Works but has no CLI arguments, no mode selection |
| `configs/default.yaml` | 🔴 Empty | Not wired to any configuration system |
| `README.md` | 🔴 Severely outdated | References Jan 2025 Playwright/Selenium experiments — needs complete rewrite |
| `.gitignore` | 🟡 Incomplete | Missing: `.env`, `*.db`, `__pycache__/` patterns for nested dirs, `.venv/` |
| `.gitattributes` | 🟡 Incomplete | No Git LFS tracking for `.db` files (discussed but not implemented) |
| Root scripts (`unit.py`, etc.) | 🔴 Quick & dirty | Useful for debugging but not organized; should be moved to a `scripts/` or `tests/` directory |

### 3.2 — Known Technical Debt Items

1. **No CLI interface.** `main.py` runs the full pipeline with no arguments. There's no way to:
   - Run only the NSE100 list sync
   - Scrape a single company
   - Export specific tables
   - Select between `nse100` mode or `full` mode
   
2. **No `.env` / environment variable support.** Supabase credentials, API keys, and configuration are not externalized. The `python-dotenv` dependency is installed but unused.

3. **No Supabase sync.** Supabase was discussed as the cloud persistence target but sync logic has not been implemented in this repo.

4. **No GitHub Actions workflow.** CI/CD configuration (including the Cloudflare bypass) was developed in the context of a separate `nse-unified-fundamentals` repo and hasn't been ported here.

5. **No resume/checkpoint support.** If the scraper crashes at company 47/100, it restarts from scratch. A `last_scraped_at` or state file is needed.

6. **No backup rotation.** Database backups are only created when corruption is detected. There's no scheduled backup strategy (Parquet snapshots, timestamped copies, etc.).

7. **Two virtual environments** (`.venv` and `.venv-1`) exist in the root — only one should be canonical.

8. **Corrupt `.bak` files** (`nse_fundamentals.corrupt.*.bak`) are 2 bytes each — they were created when the DB file was empty/invalid during early development. Safe to delete.

9. **No automated tests.** `unit.py` is a manual inspection script, not a pytest suite. There's no test coverage for parsing logic, DB writes, or export correctness.

10. **`_SLEEP_SEC = 2` is hardcoded.** Should be configurable and potentially use jitter (randomized delay) to reduce bot-detection risk.

---

## 4. Operational Impact

### 4.1 — Current System Performance

| Metric | Value |
|---|---|
| Database size | ~3.7 MB (SQLite) |
| Companies tracked | ~100+ (active + historically removed) |
| Data tables scraped per company | 5 (P&L, BS, CF, Promoter Shareholding, Investor Shareholding) |
| Essentials metrics per company | ~16 (Market Cap, P/E, P/B, EPS, ROE, ROCE, etc.) |
| Scrape time per company | ~2–4 seconds (+ 2s inter-request sleep) |
| Full pipeline run | ~10–15 minutes for 100 companies |
| Export formats | CSV (raw table dump, wide-pivot, essentials pivot) |

### 4.2 — Impact of Recent Changes

| Change | Impact |
|---|---|
| **Value normalisation fix** (Cr → ×10M, % → ÷100) | All financial values are now stored as base-unit numbers. Previous corrupted values were cleaned via `clean_db.py`. Ensures downstream analysis doesn't need unit conversion. |
| **Numeric-label guard** in essentials parser | Prevents junk data (misplaced numeric IDs from Finology's HTML) from polluting the `metric_name` column. Eliminates the root cause of the bug that required `clean_db.py`. |
| **NSE100 removal tracking** | Companies leaving the index are flagged but continue to be scraped. This preserves full longitudinal data coverage — critical for backtesting and portfolio analytics that account for delistings. |
| **EAV schema adoption** | Future-proofs the database against Finology page structure changes. No more schema migrations when new financial metrics appear. Trade-off: queries are slightly more complex (require pivot/unpivot). |

### 4.3 — Data Integrity Status

- ✅ All `company_essentials` values are clean (post `clean_db.py` run)
- ✅ All `yearly_financials` values use normalised units
- ✅ Unique constraints prevent duplicate rows
- ⚠️ No automated validation suite to catch regressions

---

## 5. Pending Tasks

### Priority 1 — Critical for Production Use

- [ ] **Implement CLI interface** — Add argument parsing to `main.py` for mode selection (`--sync-list`, `--scrape`, `--export`, `--symbol RELIANCE`)
- [ ] **Add `.env` support** — Wire `python-dotenv` to load Supabase URL, API key, and scraper configuration
- [ ] **Implement resume/checkpoint** — Track `last_scraped_at` per company; on restart, skip already-scraped symbols for the current run
- [ ] **Set up GitHub Actions** — Port the workflow from `nse-unified-fundamentals` (including Cloudflare bypass with SeleniumBase + xvfb) into this repo's `.github/workflows/`

### Priority 2 — Data Robustness

- [ ] **Implement Supabase sync** — After each scrape run, push delta changes to Supabase; implement a "keep-alive" ping to prevent project suspension
- [ ] **Add Git LFS for `.db` files** — Configure `.gitattributes` to track `*.db` via LFS; prevents repo bloat
- [ ] **Implement Parquet backups** — Export DB tables as `.parquet` files alongside CSV for efficient archival
- [ ] **Add backup rotation** — Timestamped, mode-aware backups (e.g., `nse100_2026-04-27.db.bak`)
- [ ] **Add randomized jitter** — Replace fixed `_SLEEP_SEC = 2` with `random.uniform(1.5, 4.0)` to reduce detection risk

### Priority 3 — Code Quality & Cleanup

- [ ] **Rewrite `README.md`** — Replace outdated Jan 2025 entries with current architecture overview
- [ ] **Move root scripts to `scripts/` or `tests/`** — Relocate `unit.py`, `fetch_html.py`, `clean_db.py`, `query_db.py`, `test_scraper.py`
- [ ] **Delete dead artifacts** — Remove `dump.txt`, `.bak` files, duplicate `.venv-1/` directory
- [ ] **Wire `configs/default.yaml`** — Define configurable parameters (sleep time, timeouts, table indices, export paths)
- [ ] **Update `.gitignore`** — Add patterns for `.env`, `*.db`, `.venv*/`, `*.bak`, `reports/*.csv`
- [ ] **Write pytest suite** — Unit tests for `_parse_value()`, `_to_snake()`, `_parse_essentials()`, `_parse_table()`, and export pivots

### Priority 4 — Future Features

- [ ] **Implement `rankings` table logic** — Fundamental scoring based on configurable weight profiles
- [ ] **Implement `portfolio` table logic** — Allocation suggestions and historical tracking
- [ ] **Add Screener.in integration** — Secondary data source for cross-validation (referenced in original README)
- [ ] **Special character handling** — Symbols like `M&M` need URL encoding in the Finology scraper
- [ ] **Search fallback** — When a symbol's direct URL 404s, search Finology's search API to resolve the correct page

---

## Quick-Start for New IDE Instance

```bash
# 1. Activate the virtual environment
cd "D:\Git Clones\NSE100-fundamental-analysis"
.venv\Scripts\activate

# 2. Install dependencies
pip install -r nse_project/requirements.txt

# 3. Run the full pipeline (careful — scrapes all 100+ companies)
cd nse_project
python main.py

# 4. Or test a single company
cd ..
python test_scraper.py

# 5. Export data to CSV
python -c "from nse_project.reports.export import export_table, export_essentials; export_table('yearly_financials'); export_essentials()"
```

---

*End of logbook. Update this document whenever significant changes are made to preserve continuity.*
