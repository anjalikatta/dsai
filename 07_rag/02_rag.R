# 02_rag.R

# How do I set up an LLM with Retrieval Augmented Generation in R?

# Load libraries
library(dplyr)
library(readr)
library(httr2)
library(jsonlite)
library(ellmer)

PORT = 11434
OLLAMA_HOST = paste0("http://localhost:", PORT)
DOCUMENT = "02_query_ollama/docs/pokemon.csv"


search = function(query, document){
    read_csv(document, show_col_types = FALSE) %>%
        filter(stringr::str_detect(Name, query)) %>%
        as.list() %>%
        jsonlite::toJSON(auto_unbox = TRUE) 
}

search("Pikachu", DOCUMENT)


chat = chat_ollama(
    model = "gemma3:latest",
    base_url = OLLAMA_HOST,
    messages = list(
        list(role = "system", content = "You are a helpful assistant."),
        list(role = "user", content = "What is the capital of France?"),
        list(role = "tool", content = search("Pikachu", DOCUMENT))
    )
)

# get_search = ellmer::tool(
#     fun = search,
#     name = "search",
#     description = "Search the document for the query and return a json of traits",
#     arguments = list(
#         query = type_array(type_string(), "Names"),
#         document = type_array(type_string(), "Document to search")
#     )
# )


