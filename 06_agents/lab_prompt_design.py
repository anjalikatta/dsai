# lab_prompt_design.py
# Multi-Agent Prompt Design Lab
# Pairs with LAB_prompt_design.md
# Tim Fraser

# This script implements a 3-agent pipeline for analyzing FDA drug shortage data.
# Workflow: Data Analyst → Risk Assessor → Public Health Advisory Writer
# Each agent has a carefully designed system prompt with clear role, format, and constraints.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import pandas as pd  # for data manipulation
import yaml          # for reading YAML rules

## 0.2 Load Functions #################################

# Load helper functions for agent orchestration
from functions import agent_run, get_shortages, df_as_text

# 1. CONFIGURATION ###################################

# Using a small, fast model for quick iteration
MODEL = "gemma3:latest"

# 2. SYSTEM PROMPTS ###################################

# Each agent has a specific role, expected input/output format, and constraints.
# These prompts were refined through iteration (see design notes at bottom of script).

## 2.1 Agent 1: Data Analyst ############################

# Role: Receives raw shortage data as a markdown table, identifies trends and key findings.
# Output: A structured bullet-point analysis with clear categories.
ROLE_ANALYST = """You are a pharmaceutical data analyst.
You receive a markdown table of FDA drug shortage records.

Your task:
- Identify the total number of unique drugs listed.
- Note which drugs are currently unavailable vs. available.
- Highlight any patterns in update types or dates.

Output format:
- Use a numbered list of key findings (3-5 findings).
- Keep each finding to 1-2 sentences.
- End with a one-sentence overall assessment.

Constraints:
- Only reference data present in the table. Do not speculate.
- Be precise with drug names and counts.
"""

## 2.2 Agent 2: Risk Assessor ############################

# Role: Receives the analyst's findings, assigns risk levels, and prioritizes concerns.
# Output: A risk assessment with HIGH/MEDIUM/LOW ratings.
ROLE_RISK = """You are a public health risk assessor.
You receive a data analysis summary of drug shortages from a colleague.

Your task:
- Assign a risk level (HIGH, MEDIUM, or LOW) to each finding based on patient impact.
- Rank findings from most to least concerning.
- Provide a brief justification for each risk level.

Output format:
- Use a markdown table with columns: Finding, Risk Level, Justification.
- After the table, write a 1-2 sentence overall risk summary.

Constraints:
- HIGH risk = drugs with no alternatives or widespread patient impact.
- MEDIUM risk = drugs with limited alternatives or moderate impact.
- LOW risk = drugs with readily available alternatives or minimal impact.
- Base your assessment only on the information provided.
"""

## 2.3 Agent 3: Advisory Writer ############################

# Role: Receives the risk assessment, writes a public-facing health advisory.
# Output: A short, accessible advisory document.
ROLE_ADVISORY = """You are a public health communications specialist.
You receive a risk assessment of drug shortages from a colleague.

Your task:
- Write a short public health advisory (200-300 words) for healthcare providers and patients.
- Summarize the key shortage concerns in plain language.
- Include actionable recommendations.

Output format:
- Title: "Public Health Advisory: Drug Shortage Update"
- Sections: Summary, Key Concerns, Recommendations, Contact Information.
- Use bullet points for recommendations.

Constraints:
- Use plain, accessible language (no jargon).
- Focus on HIGH and MEDIUM risk items.
- Include a note that information comes from FDA data.
- Do not provide medical advice; direct patients to consult their healthcare provider.
"""

# 3. WORKFLOW EXECUTION ###################################

# Fetch drug shortage data from the FDA API
print("=" * 60)
print("STEP 1: Fetching drug shortage data from FDA API...")
print("=" * 60)

data = get_shortages(category="Psychiatry", limit=50)
print(f"Retrieved {len(data)} records.\n")

# Process: keep only the most recent update per drug, filter for unavailable
stat = (data
        .groupby("generic_name")
        .apply(lambda x: x.loc[x["update_date"].idxmax()])
        .reset_index(drop=True))

# Convert to markdown table for the analyst agent
data_text = df_as_text(stat)

## 3.1 Agent 1: Data Analyst ############################

print("=" * 60)
print("STEP 2: Running Data Analyst Agent...")
print("=" * 60)

result_analyst = agent_run(role=ROLE_ANALYST, task=data_text, model=MODEL, output="text")

print(result_analyst)
print()

## 3.2 Agent 2: Risk Assessor ############################

print("=" * 60)
print("STEP 3: Running Risk Assessor Agent...")
print("=" * 60)

result_risk = agent_run(role=ROLE_RISK, task=result_analyst, model=MODEL, output="text")

print(result_risk)
print()

## 3.3 Agent 3: Advisory Writer ############################

print("=" * 60)
print("STEP 4: Running Advisory Writer Agent...")
print("=" * 60)

result_advisory = agent_run(role=ROLE_ADVISORY, task=result_risk, model=MODEL, output="text")

print(result_advisory)
print()

# 4. FINAL OUTPUT ###################################

print("=" * 60)
print("COMPLETE PIPELINE OUTPUT")
print("=" * 60)

print("\n--- Agent 1: Data Analysis ---")
print(result_analyst)

print("\n--- Agent 2: Risk Assessment ---")
print(result_risk)

print("\n--- Agent 3: Public Health Advisory ---")
print(result_advisory)

# 5. PROMPT DESIGN NOTES ###################################

# Iteration 1: Started with vague prompts like "Analyze this data" and "Write an advisory."
#   Problem: Outputs were unfocused and inconsistent in format.
#
# Iteration 2: Added explicit output format requirements (numbered list, markdown table, sections).
#   Improvement: Agents now produce structured, predictable output.
#   Problem: Risk assessor was speculating beyond the data.
#
# Iteration 3 (final): Added constraints to each prompt limiting agents to provided information.
#   Added risk level definitions (HIGH/MEDIUM/LOW) so the risk assessor uses consistent criteria.
#   Added word count target for the advisory writer to prevent overly long output.
#   Result: Reliable, well-structured pipeline with consistent formatting across runs.
#
# Key design choices:
#   - Each prompt has three sections: task, output format, and constraints.
#   - Output format of Agent 1 (bullet list) feeds naturally into Agent 2's input.
#   - Agent 2's markdown table output gives Agent 3 structured data to reference.
#   - Constraints prevent hallucination and keep agents grounded in the actual data.
