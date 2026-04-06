# lab_multi_agent_with_tools.py
# Multi-Agent System with Tools — FDA Device Recalls
# LAB: Multi-Agent with Function Calling
# Anjali Katta

# This script builds a 2-agent workflow where Agent 1 uses a custom tool to
# fetch FDA device recall data from the openFDA API, and Agent 2 analyzes
# the data and writes a summary report.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import os           # for environment variables
import requests     # for HTTP requests
import json         # for working with JSON
import pandas as pd # for data manipulation

## 0.2 Load Functions #################################

# Load helper functions for agent orchestration
from functions import agent_run, df_as_text

## 0.3 Configuration #################################

# Select model of interest
MODEL = "smollm2:1.7b"

# FDA API key is optional; openFDA works without it (just rate-limited)
FDA_API_KEY = os.getenv("API_KEY", "")

# 1. DEFINE CUSTOM TOOL FUNCTION ###################################

# This function queries the openFDA Device Recall API.
# The API is free; an API key raises the rate limit.
# Docs: https://open.fda.gov/apis/device/recall/

def get_fda_recalls(year=2024, limit=20):
    """
    Fetch device recall data from the openFDA Device Recall API.

    Parameters:
    -----------
    year : int
        The year to search for recalls (default: 2024)
    limit : int
        Maximum number of results to return (default: 20, max: 1000)

    Returns:
    --------
    pandas.DataFrame
        A DataFrame of device recalls with key fields
    """

    url = "https://api.fda.gov/device/recall.json"

    params = {
        "search": f"event_date_initiated:[{year}-01-01 TO {year}-12-31]",
        "limit": min(limit, 1000)
    }
    if FDA_API_KEY:
        params["api_key"] = FDA_API_KEY

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    records = []
    for item in data.get("results", []):
        records.append({
            "recall_number": item.get("recall_number", ""),
            "date": item.get("event_date_initiated", ""),
            "firm": item.get("recalling_firm", ""),
            "root_cause": item.get("root_cause_description", ""),
            "product_code": item.get("product_code", ""),
            "status": item.get("recall_status", "")
        })

    df = pd.DataFrame(records)
    return df

# 2. REGISTER TOOL IN FUNCTIONS MODULE ###################################

# The agent() wrapper in functions.py uses globals() to look up tool
# functions. We inject our function into that module so it can be found.
import functions as _fn
_fn.get_fda_recalls = get_fda_recalls

# 3. DEFINE TOOL METADATA ###################################

# Tool metadata tells the LLM what the function does and what arguments it expects
tool_get_fda_recalls = {
    "type": "function",
    "function": {
        "name": "get_fda_recalls",
        "description": (
            "Fetch device recall data from the openFDA Device Recall API. "
            "Returns a table of recalls with recall number, date, firm, "
            "root cause, product code, and status."
        ),
        "parameters": {
            "type": "object",
            "required": ["year", "limit"],
            "properties": {
                "year": {
                    "type": "number",
                    "description": "The year to search for recalls (e.g. 2024)"
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return (e.g. 20 for a sample, 1000 for all available)"
                }
            }
        }
    }
}

# 4. MULTI-AGENT WORKFLOW ###################################

# Agent 1: Data Fetcher (with tools)
# Uses the get_fda_recalls tool to pull device recall data from the FDA API
role1 = "I fetch device recall data from the openFDA Device Recall API."
task1 = "Get FDA device recall data for year 2024 with a limit of 20 records."

print("📡 Agent 1: Fetching FDA device recall data...")
result1 = agent_run(role=role1, task=task1, model=MODEL, tools=[tool_get_fda_recalls])

# result1 is the DataFrame returned by the get_fda_recalls tool
result1_text = df_as_text(result1)
print(f"   ✅ Retrieved {len(result1)} recall records.\n")
print(result1_text)
print()

# Agent 2: Report Writer (no tools)
# Receives the recall table and writes a short analysis
role2 = (
    "You are an FDA regulatory analyst. Analyze the device recall data and write "
    "a concise report summarizing: 1) the most common root causes, 2) which firms "
    "appear most frequently, and 3) any patterns in timing or status. "
    "Use bullet points. Keep under 200 words."
)
task2 = f"Analyze the following FDA device recall data and write a brief summary:\n\n{result1_text}"

print("📝 Agent 2: Writing recall analysis report...")
result2 = agent_run(role=role2, task=task2, model=MODEL, output="text", tools=None)

# 5. VIEW RESULTS ###################################

print("\n" + "=" * 60)
print("📊 AGENT 1 — FDA Recall Data (Top 10)")
print("=" * 60)
print(result1.head(10).to_string(index=False))

print("\n" + "=" * 60)
print("📰 AGENT 2 — Analysis Report")
print("=" * 60)
print(result2)

print("\n✅ Multi-agent workflow with tools complete.")
