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
import time
from pathlib import Path

import pandas as pd


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


if __name__ == "__main__":
    main()
