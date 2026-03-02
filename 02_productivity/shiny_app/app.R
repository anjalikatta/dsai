# -----------------------------------------------------------------------------
# app.R — FDA Device Recall Explorer (Shiny)
# Purpose: Query FDA device/recall API with date range and limit; show results
#          and generate AI-powered analytical reports via OpenAI.
# -----------------------------------------------------------------------------

# 0. SETUP ###################################

## 0.1 Load packages #################################

if (!requireNamespace("DT", quietly = TRUE)) {
  install.packages("DT", repos = "https://cloud.r-project.org")
}
if (!requireNamespace("markdown", quietly = TRUE)) {
  install.packages("markdown", repos = "https://cloud.r-project.org")
}
library(shiny)
library(bslib)
library(httr)
library(jsonlite)
library(dplyr)
library(DT)
library(markdown)

httr::set_config(httr::config(ssl_verifypeer = FALSE, ssl_verifyhost = FALSE))

## 0.2 Helpers #################################

# Load ALL .env files found (root has OPENAI_API_KEY, 01_query_api has API_KEY)
load_env_if_exists = function() {
  candidates = c(
    file.path(getwd(), ".env"),
    file.path(getwd(), "..", ".env"),
    file.path(dirname(getwd()), ".env"),
    file.path(getwd(), "..", "..", ".env"),
    file.path(getwd(), "..", "01_query_api", ".env"),
    file.path(getwd(), "..", "..", "01_query_api", ".env")
  )
  for (p in candidates) {
    if (file.exists(p)) readRenviron(p)
  }
  invisible(TRUE)
}

build_query_params = function(api_key, start_date, end_date, limit = 1000L) {
  search_expr = sprintf("event_date_initiated:[%s TO %s]", start_date, end_date)
  list(api_key = api_key, search = search_expr, limit = as.integer(limit))
}

