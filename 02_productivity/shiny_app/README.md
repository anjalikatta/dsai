# README '02_productivity/shiny_app'

> Shiny app that runs your FDA device recall API query on demand. Set a date range and limit, click **Query FDA API**, and view results in a sortable, filterable table.

---

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [API key](#api-key)
- [How to run](#how-to-run)
- [Usage](#usage)
- [Files](#files)

---

## Overview

The app implements the same FDA Open API call as [`my_good_query.R`](../01_query_api/my_good_query.R): it queries the **device/recall** endpoint with a date range and limit, then shows key fields (recall number, event date, product code, root cause). The UI provides:

- **Start date** and **End date** for the recall window
- **Max records** (100, 250, 500, or 1000)
- **Query FDA API** button to run the request
- A **data table** with column filters and sorting
- **Status messages** and **error handling** when the API fails or inputs are invalid

---

## Requirements

- R (>= 4.0)
- Packages: **shiny**, **bslib**, **httr**, **jsonlite**, **dplyr**, **DT**

---

## Installation

From the project root or from `02_productivity/shiny_app`:

```r
install.packages(c("shiny", "bslib", "httr", "jsonlite", "dplyr", "DT"))
```

Or, with the app folder as working directory, use the **DESCRIPTION** file:

```r
devtools::install_deps()
```

---

## API key

The app looks for an **API_KEY** in a `.env` file in this order:

1. `02_productivity/shiny_app/.env`
2. `02_productivity/.env`
3. `01_query_api/.env`

Use the same key as in the query API folder (see [README_my_good_query.md](../01_query_api/README_my_good_query.md)). If no key is set, the FDA API may still respond with lower rate limits; the app will show a warning.

---

## How to run

1. Optionally create or copy a `.env` file with `API_KEY=your_key` into `02_productivity`, `shiny_app`, or `01_query_api`.
2. In R or RStudio, set the working directory to `02_productivity/shiny_app` and run:

```r
shiny::runApp(".")
```

Or from the repo root:

```r
shiny::runApp("02_productivity/shiny_app")
```

---

## Usage

1. Choose **Start date** and **End date** (e.g. 2024-01-01 to 2024-12-31).
2. Select **Max records** (up to 1000).
3. Click **Query FDA API**.
4. View the table; use the search boxes and column headers to filter and sort.

---

## Files

| File | Purpose |
|------|--------|
| [`app.R`](app.R) | Main Shiny app (UI + server). |
| [`utils.R`](utils.R) | API helpers: env loading, query params, fetch, date formatting. |
| [`DESCRIPTION`](DESCRIPTION) | R dependencies for the app. |

---

← 🏠 [Back to Top](#table-of-contents)
