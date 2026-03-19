# lab_custom_rag_query.py
# Custom RAG Query: Systems Engineering Project Risk Advisor
# Pairs with LAB_custom_rag_query.md
# Tim Fraser

# This script builds a Retrieval-Augmented Generation (RAG) workflow
# that searches a CSV of systems engineering project risks
# and uses an LLM to provide risk analysis and mitigation advice.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import pandas as pd  # for reading CSV files and data manipulation
import requests      # for HTTP requests
import json          # for working with JSON
import os            # for file path operations

# If you haven't already, install these packages...
# pip install pandas requests

## 0.2 Load Functions #################################

# Load helper functions for agent orchestration
from functions import agent_run

## 0.3 Configuration #################################

# Select model of interest
MODEL = "smollm2:135m"  # use this small model (no function calling, < 200 MB)
PORT = 11434  # use this default port
OLLAMA_HOST = f"http://localhost:{PORT}"  # use this default host
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENT = os.path.join(SCRIPT_DIR, "data", "project_risks.csv")  # path to our risk data

# 1. SEARCH FUNCTION ###################################

def search_risks(query, document):
    """
    Search a CSV of project risks for rows matching the query.
    Checks risk_name, category, description, and mitigation columns.
    
    Parameters:
    -----------
    query : str
        The search term to look for
    document : str
        Path to the CSV file to search
    
    Returns:
    --------
    str
        JSON string of matching rows
    """
    
    # Read the CSV file
    df = pd.read_csv(document)
    
    # Search across multiple columns for the query (case-insensitive)
    mask = (
        df["risk_name"].str.contains(query, case=False, na=False) |
        df["category"].str.contains(query, case=False, na=False) |
        df["description"].str.contains(query, case=False, na=False) |
        df["mitigation"].str.contains(query, case=False, na=False)
    )
    
    # Filter matching rows
    filtered_df = df[mask]
    
    # Convert to dictionary and then to JSON
    result_dict = filtered_df.to_dict(orient="records")
    result_json = json.dumps(result_dict, indent=2)
    
    return result_json

# 2. TEST SEARCH FUNCTION ###################################

# Test search function with a sample query
print("Testing search function...")
test_result = search_risks("security", DOCUMENT)
print("Search result preview:")
print(test_result[:300] + "..." if len(test_result) > 300 else test_result)
print()

# 3. RAG WORKFLOW ###################################

# Suppose the user wants to learn about risks related to a specific category
input_data = {"topic": "technical"}

# Task 1: Data Retrieval - Search the CSV for risks matching the topic
result1 = search_risks(input_data["topic"], DOCUMENT)

# Task 2: Generation augmented with the retrieved data
# Design a system prompt that instructs the LLM to act as a risk advisor
role = (
    "You are a systems engineering risk advisor. "
    "Given JSON data about project risks, output a concise risk briefing in markdown. "
    "Include a title, a numbered list of each risk with its likelihood and impact, "
    "and a short recommended action for each. "
    "End with one overall recommendation for the project manager."
)

# Using our custom agent_run function, which wraps requests.post
result2 = agent_run(role=role, task=result1, model=MODEL, output="text")

# View result
print("Risk Briefing:")
print(result2)
print()

# 4. ALTERNATIVE: MANUAL CHAT APPROACH ###################################

# Alternative: Manual chat approach, using requests.post directly
CHAT_URL = f"{OLLAMA_HOST}/api/chat"

messages = [
    {"role": "system", "content": role},
    {"role": "user", "content": result1}
]

body = {
    "model": MODEL,
    "messages": messages,
    "stream": False
}

response = requests.post(CHAT_URL, json=body)
response.raise_for_status()
response_data = response.json()

result2b = response_data["message"]["content"]

# View result
print("Alternative Approach Result:")
print(result2b)
