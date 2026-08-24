"""
Case-file synthesis.

The terminal artifact of this system is NOT a score. It is a document a compliance
reviewer can act on inside the 72-hour window and an auditor can reconstruct later.

Section headings deliberately follow the shape a reader familiar with STR/PMLA
reporting conventions would recognise -- subject entity, grounds for review, supporting
data, disposition. This does NOT integrate with FIU-IND or CFCFRMS; it is structured so
that it could feed such a process.

Every number in the file is computed from the transaction record. Nothing is asserted
without a figure behind it. No regulatory clause numbers are cited, because they were
not independently verified -- the programs and duties named were.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .llm import write_narrative, write_narratives
from .signals import BASELINE_DAYS, CURRENT_WINDOW
from .trigger import (EXTREME_MULT, MIN_FAMILIES, SUSTAIN_DAYS, TRIGGER_WINDOW,
                      recommended_action)

RULE_TEXT = {
    "A_corroboration": (
        f"Branch A (corroboration): >= {MIN_FAMILIES} distinct signal families each crossed "
        f"threshold within a rolling {TRIGGER_WINDOW}-day window."),
    "B_sustained_extreme": (
        f"Branch B (sustained single-family extreme): one family exceeded {EXTREME_MULT}x its "
        f"threshold on >= {SUSTAIN_DAYS} consecutive observation days, with no corroborating "
        f"family."),
}

READING = {
    "category_mismatch": ("Share of recent transactions whose descriptor implies a category "
                          "other than the declared one, in excess of this merchant's own "
                          "baseline mismatch rate."),
    "ticket_psi": ("Population Stability Index of the trailing ticket-size distribution "
                   "against this merchant's 30-day post-onboarding baseline. PSI > 0.25 is "
                   "conventionally read as a significant distributional shift."),
    "velocity_peer_z": ("Transaction-volume growth ratio, scored against the same-day "
                        "cross-sectional distribution across the whole portfolio. Measured "
                        "peer-relative so that portfolio-wide seasonal surges do not register."),
    "network_overlap": ("Overlap of this merchant's recent payer-VPA population with another "
                        "merchant's, and/or a settlement account shared with another merchant."),
}


def _profile_deltas(txn: pd.DataFrame, mid: str, onboard: int, tday: int) -> dict:
    d = txn[txn.merchant_id == mid]
    base = d[(d.day >= onboard) & (d.day < onboard + BASELINE_DAYS)]
    cur = d[(d.day > tday - CURRENT_WINDOW) & (d.day <= tday)]
    if not len(base) or not len(cur):
        return {}
    bm, cm = float(base.amount_inr.median()), float(cur.amount_inr.median())
    bv = len(base) / BASELINE_DAYS
    cv = len(cur) / CURRENT_WINDOW
    top = cur.descriptor.value_counts().head(3)
    return dict(
        baseline_median_ticket_inr=round(bm, 2),
        current_median_ticket_inr=round(cm, 2),
        ticket_shift_multiple=round(cm / bm, 2) if bm else None,
        baseline_daily_txns=round(bv, 1),
        current_daily_txns=round(cv, 1),
        volume_shift_multiple=round(cv / bv, 2) if bv else None,
        current_top_descriptors=[{"descriptor": k, "n": int(v)} for k, v in top.items()],
        distinct_payer_vpas_in_window=int(cur.payer_vpa.nunique()),
        refund_rate_in_window=round(float(cur.is_refund.mean()), 4),
    )


def build_case(hit: dict, merchants: pd.DataFrame, txn: pd.DataFrame,
               thresholds: dict, provenance: dict, with_narrative: bool = True) -> dict:
    mid = hit["merchant_id"]
    m = merchants.set_index("merchant_id").loc[mid]
    onboard, tday = int(m.onboarding_day), int(hit["trigger_day"])
    action = recommended_action(hit["branch"], hit["families"], hit["shared_account"])

    sigs = []
    for s in hit["signals_fired"]:
        sigs.append({**s, "reading": READING[s["signal"]],
                     "value": round(float(s["value"]), 4),
                     "value_at_trigger_day": round(float(s["value_at_trigger_day"]), 4),
                     "threshold": round(float(s["threshold"]), 4)})

    case = {
        "case_id": f"DW-{mid}-D{tday:03d}",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "subject_entity": {
            "merchant_id": mid,
            "declared_category": m.declared_category,
            "declared_avg_ticket_inr": float(m.declared_avg_ticket_inr),
            "declared_monthly_volume": int(m.declared_monthly_volume),
            "onboarding_day": onboard,
            "settlement_account": m.settlement_account,
        },
        "trigger_day": tday,
        "days_since_onboarding": tday - onboard,
        "merchant_id": mid,
        "declared_category": m.declared_category,
        "grounds_for_review": {
            "branch": hit["branch"],
            "rule": RULE_TEXT[hit["branch"]],
            "families_fired": hit["families"],
        },
        "signals_fired": sigs,
        "supporting_data": _profile_deltas(txn, mid, onboard, tday),
        "network_context": {
            "linked_merchant": hit["network_partner"] or None,
            "shared_settlement_account": bool(hit["shared_account"]),
        },
        "recommended_action": action,
        "disposition_required_by": "72 hours from trigger_day (Mastercard SMMP investigation duty)",
        "provenance": {
            **provenance,
            "thresholds": {k: round(float(v), 4) for k, v in thresholds.items()},
            "note": ("Thresholds calibrated on the development split only. This case file was "
                     "produced by an automated monitoring system on synthetic data; it is a "
                     "behavioural signal requiring investigation, not a finding of wrongdoing."),
        },
    }

    if with_narrative:
        narrative, mode = write_narrative({
            "merchant_id": mid, "declared_category": m.declared_category,
            "trigger_day": tday, "days_since_onboarding": tday - onboard,
            "signals_fired": sigs, "supporting_data": case["supporting_data"],
            "recommended_action": action, "branch": hit["branch"],
        })
        case["narrative"] = narrative
        case["provenance"]["narrative_mode"] = mode
    return case


def write_cases(hits: pd.DataFrame, merchants: pd.DataFrame, txn: pd.DataFrame,
                thresholds: dict, provenance: dict, outdir: str | Path,
                limit: int | None = None) -> list[dict]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    # Clear case files from any previous run. Case ids embed the trigger day, so a
    # recalibration that moves a trigger writes a NEW file and leaves the old one behind.
    # Two case files for the same merchant at different trigger days, each citing the
    # thresholds of a different calibration, destroys the audit-replay property that is
    # the whole point of emitting a case file.
    for stale in outdir.glob("DW-*.json"):
        stale.unlink()
    rows = hits.to_dict("records")[: limit or len(hits)]

    # Build every case WITHOUT a narrative first, then generate narratives in a handful of
    # batched requests. One request per case needs 23 calls and cannot complete inside the
    # free tier's 20-per-day ceiling, which is how a run ends up with a mix of model and
    # template prose.
    cases = [build_case(hit, merchants, txn, thresholds, provenance, with_narrative=False)
             for hit in rows]

    payloads = [{
        "case_id": c["case_id"], "merchant_id": c["merchant_id"],
        "declared_category": c["declared_category"], "trigger_day": c["trigger_day"],
        "days_since_onboarding": c["days_since_onboarding"],
        "signals_fired": c["signals_fired"], "supporting_data": c["supporting_data"],
        "recommended_action": c["recommended_action"],
        "branch": c["grounds_for_review"]["branch"],
    } for c in cases]

    generated, batch_mode = write_narratives(payloads)

    for c, payload in zip(cases, payloads):
        text = generated.get(c["case_id"])
        if text:
            c["narrative"], c["provenance"]["narrative_mode"] = text, batch_mode
        else:
            # Per-case fallback, labelled per case. The batch may drop individual cases;
            # each one says for itself how it was produced.
            c["narrative"], c["provenance"]["narrative_mode"] = write_narrative(payload)
        (outdir / f"{c['case_id']}.json").write_text(json.dumps(c, indent=2, default=str))

    return cases