fetch_fda_recalls = function(base_url, params) {
  resp = httr::GET(base_url, query = list(
    api_key = params$api_key,
    search  = params$search,
    limit   = params$limit
  ))
  httr::stop_for_status(resp)
  raw_text = httr::content(resp, as = "text", encoding = "UTF-8")
  # Parse WITHOUT building a data frame — the FDA response has deeply nested
  # objects (openfda, etc.) that make flatten/simplifyDataFrame very slow.
  data = jsonlite::fromJSON(raw_text, simplifyDataFrame = FALSE)
  if (is.null(data$results) || length(data$results) == 0L) return(data.frame())
  # Extract only the scalar fields we need from the list of records
  extract = function(field) {
    vapply(data$results, function(x) {
      val = x[[field]]
      if (is.null(val)) NA_character_ else as.character(val)
    }, character(1))
  }
  data.frame(
    recall_number          = extract("recall_number"),
    event_date_initiated   = extract("event_date_initiated"),
    product_code           = extract("product_code"),
    root_cause_description = extract("root_cause_description"),
    stringsAsFactors       = FALSE
  )
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

# Process recall data into a structured text summary for the AI prompt
# Mirrors the data-processing pipeline from ai_reporter.py
build_data_summary = function(df, start_date, end_date) {
  total_recalls = nrow(df)

  # Parse dates for monthly aggregation
  dates = as.Date(df$event_date_initiated)

  # Top root causes (if column exists)
  root_cause_text = "(not available)"
  if ("root_cause_description" %in% names(df)) {
    rc = df %>% count(root_cause_description, sort = TRUE) %>% head(10)
    root_cause_text = paste(sprintf("  %s: %d", rc$root_cause_description, rc$n), collapse = "\n")
  }

  # Monthly recall counts
  month_df = data.frame(date = dates) %>%
    mutate(month_num = as.integer(format(date, "%m")), month_name = format(date, "%B")) %>%
    count(month_num, month_name) %>%
    arrange(month_num)
  monthly_text = paste(sprintf("  %s: %d", month_df$month_name, month_df$n), collapse = "\n")

  # Sample records (first 5 rows)
  sample_text = paste(
    utils::capture.output(print(head(df, 5), row.names = FALSE)),
    collapse = "\n"
  )

  sprintf(
    "FDA Medical Device Recall Data (%s to %s):
- Total recalls retrieved: %d

Top 10 Root Causes of Recall:
%s

Monthly Recall Counts:
%s

Sample Records (first 5):
%s",
    start_date, end_date, total_recalls,
    root_cause_text, monthly_text, sample_text
  )
}

# Call OpenAI chat completions API via curl (consistent with fetch_fda_recalls)
call_openai = function(api_key, prompt, model = "gpt-4o-mini") {
  body = list(
    model = model,
    messages = list(list(role = "user", content = prompt))
  )
  tmp_in = tempfile(fileext = ".json")
  writeLines(jsonlite::toJSON(body, auto_unbox = TRUE), tmp_in)
  tmp_out = tempfile(fileext = ".json")
  cmd = sprintf(
    'curl.exe -s -k -o "%s" -X POST "https://api.openai.com/v1/chat/completions" -H "Authorization: Bearer %s" -H "Content-Type: application/json" -d @"%s"',
    tmp_out, api_key, tmp_in
  )
  exit_code = system(cmd, intern = FALSE, wait = TRUE)
  unlink(tmp_in)
  if (exit_code != 0L) stop("OpenAI API request failed (curl exit code ", exit_code, ")")
  if (!file.exists(tmp_out) || file.size(tmp_out) == 0L) stop("OpenAI API returned empty response")
  result = jsonlite::fromJSON(tmp_out)
  unlink(tmp_out)
  if (!is.null(result$error)) stop("OpenAI error: ", result$error$message)
  result$choices$message$content[[1]]
}

## 0.3 Constants ####################################

FDA_RECALL_URL = "https://api.fda.gov/device/recall.json"
LIMIT_CHOICES  = c(100, 250, 500, 1000)

# Default AI prompt template — {data_summary} is replaced at runtime.
# Prompt design note (from ai_reporter.py iteration 3):
#   v1 "Summarize this data" was too vague; v2 added structure but
#   inconsistent length; v3 adds sentence/bullet counts and tone guidance.
DEFAULT_PROMPT = "You are a data analyst preparing a report on FDA medical device recalls.

Analyze this data and write a structured report:

{data_summary}

Report requirements:
1. **Executive Summary**: 2-3 sentence overview of the recall landscape
2. **Key Findings**: Exactly 4 bullet points highlighting the most important patterns
3. **Root Cause Analysis**: 2-3 sentences on the dominant causes and what they suggest
4. **Monthly Trends**: 2-3 sentences on how recall volume changed throughout the year
5. **Recommendations**: 3 actionable bullet points for device manufacturers or regulators

Format as Markdown with ## headers for each section. Be specific and reference actual numbers from the data. Keep the tone professional and concise."

# ---- UI ----

ui = page_fillable(
  theme = bs_theme(
    bootswatch = "flatly",
    primary = "#2c3e50"
  ),
  title = "FDA Device Recall Explorer",
  padding = 24,
  # Header
  div(
    class = "text-center mb-4",
    h1("FDA Device Recall Explorer", class = "mb-2"),
    p(
      "Query the FDA Open API for device recalls, explore the results, and generate AI-powered analytical reports.",
      class = "text-muted"
    )
  ),
  # Card: Query parameters
  card(
    card_header("Query parameters"),
    layout_columns(
      col_widths = c(3, 3, 3, 3, 12),
      dateInput("start_date", "Start date", value = "2024-01-01", max = Sys.Date(), width = "100%"),
      dateInput("end_date", "End date", value = "2024-12-31", max = Sys.Date(), width = "100%"),
      selectInput("limit", "Max records", choices = LIMIT_CHOICES, selected = 1000, width = "100%"),
      div(
        class = "d-flex align-items-end",
        actionButton("query_btn", "Query FDA API", class = "btn-primary", icon = icon("search"))
      ),
      uiOutput("status_ui")
    )
  ),
  # Tabbed results: Recalls Table | AI Report
  navset_card_tab(
    id = "results_tabs",
    full_screen = TRUE,
    # Tab 1: Data Table
    nav_panel(
      title = "Recalls Table",
      icon = icon("table"),
      uiOutput("table_placeholder"),
      DT::dataTableOutput("recall_table")
    ),
    # Tab 2: AI Report
    nav_panel(
      title = "AI Report",
      icon = icon("robot"),
      # Controls row: model selector, generate button, status
      layout_columns(
        col_widths = c(2, 3, 7),
        selectInput(
          "ai_model", "Model",
          choices = c("gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"),
          width = "100%"
        ),
        div(
          class = "d-flex align-items-end",
          actionButton("generate_btn", "Generate Report", class = "btn-success", icon = icon("wand-magic-sparkles"))
        ),
        uiOutput("ai_status_ui")
      ),
      # Generated report card (main area)
      card(
        card_header("Generated report"),
        full_screen = TRUE,
        uiOutput("report_placeholder"),
        uiOutput("report_output")
      ),
      # Prompt is collapsed by default so it stays out of the way
      accordion(
        open = FALSE,
        accordion_panel(
          title = "Prompt settings",
          icon = icon("sliders"),
          textAreaInput(
            "ai_prompt", "Prompt template",
            value = DEFAULT_PROMPT,
            width = "100%", height = "180px"
          ),
          p(
            class = "text-muted small",
            "Use {data_summary} as a placeholder \u2014 it will be replaced with the processed recall data."
          )
        )
      )
    )
  )
)

# ---- Server ----

server = function(input, output, session) {
  recalls_data = reactiveVal(NULL)
  status_msg   = reactiveVal(list(type = "info", text = "Set dates and click Query FDA API."))
  ai_status    = reactiveVal(list(type = "info", text = "Query data first, then generate a report."))
  report_md    = reactiveVal(NULL)

  # Load all .env files at startup so both API_KEY and OPENAI_API_KEY are available
  load_env_if_exists()
  api_key    = reactive(Sys.getenv("API_KEY"))
  openai_key = reactive(Sys.getenv("OPENAI_API_KEY"))

  # ---- FDA Query ----
  observeEvent(input$query_btn, {
    start = as.character(input$start_date)
    end   = as.character(input$end_date)
    if (start > end) {
      status_msg(list(type = "error", text = "Start date must be on or before end date."))
      recalls_data(NULL)
      return()
    }
    key = api_key()
    if (is.null(key) || key == "") {
      status_msg(list(type = "warning", text = "No API_KEY in .env. Query may hit rate limits."))
    }
    params = build_query_params(key, start, end, as.integer(input$limit))
    status_msg(list(type = "info", text = "Querying FDA API\u2026"))
    recalls_data(NULL)
    report_md(NULL)

    tryCatch(
      {
        withProgress(message = "Fetching recalls\u2026", value = 0, {
          raw = fetch_fda_recalls(FDA_RECALL_URL, params)
          tbl = recalls_to_display(raw)
          recalls_data(tbl)
          n = nrow(tbl)
          status_msg(list(type = "success", text = sprintf("Retrieved %d recall record(s).", n)))
          ai_status(list(type = "info", text = sprintf("%d records ready. Click Generate Report.", n)))
        })
      },
      error = function(e) {
        recalls_data(NULL)
        status_msg(list(type = "error", text = paste0("Error: ", conditionMessage(e))))
      }
    )
  })

  # ---- AI Report Generation ----
  observeEvent(input$generate_btn, {
    tbl = recalls_data()
    if (is.null(tbl) || nrow(tbl) == 0L) {
      ai_status(list(type = "error", text = "No recall data. Run the FDA query first."))
      return()
    }
    oai_key = openai_key()
    if (is.null(oai_key) || oai_key == "") {
      ai_status(list(type = "error", text = "OPENAI_API_KEY not found. Add it to your .env file."))
      return()
    }
    ai_status(list(type = "info", text = "Sending data to OpenAI\u2026"))
    report_md(NULL)

    tryCatch(
      {
        withProgress(message = "Generating AI report\u2026", value = 0, {
          # Build structured data summary (mirrors ai_reporter.py pipeline)
          summary_text = build_data_summary(
            tbl, as.character(input$start_date), as.character(input$end_date)
          )
          # Inject summary into prompt template
          final_prompt = gsub("{data_summary}", summary_text, input$ai_prompt, fixed = TRUE)
          # Call OpenAI API
          report = call_openai(oai_key, final_prompt, model = input$ai_model)
          report_md(report)
          ai_status(list(type = "success", text = "Report generated successfully."))
        })
      },
      error = function(e) {
        report_md(NULL)
        ai_status(list(type = "error", text = paste0("Error: ", conditionMessage(e))))
      }
    )
  })

  # ---- UI Outputs ----
  output$status_ui = renderUI({
    msg = status_msg()
    cls = switch(msg$type, success = "text-success", error = "text-danger", warning = "text-warning", "text-muted")
    div(class = paste("mt-2", cls), strong(msg$text))
  })

  output$ai_status_ui = renderUI({
    msg = ai_status()
    cls = switch(msg$type, success = "text-success", error = "text-danger", warning = "text-warning", "text-muted")
    div(class = paste("mt-2 d-flex align-items-end", cls), strong(msg$text))
  })

  output$table_placeholder = renderUI({
    if (is.null(recalls_data()) || nrow(recalls_data()) == 0L) {
      div(class = "text-muted text-center py-5", p("No data yet. Use the query parameters above and click Query FDA API."))
    }
  })

  output$recall_table = DT::renderDataTable({
    df = recalls_data()
    if (is.null(df) || nrow(df) == 0L) return(NULL)
    DT::datatable(
      df,
      options = list(pageLength = 25, lengthMenu = c(10, 25, 50, 100), scrollX = TRUE, dom = "Blfrtip"),
      rownames = FALSE,
      filter = "top"
    )
  })

  output$report_placeholder = renderUI({
    if (is.null(report_md())) {
      div(class = "text-muted text-center py-5", p("No report yet. Query data, then click Generate Report."))
    }
  })

  # Render the AI-generated markdown as HTML
  output$report_output = renderUI({
    md = report_md()
    if (is.null(md)) return(NULL)
    HTML(markdown::markdownToHTML(text = md, fragment.only = TRUE))
  })
}

# ---- Run app ----

shinyApp(ui, server)
