# homework3_validator.py
# Homework 3 Step 2: Custom FDA-specific validation system (NOT the LAB Likert scales)
# Anjali Katta

# This is the validation system for HW3. It evaluates each generated FDA recall
# report on a domain-specific rubric tailored to regulatory device-recall briefs:
#   - 5 Likert dimensions (1-5): regulatory_grounding, data_specificity,
#     patient_safety_framing, actionability, structural_fidelity
#   - 1 hard boolean: hallucination_free (any fabricated firm/recall_number/date
#     fails the report regardless of its Likert scores)
#   - details: short justification string
# overall_score = mean of the 5 Likert dims; benchmark for PASS is
# overall_score >= 4.0 AND hallucination_free == True. This rubric goes well
# beyond the LAB's generic Likert scales (accuracy/formality/etc.) by adding
# domain meaning and a hard pass/fail criterion that matters for regulated text.

# 0. Setup #################################

## 0.1 Load Packages ############################

import os
import json
import re
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

## 0.2 Configuration ############################

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"

for env_path in [HERE / ".env", HERE.parent / ".env", HERE.parent / "08_function_calling" / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        break
load_dotenv()

OPENAI_MODEL = "gpt-4o-mini"
TEMPERATURE = 0.3  # lower temperature for more consistent judging (LAB pattern)
LIKERT_DIMS = [
    "regulatory_grounding",
    "data_specificity",
    "patient_safety_framing",
    "actionability",
    "structural_fidelity",
]
PASS_THRESHOLD = 4.0

client = OpenAI()

# 1. Build the rubric prompt #################################

SYSTEM_PROMPT = (
    "You are a quality control validator for AI-generated FDA Device Recall executive "
    "reports. You compare a candidate report to the source FDA recall data and score it "
    "on a domain-specific rubric. Always return ONLY a valid JSON object."
)

RUBRIC_INSTRUCTIONS = """
Evaluate the report below against the source FDA recall data. Return ONLY a JSON
object with these exact fields:

- regulatory_grounding (integer 1-5): correctness of FDA recall classification
  language (Class I/II/III), 21 CFR Part 7, and regulatory framing.
  1 = no regulatory framing or wrong classifications; 5 = appropriate regulatory
  framing throughout.
- data_specificity (integer 1-5): cites concrete recall numbers, dates, firm
  names, and/or product codes from the source data.
  1 = vague, no specifics; 5 = multiple specific source citations.
- patient_safety_framing (integer 1-5): explicitly addresses patient/clinical
  impact, not just business impact.
  1 = no patient framing; 5 = clear patient-centered framing throughout.
- actionability (integer 1-5): recommendations are concrete, distinct, and
  implementable; not generic platitudes.
  1 = vague platitudes; 5 = several distinct, actionable recommendations.
- structural_fidelity (integer 1-5): follows a four-section executive brief
  structure (Overview / Findings / Context / Recommendations) with clear headings.
  1 = unstructured prose; 5 = all four sections present with clear headings.
- hallucination_free (boolean): true if EVERY firm name, recall_number, date,
  and product_code mentioned in the report appears in the source data; false if
  any fabricated specifics appear. Generic FDA framing (Class I/II/III, 21 CFR)
  is allowed even if not in the source.
- details (string): 0-50 word justification of your scores.

Return ONLY the JSON object, with all 7 fields, and no other text.
"""

def build_user_message(report_text, source_text):
    return (
        f"SOURCE FDA RECALL DATA (ground truth):\n{source_text}\n\n"
        f"REPORT TO VALIDATE:\n{report_text}\n"
        f"{RUBRIC_INSTRUCTIONS}"
    )

# 2. Query the validator #################################

def query_validator(report_text, source_text, max_retries=2):
    user_msg = build_user_message(report_text, source_text)
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=TEMPERATURE,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            last_err = e
            print(f"   ⚠️  Validator attempt {attempt} failed: {e}")
            time.sleep(1.0)
    raise RuntimeError(f"Validator failed after {max_retries} retries: {last_err}")

# 3. Parse JSON safely #################################

def parse_validator_json(raw):
    # The model returns JSON when response_format=json_object, but be defensive.
    text = raw.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    obj = json.loads(text)

    parsed = {}
    for dim in LIKERT_DIMS:
        v = obj.get(dim)
        try:
            parsed[dim] = int(round(float(v))) if v is not None else None
        except (TypeError, ValueError):
            parsed[dim] = None
    hf = obj.get("hallucination_free")
    if isinstance(hf, str):
        hf = hf.strip().lower() in ("true", "yes", "1", "t")
    parsed["hallucination_free"] = bool(hf) if hf is not None else None
    parsed["details"] = str(obj.get("details", ""))
    return parsed

# 4. Main loop #################################

def main():
    print("=" * 60)
    print("📋 HW3 Step 2 — Validate reports with FDA-specific rubric")
    print("=" * 60)

    reports_path = DATA_DIR / "fda_reports.csv"
    source_path = DATA_DIR / "source_data.txt"
    if not reports_path.exists():
        raise FileNotFoundError(
            f"{reports_path} not found. Run homework3_generate_reports.py first."
        )
    if not source_path.exists():
        raise FileNotFoundError(
            f"{source_path} not found. Run homework3_generate_reports.py first."
        )

    reports = pd.read_csv(reports_path)
    source_text = source_path.read_text(encoding="utf-8")
    print(f"📂 Loaded {len(reports)} reports from {reports_path}")
    print(f"📂 Loaded source ground truth ({len(source_text)} chars) from {source_path}")

    rows = []
    raw_dump = []
    for idx, row in reports.iterrows():
        prompt_id = row["prompt_id"]
        report_id = int(row["report_id"])
        report_text = row["report_text"]
        print(f"\n🔍 Validating prompt={prompt_id} report={report_id} "
              f"({idx + 1}/{len(reports)})...")
        try:
            raw = query_validator(report_text, source_text)
            parsed = parse_validator_json(raw)
        except Exception as e:
            print(f"   ❌ Could not validate: {e}")
            continue

        likerts = [parsed[d] for d in LIKERT_DIMS if parsed[d] is not None]
        overall = round(sum(likerts) / len(likerts), 3) if likerts else None
        passed = (
            overall is not None
            and overall >= PASS_THRESHOLD
            and parsed["hallucination_free"] is True
        )

        rows.append({
            "prompt_id": prompt_id,
            "report_id": report_id,
            **{d: parsed[d] for d in LIKERT_DIMS},
            "hallucination_free": parsed["hallucination_free"],
            "overall_score": overall,
            "passed": passed,
            "details": parsed["details"],
        })
        raw_dump.append({
            "prompt_id": prompt_id,
            "report_id": report_id,
            "raw_json": raw,
        })
        print(f"   ✅ Likert avg={overall}  hallucination_free="
              f"{parsed['hallucination_free']}  passed={passed}")
        time.sleep(0.3)

    out = pd.DataFrame(rows)
    out_path = DATA_DIR / "validation_scores.csv"
    out.to_csv(out_path, index=False)

    raw_path = DATA_DIR / "validation_raw.jsonl"
    with raw_path.open("w", encoding="utf-8") as f:
        for r in raw_dump:
            f.write(json.dumps(r) + "\n")

    print("\n" + "=" * 60)
    print(f"✅ Wrote validation scores: {out_path}")
    print(f"✅ Wrote raw audit trail: {raw_path}")
    print("=" * 60)

    # Quick sanity summary
    print("\nMean overall_score by prompt:")
    print(out.groupby("prompt_id")["overall_score"].agg(["mean", "std", "count"]).round(3))
    print("\nPass-rate (overall >= 4.0 AND hallucination_free) by prompt:")
    print(out.groupby("prompt_id")["passed"].mean().round(3))

if __name__ == "__main__":
    main()
