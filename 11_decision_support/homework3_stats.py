# homework3_stats.py
# Homework 3 Step 3: Statistical comparison of three prompts on validation scores
# Anjali Katta

# This script runs the experiment's statistical analysis on data/validation_scores.csv:
#   1. Bartlett's test for homogeneity of variance on overall_score by prompt_id
#   2. One-way ANOVA (or Welch's ANOVA when Bartlett is significant) on overall_score
#   3. Tukey HSD post-hoc to identify which prompt PAIRS differ
#   4. Per-dimension ANOVAs to show WHERE the prompts diverge
#   5. OLS linear regression with prompt as a factor for the writeup
# Outputs:
#   - figures/boxplot_overall.png  (overall_score by prompt)
#   - figures/dimensions_bar.png   (mean Likert score per dimension by prompt)
#   - data/stats_summary.json      (machine-readable headline numbers)
#   - data/stats_report.txt        (human-readable run log)

# 0. Setup #################################

## 0.1 Load Packages ############################

import os
import json
import io
import textwrap
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import numpy as np
from scipy.stats import bartlett, f_oneway
import statsmodels.formula.api as smf
import statsmodels.api as sm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.oneway import anova_oneway

# Use a non-interactive backend so this works in headless terminals
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

## 0.2 Paths and config ############################

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
FIG_DIR = HERE / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

LIKERT_DIMS = [
    "regulatory_grounding",
    "data_specificity",
    "patient_safety_framing",
    "actionability",
    "structural_fidelity",
]

# 1. Load validation scores #################################

def load_scores():
    path = DATA_DIR / "validation_scores.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run homework3_validator.py first."
        )
    scores = pd.read_csv(path)
    # Drop rows where overall_score is missing (validator failures)
    scores = scores.dropna(subset=["overall_score"])
    return scores

# 2. Headline statistical analysis ###########################

def run_overall_analysis(scores):
    out = {}

    # Per-prompt descriptive stats
    desc = (
        scores.groupby("prompt_id")["overall_score"]
        .agg(["mean", "std", "count"])
        .round(3)
    )
    print("📈 Descriptive stats — overall_score by prompt_id")
    print(desc)
    print()
    out["descriptive_stats"] = desc.reset_index().to_dict(orient="records")

    # Pull a vector per prompt for parametric tests
    groups = {p: scores.loc[scores["prompt_id"] == p, "overall_score"].values
              for p in sorted(scores["prompt_id"].unique())}

    # Bartlett's test
    b_stat, b_p = bartlett(*groups.values())
    var_equal = b_p >= 0.05
    print(f"🔍 Bartlett's test for equal variances: stat={b_stat:.4f}, p={b_p:.4f}")
    print(f"   {'✅ Equal variances assumed' if var_equal else '❌ Unequal variances — using Welch ANOVA'}")
    print()
    out["bartlett"] = {"statistic": float(b_stat), "p_value": float(b_p),
                       "equal_variance": bool(var_equal)}

    # ANOVA (standard or Welch)
    if var_equal:
        f_stat, p_val = f_oneway(*groups.values())
        anova_kind = "one-way ANOVA (equal variance)"
        df1 = len(groups) - 1
        df2 = sum(len(v) for v in groups.values()) - len(groups)
    else:
        wa = anova_oneway(scores["overall_score"], scores["prompt_id"], use_var="unequal")
        f_stat = float(wa.statistic)
        p_val = float(wa.pvalue)
        df1 = float(wa.df_num)
        df2 = float(wa.df_denom)
        anova_kind = "Welch's ANOVA (unequal variance)"

    print(f"📊 {anova_kind}: F({df1:.2f}, {df2:.2f})={f_stat:.4f}, p={p_val:.4g}")
    if p_val < 0.05:
        print("   ✅ At least one prompt differs significantly.")
    else:
        print("   ❌ No significant difference between prompts.")
    print()
    out["anova"] = {
        "kind": anova_kind,
        "F": float(f_stat),
        "df1": float(df1),
        "df2": float(df2),
        "p_value": float(p_val),
    }

    # Tukey HSD
    tukey = pairwise_tukeyhsd(scores["overall_score"], scores["prompt_id"], alpha=0.05)
    print("📋 Tukey HSD post-hoc:")
    print(tukey.summary())
    print()
    tukey_rows = []
    for row in tukey.summary().data[1:]:
        tukey_rows.append({
            "group1": row[0],
            "group2": row[1],
            "meandiff": float(row[2]),
            "p_adj": float(row[3]),
            "lower": float(row[4]),
            "upper": float(row[5]),
            "reject": bool(row[6]),
        })
    out["tukey"] = tukey_rows

    return out

