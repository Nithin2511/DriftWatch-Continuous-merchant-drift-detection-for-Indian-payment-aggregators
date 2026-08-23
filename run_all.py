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
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    data, out = Path(a.data), Path(a.out)
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
    print("[4/5] calibrating on dev split, scoring held-out once ...")
    res = evaluate(datadir=str(data), outdir=str(out), max_fp_rate=a.max_fp)
    h = res["held_out"]
    print(f"      HELD-OUT: median lead {h['median_lead_days']:.0f}d | "
          f"catch {h['catch_rate']:.1%} | FP {h['false_positive_rate']:.1%}")

    # 5 -- case files
    from driftwatch.casefile import write_cases
    hits = pd.read_json(out / "held_out_triggers.json")
    print(f"[5/5] synthesising {len(hits)} case files ...")
    prov = dict(descriptor_classifier_mode=mode,
                calibration="development split (60%); held-out untouched until final scoring",
                data="synthetic", generator_seed=meta["seed"])
    write_cases(hits, merchants, txn, res["thresholds"], prov, out / "cases")

    print(f"\ndone in {time.time()-t0:.0f}s. run `python -m driftwatch.demo` for the demo view.")


if __name__ == "__main__":
    main()
