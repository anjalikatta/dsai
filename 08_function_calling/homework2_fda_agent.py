# homework2_fda_agent.py
# AI Agent System with RAG and Tools — FDA Device Recalls
# Homework 2: Compiles work from LAB_prompt_design, LAB_custom_rag_query,
# and LAB_multi_agent_with_tools
# Anjali Katta

# This script combines multi-agent orchestration, RAG integration, and
# function calling into a unified AI agent system for analyzing FDA device
# recalls. Three agents work together:
#   Agent 1 (Data Fetcher)      — uses function calling to query the FDA API
#   Agent 2 (Context Researcher) — uses RAG to retrieve domain knowledge
#   Agent 3 (Executive Reporter) — synthesizes data + context into a report

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import os           # for environment variables and file paths
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

# Path to the RAG knowledge base (in the 07_rag module)
RAG_KNOWLEDGE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "07_rag", "data", "fda_recall_knowledge.txt"
)

print("=" * 60)
print("📋 FDA Device Recall AI Agent System")
print("   Homework 2 — Multi-Agent + RAG + Function Calling")
print("=" * 60)
print()

# ============================================================
# COMPONENT 1: FUNCTION CALLING — FDA API Tool
# ============================================================

# 1. DEFINE TOOL FUNCTION ###################################

# This function queries the openFDA Device Recall API.
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

# 2. REGISTER TOOL ###################################

# The agent() wrapper in functions.py looks up tool functions by name.
# Inject our function so it can be found during tool dispatch.
import functions as _fn
_fn.get_fda_recalls = get_fda_recalls

# 3. TOOL METADATA ###################################

# Metadata tells the LLM what the tool does and what arguments it expects
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
                    "description": "Maximum number of results to return (e.g. 20 for a sample, 1000 for all)"
                }
            }
        }
    }
}

# ============================================================
# COMPONENT 2: RAG — FDA Recall Knowledge Search
# ============================================================

# 4. RAG SEARCH FUNCTION ###################################

# This function searches a local text file for lines matching a query.
# The knowledge base contains FDA domain context: recall classifications,
# root cause explanations, regulatory processes, and safety impact.

def search_fda_knowledge(query, document_path=RAG_KNOWLEDGE_PATH):
    """
    Search the FDA recall knowledge base for lines matching a query.

    Parameters:
    -----------
    query : str
        The search term to look for (case-insensitive)
    document_path : str
        Path to the knowledge base text file

    Returns:
    --------
    str
        Matching lines from the knowledge base as a single string
    """

    with open(document_path, 'r', encoding='utf-8') as f:
        text_content = f.readlines()

    matching_lines = [line.strip() for line in text_content
                      if query.lower() in line.lower() and line.strip()]

    if not matching_lines:
        return "No matching context found in knowledge base."

    return "\n".join(matching_lines)

# ============================================================
# COMPONENT 3: MULTI-AGENT ORCHESTRATION
# ============================================================

# 5. AGENT 1: DATA FETCHER (Function Calling) ###################################

# Agent 1 uses the get_fda_recalls tool to fetch live data from the FDA API
role1 = "I fetch device recall data from the openFDA Device Recall API."
task1 = "Get FDA device recall data for year 2024 with a limit of 20 records."

print("=" * 60)
print("📡 AGENT 1: Fetching FDA recall data via API tool...")
print("=" * 60)
result1 = agent_run(role=role1, task=task1, model=MODEL, tools=[tool_get_fda_recalls])

result1_text = df_as_text(result1)
print(f"   ✅ Retrieved {len(result1)} recall records.")
print(result1_text[:600])
print()

# 6. AGENT 2: CONTEXT RESEARCHER (RAG) ###################################

# Agent 2 uses RAG to search the local knowledge base for domain expertise
# about root causes, classification levels, and regulatory context.
print("=" * 60)
print("🔍 AGENT 2: Searching knowledge base for context (RAG)...")
print("=" * 60)

# Search for context on several relevant topics from the data
rag_context_causes = search_fda_knowledge("root cause")
rag_context_class = search_fda_knowledge("Class")
rag_context_safety = search_fda_knowledge("patient safety")

combined_rag_context = (
    "ROOT CAUSE CONTEXT:\n" + rag_context_causes + "\n\n"
    "CLASSIFICATION CONTEXT:\n" + rag_context_class + "\n\n"
    "SAFETY CONTEXT:\n" + rag_context_safety
)

print(f"   ✅ Retrieved context from knowledge base ({len(combined_rag_context)} chars)")

role2 = (
    "You are an FDA regulatory researcher. Given retrieved knowledge about FDA "
    "device recalls, synthesize a brief context summary that explains: "
    "1) what recall classifications mean, 2) common root cause categories, "
    "and 3) patient safety implications. Use bullet points. Keep under 150 words."
)
task2 = f"Synthesize the following retrieved FDA recall knowledge:\n\n{combined_rag_context}"

result2 = agent_run(role=role2, task=task2, model=MODEL, output="text")
print("📝 Context summary:")
print(result2)
print()

# 7. AGENT 3: EXECUTIVE REPORTER (Multi-Agent) ###################################

# Agent 3 combines the live API data from Agent 1 with the domain context
# from Agent 2 to produce a comprehensive executive report.
print("=" * 60)
print("📝 AGENT 3: Writing executive report...")
print("=" * 60)

role3 = (
    "You are an executive report writer for FDA device safety. "
    "Given both live recall data AND domain context, write a professional "
    "executive brief with these sections:\n"
    "1. **Overview**: 2-3 sentence summary of the recall landscape\n"
    "2. **Key Findings**: 3-4 bullet points from the data\n"
    "3. **Regulatory Context**: 2-3 bullets explaining significance using domain knowledge\n"
    "4. **Recommendations**: 2-3 actionable bullets for manufacturers or regulators\n"
    "Keep the total report under 300 words. Use formal, professional language."
)

task3 = (
    f"Write an executive report combining this live recall data and domain context.\n\n"
    f"LIVE FDA RECALL DATA (2024):\n{result1_text}\n\n"
    f"DOMAIN CONTEXT (from knowledge base):\n{result2}"
)

result3 = agent_run(role=role3, task=task3, model=MODEL, output="text")

# 8. FINAL OUTPUT ###################################

print("\n" + "=" * 60)
print("📊 FINAL RESULTS")
print("=" * 60)

print("\n--- Agent 1: Live FDA Recall Data (Top 10) ---")
print(result1.head(10).to_string(index=False))

print("\n--- Agent 2: Domain Context (RAG) ---")
print(result2)

print("\n--- Agent 3: Executive Report ---")
print(result3)

print("\n" + "=" * 60)
print("📊 System Summary")
print("=" * 60)
print(f"   📡 Function Calling: get_fda_recalls() → {len(result1)} records from openFDA")
print(f"   🔍 RAG: Searched fda_recall_knowledge.txt → {len(combined_rag_context)} chars of context")
print(f"   📝 Multi-Agent: 3 agents (Fetcher → Researcher → Reporter)")
print(f"   🤖 Model: {MODEL}")
print("✅ AI Agent System complete.")
