# 05_two_agent_chain.py
# Simple 2-Agent Workflow
# Multi-Agent Workflow Activity
# Tim Fraser

# This script demonstrates a 2-agent chain where agents work together in sequence.
# Agent 1 summarizes raw data; Agent 2 formats the summary into readable output.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

# Load helper function for agent orchestration
from functions import agent_run

# 1. CONFIGURATION ###################################

MODEL = "smollm2:360m"

# Sample raw data: monthly sales figures for a small business
# In a real workflow, this might come from a CSV, API, or database
raw_data = """
Month,Product A,Product B,Product C,Total
Jan,1200,800,950,2950
Feb,1350,720,1100,3170
Mar,1180,890,1050,3120
Apr,1420,810,980,3210
May,1280,950,1120,3350
Jun,1500,880,1080,3460
"""

# 2. WORKFLOW EXECUTION ###################################

# Agent 1: Takes raw data and produces a summary
# This agent analyzes the data and extracts key insights
role1 = "I analyze raw tabular data provided by the user. I produce a brief summary with key trends, highlights, and notable observations. Keep the summary to 3-5 sentences."
result1 = agent_run(role=role1, task=raw_data, model=MODEL, output="text")

# Agent 2: Takes the summary and produces formatted output
# This agent takes the analyst's summary and formats it for presentation
role2 = "I take summaries from the user and format them into clear, professional output. Use bullet points and section headers. Make it easy to read and present to stakeholders."
result2 = agent_run(role=role2, task=result1, model=MODEL, output="text")

# 3. VIEW RESULTS ###################################

print("=" * 60)
print("AGENT 1 OUTPUT (Summary):")
print("=" * 60)
print(result1)
print()

print("=" * 60)
print("AGENT 2 OUTPUT (Formatted):")
print("=" * 60)
print(result2)
