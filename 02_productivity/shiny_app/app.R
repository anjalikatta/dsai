# -----------------------------------------------------------------------------
# app.R — FDA Device Recall Explorer (Shiny)
# Purpose: Query FDA device/recall API with date range and limit; show results.
# -----------------------------------------------------------------------------

# 0. SETUP ###################################

## 0.1 Load packages #################################

if (!requireNamespace("DT", quietly = TRUE)) {
  install.packages("DT", repos = "https://cloud.r-project.org")
}
library(shiny)
library(bslib)
library(httr)
library(jsonlite)
library(dplyr)
library(DT)

# Helpers: inlined so app works when sourced from any working directory (see utils.R for same code)
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
build_query_params = function(api_key, start_date, end_date, limit = 1000L) {
  search_expr = sprintf("event_date_initiated:[%s TO %s]", start_date, end_date)
  list(api_key = api_key, search = search_expr, limit = as.integer(limit))
}
fetch_fda_recalls = function(base_url, params) {
  response = httr::GET(base_url, query = params)
  status = httr::status_code(response)
  if (status != 200L) {
    body = httr::content(response, as = "text", encoding = "UTF-8")
    stop(sprintf("FDA API returned status %s: %s", status, body))
  }
  data = jsonlite::fromJSON(rawToChar(response$content), flatten = TRUE)
  if (is.null(data$results) || !is.data.frame(data$results)) return(data.frame())
  data$results
}
format_fda_date = function(x) {
  if (is.null(x) || all(is.na(x))) return(x)
  x = as.character(x)
  if (grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", x[1L])) return(x)
  out = rep(NA_character_, length(x))
  ok = nchar(x) >= 8L & !is.na(x)
  if (any(ok)) {
    y = x[ok]
    out[ok] = paste0(substr(y, 1L, 4L), "-", substr(y, 5L, 6L), "-", substr(y, 7L, 8L))
  }
  out
}
recalls_to_display = function(recalls) {
  cols_wanted = c("recall_number", "event_date_initiated", "product_code", "root_cause_description")
  existing = intersect(names(recalls), cols_wanted)
  if (length(existing) == 0L) return(recalls)
  out = recalls[, existing, drop = FALSE]
  if ("event_date_initiated" %in% names(out)) out$event_date_initiated = format_fda_date(out$event_date_initiated)
  out
}

## 0.2 Constants ####################################

FDA_RECALL_URL = "https://api.fda.gov/device/recall.json"
LIMIT_CHOICES = c(100, 250, 500, 1000)

# ---- UI ----

ui = page_fillable(
  theme = bs_theme(
    bootswatch = "flatly",
    primary = "#2c3e50",
    base_font = bslib::font_google("Source Sans 3"),
    heading_font = bslib::font_google("Source Sans 3")
  ),
  title = "FDA Device Recall Explorer",
  padding = 24,
  # Header
  div(
    class = "text-center mb-4",
    h1("FDA Device Recall Explorer", class = "mb-2"),
    p(
      "Query the FDA Open API for device recalls by date range. Set start and end dates, choose a result limit, then click Query.",
      class = "text-muted"
    )
  ),
  layout_columns(
    col_widths = c(12, 12),
    row_heights = c("auto", "1fr"),
    # Card: Inputs
    card(
      card_header("Query parameters"),
      fill = TRUE,
      layout_columns(
        col_widths = c(3, 3, 3, 3, 12),
        dateInput(
          "start_date",
          "Start date",
          value = "2024-01-01",
          max = Sys.Date(),
          width = "100%"
        ),
        dateInput(
          "end_date",
          "End date",
          value = "2024-12-31",
          max = Sys.Date(),
          width = "100%"
        ),
        selectInput(
          "limit",
          "Max records",
          choices = LIMIT_CHOICES,
          selected = 1000,
          width = "100%"
        ),
        div(
          class = "d-flex align-items-end",
          actionButton("query_btn", "Query FDA API", class = "btn-primary", icon = icon("search"))
        ),
        uiOutput("status_ui")
      )
    ),
    # Card: Results table
    card(
      card_header("Recalls"),
      full_screen = TRUE,
      uiOutput("table_placeholder"),
      DT::dataTableOutput("recall_table")
    )
  )
)

# ---- Server ----

server = function(input, output, session) {
  # Reactive value holding the last fetched recalls data frame
  recalls_data = reactiveVal(NULL)
  # Reactive value for status message (success or error text)
  status_msg = reactiveVal(list(type = "info", text = "Set dates and click Query FDA API."))

  # Load .env once at startup (so API key is available)
  load_env_if_exists()
  api_key = reactive(Sys.getenv("API_KEY"))

  # Run query when button is clicked
  observeEvent(input$query_btn, {
    start = as.character(input$start_date)
    end = as.character(input$end_date)
    if (start > end) {
      status_msg(list(type = "error", text = "Start date must be on or before end date."))
      recalls_data(NULL)
      return()
    }
    key = api_key()
    if (is.null(key) || key == "") {
      status_msg(list(
        type = "warning",
        text = "No API_KEY in .env. Query may hit rate limits; add API_KEY to a .env file in this folder, 02_productivity, or 01_query_api."
      ))
    }
    params = build_query_params(key, start, end, as.integer(input$limit))
    status_msg(list(type = "info", text = "Querying FDA API…"))
    recalls_data(NULL)

    tryCatch(
      {
        withProgress(message = "Fetching recalls…", value = 0, {
          raw_recalls = fetch_fda_recalls(FDA_RECALL_URL, params)
          tbl = recalls_to_display(raw_recalls)
          recalls_data(tbl)
          n = nrow(tbl)
          status_msg(list(
            type = "success",
            text = sprintf("Retrieved %d recall record(s).", n)
          ))
        })
      },
      error = function(e) {
        recalls_data(NULL)
        status_msg(list(
          type = "error",
          text = paste0("Error: ", conditionMessage(e))
        ))
      }
    )
  })

  # Status message UI
  output$status_ui = renderUI({
    msg = status_msg()
    cls = switch(
      msg$type,
      success = "text-success",
      error = "text-danger",
      warning = "text-warning",
      "text-muted"
    )
    div(class = paste("mt-2", cls), strong(msg$text))
  })

  # Placeholder when no data
  output$table_placeholder = renderUI({
    if (is.null(recalls_data()) || nrow(recalls_data()) == 0L) {
      div(
        class = "text-muted text-center py-5",
        p("No data yet. Use the query parameters above and click Query FDA API.")
      )
    } else {
      NULL
    }
  })

  # DataTable of recalls
  output$recall_table = DT::renderDataTable({
    df = recalls_data()
    if (is.null(df) || nrow(df) == 0L) return(NULL)
    DT::datatable(
      df,
      options = list(
        pageLength = 25,
        lengthMenu = c(10, 25, 50, 100),
        scrollX = TRUE,
        dom = "Blfrtip"
      ),
      rownames = FALSE,
      filter = "top"
    )
  })
}

# ---- Run app ----

shinyApp(ui, server)
