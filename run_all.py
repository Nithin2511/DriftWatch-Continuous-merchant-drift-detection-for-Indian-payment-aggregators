#!/usr/bin/env python3
"""
DriftWatch — full pipeline, one command.

    python run_all.py [--skip-generate] [--max-fp 0.10]

Set GEMINI_API_KEY to use Gemini for descriptor classification and case narratives.
Without it the pipeline still runs end to end using labelled deterministic fallbacks.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd


# Fields whose values are quoted in README.md / docs/EVALUATION.md and asserted by
# tests/test_docs_consistency.py. If any of these move, the committed artifact and the
# documentation both have to move with them.
_REPORTED_FIELDS = [
    ("thresholds",), ("variant",), ("fp_budget",),
    ("development", "caught"), ("development", "n_drifters"), ("development", "catch_rate"),
    ("development", "median_lead_days"), ("development", "n_false_positives"),
    ("development", "n_non_drifters"), ("development", "false_positive_rate"),
    ("held_out", "caught"), ("held_out", "n_drifters"), ("held_out", "catch_rate"),
    ("held_out", "median_lead_days"), ("held_out", "p25_lead_days"),
    ("held_out", "p75_lead_days"), ("held_out", "min_lead_days"),
    ("held_out", "max_lead_days"), ("held_out", "n_false_positives"),
    ("held_out", "n_non_drifters"), ("held_out", "false_positive_rate"),
    ("held_out", "n_fp_confounders"), ("held_out", "n_actionable"),
    ("held_out", "actionable_rate_of_drifters"), ("held_out_by_type",),
]


def _dig(d, path):
    for key in path:
        if not isinstance(d, dict) or key not in d:
            return "<missing>"
        d = d[key]
    return d


def check_artifact_is_committed(outdir: Path) -> bool:
    """Compare the freshly written evaluation.json against the copy in git.

    out/evaluation.json is the ONLY generated file under version control. It is committed
    so CI can run tests/test_docs_consistency.py against it; without it those tests skip
    and the docs-vs-numbers guard enforces nothing on pull requests.

    That creates the failure mode this function closes: re-run the pipeline, update the
    docs, forget to re-commit the artifact -- and CI then validates the documentation
    against a stale file and passes.

    Returns True when this run agrees with what is committed.
    """
    fresh_path = outdir / "evaluation.json"
    if not fresh_path.exists():
        return True
    try:
        shown = subprocess.run(["git", "show", f"HEAD:{outdir.name}/evaluation.json"],
                               capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return True                     # no git here; nothing to compare against
    if shown.returncode != 0:
        return True                     # not committed on this branch yet
    try:
        committed = json.loads(shown.stdout)
    except json.JSONDecodeError:
        return True
    fresh = json.loads(fresh_path.read_text(encoding="utf-8"))

    drifted = [(".".join(path), _dig(committed, path), _dig(fresh, path))
               for path in _REPORTED_FIELDS
               if _dig(committed, path) != _dig(fresh, path)]
    if not drifted:
        return True

    bar = "=" * 78
    print("\n" + bar)
    print("ARTIFACT DRIFT: out/evaluation.json differs from the committed copy")
    print(bar)
    for field, was, now in drifted:
        print(f"  {field}")
        print(f"      committed: {was}")
        print(f"      this run : {now}")
    print()
    print(f"{len(drifted)} reported field(s) changed. out/evaluation.json is committed so CI")
    print("can check the documentation against it. A stale copy means CI validates the docs")
    print("against numbers the pipeline no longer produces -- and passes.")
    print()
    print("Do all three, or none:")
    print("  1. update README.md and docs/EVALUATION.md to the new numbers")
    print("  2. git add out/evaluation.json")
    print("  3. python -m pytest tests -q")
    print(bar)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--max-fp", type=float, default=0.10,
                    help="FP-rate budget the calibration must respect on the dev split")
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default=None,
                    help="output dir (default: out, or out-ablation when --ablate-content)")
    ap.add_argument("--ablate-content", action="store_true",
                    help="drop the content family (category_mismatch) and recalibrate "
                         "from scratch. Answers 'what does this buy when the PA has no "
                         "usable descriptor text?' -- see docs/EVALUATION.md.")
    a = ap.parse_args()
    data = Path(a.data)
    out = Path(a.out) if a.out else Path("out-ablation" if a.ablate_content else "out")
    t0 = time.time()

    # 1 -- synthetic data
    if not a.skip_generate or not (data / "transactions.parquet").exists():
        from driftwatch.generate import generate
        print("[1/5] generating synthetic portfolio ...")
        meta = generate(outdir=data)
        print(f"      {meta['n_merchants']} merchants, {meta['n_transactions']:,} txns, "
              f"{meta['n_drifters']} drifters, {meta['n_confounders']} confounders")
    else:
        meta = json.loads((data / "meta.json").read_text())
        print("[1/5] reusing existing synthetic portfolio")

    txn = pd.read_parquet(data / "transactions.parquet")
    merchants = pd.read_csv(data / "merchants.csv")

    # 2 -- descriptor classification (Gemini, O(vocabulary))
    from driftwatch.llm import classify_descriptors
    descs = txn.descriptor.unique().tolist()
    print(f"[2/5] classifying {len(descs)} unique descriptors ...")
    mapping, mode = classify_descriptors(descs)
    print(f"      classifier mode: {mode}")

    # 3 -- signals
    from driftwatch.signals import SignalEngine
    print("[3/5] computing walk-forward signals ...")
    sig = SignalEngine(txn, merchants, mapping).compute(horizon=meta["horizon_days"])
    sig.to_parquet(data / "signals.parquet", index=False)
    print(f"      {len(sig):,} merchant-days scored")

    # 4 -- calibrate on dev, score held-out once
    from driftwatch.evaluate import main as evaluate
    variant = "NO-CONTENT ABLATION" if a.ablate_content else "full signal set"
    print(f"[4/5] calibrating on dev split ({variant}), scoring held-out once ...")
    res = evaluate(datadir=str(data), outdir=str(out), max_fp_rate=a.max_fp,
                   ablate_content=a.ablate_content)
    h = res["held_out"]
    cc, cf = h["catch_rate_ci"], h["false_positive_rate_ci"]
    print(f"      HELD-OUT: median lead {h['median_lead_days']:g}d | "
          f"catch {h['catch_rate']:.1%} [{cc[0]}-{cc[1]}%] | "
          f"FP {h['false_positive_rate']:.1%} [{cf[0]}-{cf[1]}%]")

    # 5 -- case files
    from driftwatch.casefile import write_cases
    hits = pd.read_json(out / "held_out_triggers.json")
    print(f"[5/5] synthesising {len(hits)} case files ...")
    from driftwatch.llm import MODEL as LLM_MODEL
    prov = dict(descriptor_classifier_mode=mode, llm_model=LLM_MODEL,
                variant=res["variant"], signals_used=res["signals_used"],
                calibration="development split (60%); held-out untouched until final scoring",
                data="synthetic", generator_seed=meta["seed"])
    write_cases(hits, merchants, txn, res["thresholds"], prov, out / "cases")

    print(f"\ndone in {time.time()-t0:.0f}s. run `python -m driftwatch.demo` for the demo view.")

    # The ablation writes to its own directory and is not the artifact CI validates
    # against, so it is exempt.
    if not a.ablate_content and not check_artifact_is_committed(out):
        sys.exit(1)


if __name__ == "__main__":
    main()
