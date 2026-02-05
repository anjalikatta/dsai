# -----------------------------------------------------------------------------
# Script: my_good_query.R
# Purpose: Query FDA for Device Recalls (Returning Max Limit)
# -----------------------------------------------------------------------------

library(httr)
library(jsonlite)

# 1. Load API Key
readRenviron("/Users/akatt/dsai/01_query_api/.env")
api_key <- Sys.getenv("API_KEY")

# 2. Define Endpoint
base_url <- "https://api.fda.gov/device/recall.json"

# 3. Define Query
# We set limit to 1000 (FDA Max) to get "all" records in a single page
query_params <- list(
  api_key = api_key,
  search = "event_date_initiated:[2024-01-01 TO 2024-12-31]",
  limit = 1000
)

print("📡 Querying FDA API for 2024 Recalls...")

# 4. Make Request
response <- GET(base_url, query = query_params)
status <- status_code(response)

if (status == 200) {
  print(paste("✅ Success! Status Code:", status))
  
  # Parse Data
  raw_content <- rawToChar(response$content)
  data <- fromJSON(raw_content, flatten = TRUE)
  recalls <- data$results
  
  # ---------------------------------------------------------------------------
  # 📸 Code + Output
  # ---------------------------------------------------------------------------
  print("--- DATA OUTPUT (First 15 Rows) ---")
  print(paste("Total Records Retrieved:", nrow(recalls)))
  
  # Select key columns for easier submission
  # We check for columns that definitely exist
  cols_to_show <- c("recall_number", "event_date_initiated", "product_code", "root_cause_description")
  existing_cols <- intersect(names(recalls), cols_to_show)
  
  # Print 15 rows
  print(head(recalls[, existing_cols], 15))
  
} else {
  print(paste("❌ Error:", status))
  print(content(response, "text"))
}