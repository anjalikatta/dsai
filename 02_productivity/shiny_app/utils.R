# -----------------------------------------------------------------------------
# utils.R — Helper functions for FDA Device Recall Shiny app
# Purpose: API client and data formatting for device/recall endpoint.
# -----------------------------------------------------------------------------

# Load API key from .env (tries app dir, parent 02_productivity, then 01_query_api)
# Uses readRenviron(); no dotenv package.
load_env_if_exists = function() {
  candidates = c(
    file.path(getwd(), ".env"),
    file.path(getwd(), "..", ".env"),
    file.path(dirname(getwd()), ".env"),
    file.path(getwd(), "..", "..", "01_query_api", ".env")
  )
  for (p in candidates) {
    if (file.exists(p)) {
      readRenviron(p)
      return(invisible(TRUE))
    }
  }
  invisible(FALSE)
}

# Build FDA device recall query parameters from user inputs
# start_date, end_date: "YYYY-MM-DD"; limit: 1–1000
build_query_params = function(api_key, start_date, end_date, limit = 1000L) {
  search_expr = sprintf(
    "event_date_initiated:[%s TO %s]",
    start_date,
    end_date
  )
  list(
    api_key = api_key,
    search = search_expr,
    limit = as.integer(limit)
  )
}

# Fetch FDA device recalls and return a data frame of results, or throw/error
# base_url: endpoint; params: list from build_query_params
fetch_fda_recalls = function(base_url, params) {
  response = httr::GET(base_url, query = params)
  status = httr::status_code(response)
  if (status != 200L) {
    body = httr::content(response, as = "text", encoding = "UTF-8")
    stop(sprintf("FDA API returned status %s: %s", status, body))
  }
  raw_content = rawToChar(response$content)
  data = jsonlite::fromJSON(raw_content, flatten = TRUE)
  if (is.null(data$results) || !is.data.frame(data$results)) {
    return(data.frame())
  }
  data$results
}

# Select and optionally format key columns for display
# Handles missing columns gracefully
recalls_to_display = function(recalls) {
  cols_wanted = c(
    "recall_number",
    "event_date_initiated",
    "product_code",
    "root_cause_description"
  )
  existing = intersect(names(recalls), cols_wanted)
  if (length(existing) == 0L) return(recalls)
  out = recalls[, existing, drop = FALSE]
  # Format date for readability if present
  if ("event_date_initiated" %in% names(out)) {
    out$event_date_initiated = format_fda_date(out$event_date_initiated)
  }
  out
}

# Format FDA date (e.g. 20240301) to YYYY-MM-DD
format_fda_date = function(x) {
  if (is.null(x) || all(is.na(x))) return(x)
  x = as.character(x)
  # Already looks like YYYY-MM-DD
  if (grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", x[1L])) return(x)
  # YYYYMMDD
  out = rep(NA_character_, length(x))
  ok = nchar(x) >= 8L & !is.na(x)
  if (any(ok)) {
    y = x[ok]
    out[ok] = paste0(
      substr(y, 1L, 4L), "-",
      substr(y, 5L, 6L), "-",
      substr(y, 7L, 8L)
    )
  }
  out
}