# 3. Per-dimension ANOVAs ###################################

def run_per_dimension(scores):
    out = {}
    print("📊 Per-dimension Welch ANOVAs:")
    for dim in LIKERT_DIMS:
        if dim not in scores.columns:
            continue
        sub = scores.dropna(subset=[dim])
        if sub[dim].nunique() < 2:
            continue
        groups = [sub.loc[sub["prompt_id"] == p, dim].values
                  for p in sorted(sub["prompt_id"].unique())]
        # Skip if any group is empty or constant -- Welch needs variance
        if any(len(g) == 0 for g in groups):
            continue
        # Try Welch first; fall back to standard ANOVA if Welch is undefined
        # (e.g. one group has zero variance, which is common when scorers give
        # the same Likert value to every report in a group).
        F, p, kind = None, None, None
        try:
            wa = anova_oneway(sub[dim], sub["prompt_id"], use_var="unequal")
            F = float(wa.statistic)
            p = float(wa.pvalue)
            kind = "Welch"
        except Exception:
            pass
        if F is None or np.isnan(F) or np.isnan(p):
            try:
                F, p = f_oneway(*groups)
                F, p = float(F), float(p)
                kind = "Standard"
            except Exception as e:
                print(f"   ⚠️  Could not run ANOVA on {dim}: {e}")
                continue
        means = sub.groupby("prompt_id")[dim].mean().round(3).to_dict()
        print(f"   {dim:>22s}: F={F:.3f}, p={p:.4g}, means={means} [{kind} ANOVA]")
        out[dim] = {"F": F, "p_value": p, "kind": kind, "means": means}
    print()
    return out

# 4. OLS regression ###################################

def run_regression(scores):
    # Treat prompt_id as a categorical predictor; A is reference category.
    model = smf.ols("overall_score ~ C(prompt_id)", data=scores).fit()
    print("📐 OLS regression: overall_score ~ C(prompt_id)")
    print(model.summary())
    print()

    # Pass-rate (overall >= 4.0 AND hallucination_free) per prompt
    if "passed" in scores.columns:
        pass_rate = scores.groupby("prompt_id")["passed"].mean().round(3)
        print("✅ Pass-rate (overall >= 4.0 AND hallucination_free):")
        print(pass_rate)
        print()
        return {
            "params": model.params.to_dict(),
            "pvalues": model.pvalues.to_dict(),
            "rsquared": float(model.rsquared),
            "pass_rate": pass_rate.to_dict(),
        }
    return {
        "params": model.params.to_dict(),
        "pvalues": model.pvalues.to_dict(),
        "rsquared": float(model.rsquared),
    }

# 5. Figures ###################################

def make_boxplot(scores, path):
    fig, ax = plt.subplots(figsize=(7, 5))
    prompts = sorted(scores["prompt_id"].unique())
    data = [scores.loc[scores["prompt_id"] == p, "overall_score"].values
            for p in prompts]
    ax.boxplot(data, labels=[f"Prompt {p}" for p in prompts], showmeans=True)
    ax.set_title("Overall validation score by prompt (HW3)")
    ax.set_ylabel("Mean Likert score (1–5)")
    ax.set_xlabel("Prompt")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(f"💾 Saved {path}")

