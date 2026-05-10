# homework3_generate_reports.py
# Homework 3 Step 1: Generate FDA Device Recall reports under three competing prompts
# Anjali Katta

# This script holds the FDA recall source data CONSTANT across all reports
# (so prompt is the only manipulated variable in the experiment) and generates
# 20 executive recall reports per prompt (3 prompts x 20 = 60 total reports)
# using OpenAI gpt-4o-mini at temperature=0.7. Reports are written to
# data/fda_reports.csv and the held-constant source data is saved to
# data/source_data.txt for the validator to share as ground truth.

# 0. Setup #################################

## 0.1 Load Packages ############################

import os
import time
import pandas as pd
import requests
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

## 0.2 Configuration ############################

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load OPENAI_API_KEY from a local .env (looked up in priority order)
for env_path in [HERE / ".env", HERE.parent / ".env", HERE.parent / "08_function_calling" / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        break
load_dotenv()

OPENAI_MODEL = "gpt-4o-mini"
N_PER_PROMPT = 20
TEMPERATURE = 0.7
RECALL_YEAR = 2024
RECALL_LIMIT = 12

client = OpenAI()

# 1. Pull held-constant FDA recall source data ##########

# Reuse the openFDA Device Recall API pattern from HW2.
# We pull a small fixed sample (RECALL_LIMIT records) ONCE and freeze it as
# the shared ground truth that every prompt and the validator will see.
def fetch_fda_recalls(year=RECALL_YEAR, limit=RECALL_LIMIT):
    url = "https://api.fda.gov/device/recall.json"
    params = {
        "search": f"event_date_initiated:[{year}-01-01 TO {year}-12-31]",
        "limit": min(limit, 1000),
    }
    api_key = os.getenv("API_KEY", "")
    if api_key:
        params["api_key"] = api_key
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for item in data.get("results", []):
        rows.append({
            "recall_number": item.get("recall_number", ""),
            "date": item.get("event_date_initiated", ""),
            "firm": item.get("recalling_firm", ""),
            "root_cause": item.get("root_cause_description", ""),
            "product_code": item.get("product_code", ""),
            "status": item.get("recall_status", ""),
        })
    return pd.DataFrame(rows)

def freeze_source_data(df, path):
    # Plain text block matching the LAB's "Source Data" pattern.
    # Plain text (not markdown) is more robust for downstream judging.
    lines = [f"FDA Device Recalls — Year {RECALL_YEAR} — sample of {len(df)} records"]
    lines.append("Source: openFDA Device Recall API")
    lines.append("")
    for _, row in df.iterrows():
        lines.append(
            f"- recall_number={row['recall_number']} | date={row['date']} | "
            f"firm={row['firm']} | product_code={row['product_code']} | "
            f"status={row['status']} | root_cause={row['root_cause']}"
        )
    text = "\n".join(lines)
    Path(path).write_text(text, encoding="utf-8")
    return text

# 2. Three competing prompts ###############

# Each prompt is a different system message for the report writer. The user
# message (the source data block) is identical across prompts.

PROMPT_A_REGULATORY = (
    "You are a senior FDA regulatory analyst writing for committee counsel. "
    "Use FORMAL government report language. Always classify recalls into Class I, II, "
    "or III where the data permits and explicitly invoke 21 CFR Part 7 framing. "
    "Cite the recall_number, firm, date, and product_code from the source whenever you "
    "make a claim about a specific recall. Address patient safety and clinical impact "
    "explicitly. Produce a four-section executive brief with these exact headings: "
    "Overview, Key Findings, Regulatory Context, Recommendations. "
    "Keep the report under 350 words. Do not invent any recall numbers, firms, dates, "
    "or product codes that are not in the source data."
)

PROMPT_B_EXECUTIVE = (
    "You are an executive briefing writer for a busy device manufacturer COO. "
    "Be terse and recommendation-forward. Lead with the action items the COO should "
    "take this week. Use plain business language, not legalese. "
    "Reference firms and recall numbers from the source where helpful, but prioritize "
    "decisions over citations. Keep the report under 250 words. "
    "Do not invent any recall numbers, firms, dates, or product codes that are not "
    "in the source data."
)

PROMPT_C_NARRATIVE = (
    "You are a narrative storyteller writing a feature piece about device safety for a "
    "general audience. Write in vivid, flowing prose with no headings or bullet points. "
    "Use evocative language to make the recalls feel real to readers. "
    "Mention specific firms or recalls from the source where they make the story land, "
    "but do not slow the prose down with citation-heavy structure. "
    "Keep the piece under 350 words. Do not invent any recall numbers, firms, dates, "
    "or product codes that are not in the source data."
)

PROMPTS = {
    "A": PROMPT_A_REGULATORY,
    "B": PROMPT_B_EXECUTIVE,
    "C": PROMPT_C_NARRATIVE,
}

# 3. Report generation function ###############

def generate_report(system_prompt, source_data_text):
    user_msg = (
        "Here is the FDA recall data for this period. Write the report described in "
        "your system instructions, using ONLY this data:\n\n"
        f"{source_data_text}"
    )
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    return response.choices[0].message.content.strip()

# 4. Run the experiment ###############

def main():
    print("=" * 60)
    print("📋 HW3 Step 1 — Generate FDA recall reports (3 prompts x "
          f"{N_PER_PROMPT} = {3 * N_PER_PROMPT} reports)")
    print("=" * 60)

    # Pull and freeze the FDA recall source data
    print(f"\n📡 Fetching FDA recall sample (year={RECALL_YEAR}, limit={RECALL_LIMIT})...")
    recalls_df = fetch_fda_recalls()
    print(f"   ✅ Got {len(recalls_df)} records")
    source_text = freeze_source_data(recalls_df, DATA_DIR / "source_data.txt")
    print(f"   💾 Saved {DATA_DIR / 'source_data.txt'} ({len(source_text)} chars)")

    # Generate reports
    rows = []
    for prompt_id, sys_prompt in PROMPTS.items():
        print(f"\n🤖 Prompt {prompt_id}: generating {N_PER_PROMPT} reports...")
        for i in range(1, N_PER_PROMPT + 1):
            try:
                text = generate_report(sys_prompt, source_text)
                rows.append({
                    "prompt_id": prompt_id,
                    "report_id": i,
                    "report_text": text,
                })
                print(f"   ✅ Prompt {prompt_id} report {i}/{N_PER_PROMPT} ({len(text)} chars)")
            except Exception as e:
                print(f"   ❌ Prompt {prompt_id} report {i}/{N_PER_PROMPT} failed: {e}")
            # Small pause to be polite to the API
            time.sleep(0.4)

    # Save reports
    out = pd.DataFrame(rows)
    out_path = DATA_DIR / "fda_reports.csv"
    out.to_csv(out_path, index=False)
    print("\n" + "=" * 60)
    print(f"✅ Wrote {len(out)} reports to {out_path}")
    print("=" * 60)
    print(out.groupby("prompt_id").size().to_string())

if __name__ == "__main__":
    main()
