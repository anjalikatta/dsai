# 04_agent_query.py
# Agent with REST Tool Call
# Pairs with 04_agent_query.R
# Tim Fraser

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "08_function_calling"))

from dotenv import load_dotenv
from functions import agent

import json
import requests

# 1. CONFIG ###################################

load_dotenv(ROOT_DIR / "12_end" / ".env")

# Paste your live URL in 12_end/.env as API_PUBLIC_URL=... or override here.
ENDPOINT_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000").rstrip("/")
MODEL = os.getenv("OLLAMA_MODEL", "smollm2:1.7b")

UNIT_NOTE = "vehicles observed in one representative minute (1m/t1 interval) within the requested hour and day of week"

# 2. DEFINE TOOL FUNCTION ###################################

def predict_vehicle_count(day_of_week, hours_of_day):
    hours = [int(h) for h in hours_of_day if 0 <= int(h) <= 23]
    if not hours:
        raise ValueError("hours_of_day must contain at least one integer between 0 and 23.")

    predictions = []
    for hour in hours:
        resp = requests.get(
            f"{ENDPOINT_URL}/predict",
            params={"day_of_week": int(day_of_week), "hour_of_day": hour},
            timeout=10,
        )
        resp.raise_for_status()
        predictions.append(
            {
                "hour_of_day": hour,
                "predicted_vehicle_count": float(resp.json()["predicted_vehicle_count"]),
            }
        )

    return {
        "day_of_week": int(day_of_week),
        "unit": "vehicles_observed_in_one_minute",
        "interval": "1m_t1",
        "note": "Each prediction is for one representative minute within that hour and day of week.",
        "predictions": predictions,
    }

# 3. DEFINE TOOL METADATA ###################################

tool_predict_vehicle_count = {
    "type": "function",
    "function": {
        "name": "predict_vehicle_count",
        "description": (
            "Predict Brussels vehicle count for a specific day of week and vector of hours. "
            "Returns one estimated vehicle count per requested hour. "
            "Each value is for one representative minute (1m/t1 interval) within that hour on that day of week."
        ),
        "parameters": {
            "type": "object",
            "required": ["day_of_week", "hours_of_day"],
            "properties": {
                "day_of_week": {"type": "integer", "description": "Day of week (1=Monday, ..., 7=Sunday)"},
                "hours_of_day": {
                    "type": "array",
                    "description": "Vector of hours to predict (0-23), e.g. [0,1,2,...,23].",
                    "items": {"type": "integer"},
                },
            }
        }
    }
}

# 4. RUN AGENT ###################################

tools = [tool_predict_vehicle_count]
system_prompt = (
    "You are a Brussels traffic assistant. "
    "Always report units clearly as vehicles observed in one representative minute "
    "(1m/t1 interval) within the requested hour and day of week. "
    "Map phrases to integers: Monday=1, Tuesday=2, ..., Sunday=7; "
    "8 AM→8, noon→12, 6 PM→18, midnight→0. "
    "Call predict_vehicle_count with day_of_week and hours_of_day (hours as a list)."
)


def run_turn(user_text: str):
    return agent(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        model=MODEL,
        output="text",
        tools=tools,
    )


# Stage 2: Natural-language ask + explicit clock hint so small local models hit the right tool args
result1 = run_turn(
    "Predict Brussels vehicle count for Monday at 8 AM. "
    "Call the tool once with hours_of_day set to [8] only."
)
print("Agent result:", result1)
direct1 = predict_vehicle_count(day_of_week=1, hours_of_day=[8])
print("Direct API call:", json.dumps(direct1, indent=2))
print("Unit:", UNIT_NOTE)
p1 = direct1["predictions"][0]["predicted_vehicle_count"]
print("Match:", str(p1) in str(result1))

# Second prompt: different day/hour mapping
result2 = run_turn(
    "Predict Brussels vehicle count for Friday at 6 PM. "
    "Call the tool once with hours_of_day set to [18] only."
)
print("Agent result:", result2)
direct2 = predict_vehicle_count(day_of_week=5, hours_of_day=[18])
print("Direct API call:", json.dumps(direct2, indent=2))
p2 = direct2["predictions"][0]["predicted_vehicle_count"]
print("Match:", str(p2) in str(result2))
