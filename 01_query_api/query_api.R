library(httr)
library(jsonlite)

# 1. Load the key from the .env file
# This looks for .env in the current folder
readRenviron(".env")

# 2. Retrieve the key
api_key <- Sys.getenv("API_KEY")

# Safety check
if (api_key == "") {
  stop("❌ Error: API_KEY not found. Make sure your .env file is in this folder.")
}

# 3. Define the endpoint
url <- "https://api.fda.gov/device/recall.json"
print(paste("📡 Connecting to", url, "..."))

# 4. Make the GET request
# We pass the key and limit=1 as query parameters
response <- GET(url, query = list(api_key = api_key, limit = 1))

# 5. Verify Success
status <- status_code(response)

if (status == 200) {
  print(paste("✅ Success! Status Code:", status))
  
  # Parse the JSON content
  content <- fromJSON(rawToChar(response$content))
  
  print("--- API Metadata ---")
  print(content$meta)
  
  # Optional: Print the first recall number
  print(paste("Example Recall Number:", content$results$recall_number[1]))
  
} else {
  print(paste("❌ Error:", status))
  print(content(response, "text"))
}