def make_rubric_figure(path):
    # A clean visual of the FDA-specific rubric so HW3's deliverables include
    # a screenshot-ready rubric figure (the spec asks for a rubric visual).
    rows = [
        ["regulatory_grounding", "1–5",
         "Correct FDA classification\nlanguage (Class I/II/III),\n21 CFR Part 7 framing",
         "Mean ≥ 4 to pass"],
        ["data_specificity", "1–5",
         "Cites concrete recall #s,\ndates, firms, product codes\nfrom the source",
         "Mean ≥ 4 to pass"],
        ["patient_safety_framing", "1–5",
         "Explicitly addresses\npatient/clinical impact",
         "Mean ≥ 4 to pass"],
        ["actionability", "1–5",
         "Concrete, distinct,\nimplementable recommendations\n(no platitudes)",
         "Mean ≥ 4 to pass"],
        ["structural_fidelity", "1–5",
         "Four-section exec brief:\nOverview / Findings /\nContext / Recommendations",
         "Mean ≥ 4 to pass"],
        ["hallucination_free", "Boolean",
         "Every firm, recall #, date,\nproduct code in source data\n(no fabrications)",
         "MUST be true (HARD FAIL)"],
        ["details", "string",
         "0–50 word justification\nof the scores above",
         "Audit / explanation only"],
    ]
    headers = ["Dimension", "Scale", "What it measures", "Benchmark"]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc="left",
        colLoc="center",
        loc="center",
        colWidths=[0.22, 0.10, 0.42, 0.26],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1.0, 2.4)
    # Bold header row
    for col in range(len(headers)):
        cell = table[(0, col)]
        cell.set_text_props(weight="bold", color="white")
        cell.set_facecolor("#1E40AF")
    # Highlight the boolean hard-fail row
    for col in range(len(headers)):
        cell = table[(6, col)]
        cell.set_facecolor("#FEF3C7")
    ax.set_title(
        "HW3 Validation Rubric — FDA Device Recall Reports\n"
        "(domain-specific; replaces LAB Likert scales)",
        fontsize=12, weight="bold", pad=14,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"💾 Saved {path}")

def make_dimensions_bar(scores, path):
    prompts = sorted(scores["prompt_id"].unique())
    means = (
        scores.groupby("prompt_id")[LIKERT_DIMS]
        .mean()
        .reindex(prompts)
    )
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(LIKERT_DIMS))
    width = 0.25
    for i, p in enumerate(prompts):
        ax.bar(x + (i - 1) * width, means.loc[p].values, width=width, label=f"Prompt {p}")
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace("_", "\n") for d in LIKERT_DIMS])
    ax.set_ylabel("Mean Likert score (1–5)")
    ax.set_ylim(0, 5)
    ax.set_title("Mean rubric scores by dimension and prompt (HW3)")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(f"💾 Saved {path}")

# 6. Main ###################################

def main():
    print("=" * 60)
    print("📋 HW3 Step 3 — Statistical comparison of prompts A/B/C")
    print("=" * 60 + "\n")

    scores = load_scores()
    print(f"📂 Loaded {len(scores)} validated reports")
    print(scores.groupby("prompt_id").size().to_string())
    print()

    # Capture all stats output to a file too
    buf = io.StringIO()

    class Tee:
        def __init__(self, *streams): self.streams = streams
        def write(self, s):
            for st in self.streams: st.write(s)
        def flush(self):
            for st in self.streams: st.flush()

    import sys as _sys
    real_stdout = _sys.stdout
    _sys.stdout = Tee(real_stdout, buf)
    try:
        out = {}
        out["overall"] = run_overall_analysis(scores)
        out["per_dimension"] = run_per_dimension(scores)
        out["regression"] = run_regression(scores)
    finally:
        _sys.stdout = real_stdout

    (DATA_DIR / "stats_report.txt").write_text(buf.getvalue(), encoding="utf-8")
    (DATA_DIR / "stats_summary.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )

    make_boxplot(scores, FIG_DIR / "boxplot_overall.png")
    make_dimensions_bar(scores, FIG_DIR / "dimensions_bar.png")
    make_rubric_figure(FIG_DIR / "rubric_table.png")

    print("\n" + "=" * 60)
    print(f"✅ Wrote {DATA_DIR / 'stats_report.txt'}")
    print(f"✅ Wrote {DATA_DIR / 'stats_summary.json'}")
    print(f"✅ Wrote {FIG_DIR / 'boxplot_overall.png'}")
    print(f"✅ Wrote {FIG_DIR / 'dimensions_bar.png'}")
    print(f"✅ Wrote {FIG_DIR / 'rubric_table.png'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
