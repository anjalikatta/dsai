# README: FDA Device Recalls (openFDA API)

> This README describes **FDA medical device recalls** and how to query them using the openFDA API. The project uses an R script in [`01_query_api`](../01_query_api) to fetch recall data by year and display key fields.

---

## 📋 Table of Contents

- [What Are FDA Device Recalls?](#what-are-fda-device-recalls)
- [The openFDA Device Recall API](#the-openfda-device-recall-api)
- [Query Script and Data](#query-script-and-data)
- [Key Response Fields](#key-response-fields)
- [Quick Start](#quick-start)
- [Related Materials](#related-materials)

---

## 🎯 What Are FDA Device Recalls?

A **recall** is an action taken to address a medical device that violates FDA law. Recalls occur when a device is defective, poses a risk to health, or both. The FDA works with firms to remove or correct products; the **openFDA Device Recall API** exposes this data for programmatic access.

---

## 🔌 The openFDA Device Recall API

| Item | Value |
|------|--------|
| **Base URL** | `https://api.fda.gov/device/recall.json` |
| **Method** | GET |
| **Auth** | Optional `api_key` (higher rate limits with a key) |

**Common parameters:**

| Parameter | Description |
|-----------|-------------|
| `search` | Lucene-style filter (e.g. `event_date_initiated:[2024-01-01 TO 2024-12-31]`) |
| `limit` | Records per response (default 100; max **1000**) |

Example request:

```bash
curl "https://api.fda.gov/device/recall.json?search=event_date_initiated:[2024-01-01+TO+2024-12-31]&limit=100"
```

---

## 📁 Query Script and Data

The course uses an R script that requests up to 1,000 recalls per call (FDA’s maximum), filters by **event date** (e.g. calendar year 2024), and prints total count plus the first 15 rows of selected columns.

| Resource | Description |
|----------|-------------|
| [**`my_good_query.R`**](../01_query_api/my_good_query.R) | R script: GET recall JSON, parse with `jsonlite`, print sample rows. |
| [**README: FDA Device Recall Query Script**](../01_query_api/README_my_good_query.md) | Full docs: endpoint, parameters, data structure, flow diagram, usage. |

Dependencies: **`httr`** and **`jsonlite`**. API key is read from a `.env` file (see [README_my_good_query](../01_query_api/README_my_good_query.md)).

---

## 📊 Key Response Fields

The API returns JSON with `meta` and **`results`** (array of recall records). The script uses these fields:

| Field | Description |
|-------|-------------|
| `recall_number` | Unique FDA recall identifier. |
| `event_date_initiated` | Date the recall was initiated (e.g. `20240115`). |
| `product_code` | FDA product code for the device. |
| `root_cause_description` | Description of the root cause of the recall. |

---

## ⚡ Quick Start

1. **Prerequisites:** R with `httr` and `jsonlite`; optional [FDA API key](https://open.fda.gov/apis/authentication/).
2. **Configure:** Create a `.env` in `01_query_api/` with `API_KEY=your_key` (or run without a key under lower rate limits).
3. **Run:** From project root:

```bash
Rscript 01_query_api/my_good_query.R
```

Or from R: `source("01_query_api/my_good_query.R")`. Adjust paths if your working directory differs.

---

## 📚 Related Materials

- [openFDA Device Recall API](https://open.fda.gov/apis/device/recall/) — official API documentation.
- [READ: Find APIs](../01_query_api/READ_find_apis.md) — how to discover and choose APIs.
- [ACTIVITY: Your API Query](../01_query_api/ACTIVITY_your_api_query.md) — practice building your own API query.

---

← [Back to Top](#readme-fda-device-recalls-openfda-api)
