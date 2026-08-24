"""
Evaluation harness.

The headline metric is LEAD TIME BOUGHT:

    lead_time = T_lag - T_detect

    T_lag    = the day the lagging, confirming evidence (chargeback surge / LEA hold)
               would have arrived -- held-back ground truth, 30-90 days after true onset
    T_detect = the first day the trigger rule fired

A detector with excellent AUC that only fires once chargebacks are flowing has bought
zero days and is worthless, because the lagging signal would have caught it anyway.

Split discipline
----------------
Merchants are split 60/40 into development and held-out. Thresholds are grid-searched
on DEVELOPMENT ONLY. The held-out split is scored exactly once, at the end. No
threshold is ever chosen by looking at held-out performance.

Threshold parameterisation is deliberately label-free: each signal's threshold is the
q-th percentile of that signal's own distribution across the development portfolio.
Only q is tuned (using dev labels). That means the calibration procedure is
reproducible in production from an unlabelled portfolio.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .trigger import SIGNALS, SIGNALS_NO_CONTENT, run_triggers

# Cost model. Deliberately conservative and stated out loud rather than buried.
# Sources for the loss side are the verified scheme/regulatory exposures; the
# investigation cost is an order-of-magnitude estimate and is labelled as such.
COST_FALSE_POSITIVE_INR = 12_000    # analyst review + merchant relationship friction
COST_MISSED_DRIFT_INR = 850_000     # scheme assessment + chargeback write-off + remediation

#: A catch is "actionable" only if it leaves real room to work. The SMMP duty is to
#: investigate within 72 hours; a 4-day lead means the investigation and the lagging
#: evidence land in the same week, which is not the same product as a 40-day warning.
#: Reported alongside the median so marginal catches are not averaged into it.
ACTIONABLE_LEAD_DAYS = 7


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion, as a percentage pair.

    Used instead of the normal approximation because the splits are small (17 held-out
    drifters); the normal interval misbehaves badly near 0 and 1 at that n.
    """
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    lo, hi = 100 * (centre - half), 100 * (centre + half)
    return (round(max(0.0, lo), 1), round(min(100.0, hi), 1))


def split_merchants(truth: pd.DataFrame, seed: int = 7, dev_frac: float = 0.6) -> tuple[set[str], set[str]]:
    """Stratified split by (drifts, drift_type, confounder) to ensure fair balance across
    all drift types in both development and held-out splits."""
    rng = np.random.default_rng(seed)
    dev, hold = set(), set()
    df = truth[["merchant_id", "drifts", "drift_type", "confounder"]].copy()
    df["stratum"] = df.apply(lambda r: f"{r.drifts}_{r.drift_type}_{r.confounder}", axis=1)

    for _, grp in df.groupby("stratum"):
        mids = grp["merchant_id"].tolist()
        shuffled = [mids[i] for i in rng.permutation(len(mids))]
        cut = int(round(len(mids) * dev_frac))
        dev.update(shuffled[:cut])
        hold.update(shuffled[cut:])
    return dev, hold


def thresholds_at_q(sig: pd.DataFrame, q: dict) -> dict[str, float]:
    """category_mismatch has no canonical scale, so it is parameterised as a portfolio
    quantile. PSI and z-score DO have canonical scales, so they are absolute values
    taken from the literature -- see trigger.py docstring for why quantiles were wrong
    for those."""
    full = {
        "category_mismatch": (float(np.quantile(sig["category_mismatch"],
                                                q["category_mismatch"]))
                              if "category_mismatch" in q else None),
        "ticket_psi": float(q["ticket_psi"]),
        "velocity_peer_z": float(q["velocity_peer_z"]),
        "network_overlap": float(q["network_overlap"]),
    }
    return {k: v for k, v in full.items() if v is not None}


def score(fired: pd.DataFrame, truth: pd.DataFrame, subset: set[str]) -> dict:
    t = truth[truth.merchant_id.isin(subset)].set_index("merchant_id")
    det = dict(zip(fired.merchant_id, fired.trigger_day)) if len(fired) else {}

    drifters = t[t.drifts]
    leads, caught, missed_type = [], 0, []
    for mid, r in drifters.iterrows():
        td = det.get(mid)
        if td is not None and td < r.t_lag:
            caught += 1
            leads.append(int(r.t_lag - td))
        else:
            missed_type.append(r.drift_type)

    non = t[~t.drifts]
    fp_ids = [m for m in non.index if m in det]
    fp_conf = [m for m in fp_ids if bool(non.at[m, "confounder"])]

    n_actionable = sum(1 for l in leads if l > ACTIONABLE_LEAD_DAYS)
    n_d, n_n = len(drifters), len(non)
    catch = caught / n_d if n_d else 0.0
    fpr = len(fp_ids) / n_n if n_n else 0.0

    exp_cost = (len(fp_ids) * COST_FALSE_POSITIVE_INR
                + (n_d - caught) * COST_MISSED_DRIFT_INR)
    do_nothing_cost = n_d * COST_MISSED_DRIFT_INR

    return dict(
        n_drifters=n_d, n_non_drifters=n_n,
        catch_rate=catch, caught=caught,
        median_lead_days=float(np.median(leads)) if leads else 0.0,
        p25_lead_days=float(np.percentile(leads, 25)) if leads else 0.0,
        p75_lead_days=float(np.percentile(leads, 75)) if leads else 0.0,
        min_lead_days=int(min(leads)) if leads else 0,
        max_lead_days=int(max(leads)) if leads else 0,
        catch_rate_ci=wilson_ci(caught, n_d),
        n_actionable=n_actionable,
        actionable_share_of_caught=(n_actionable / caught if caught else 0.0),
        actionable_rate_of_drifters=(n_actionable / n_d if n_d else 0.0),
        actionable_rate_ci=wilson_ci(n_actionable, n_d),
        min_actionable_lead_days=ACTIONABLE_LEAD_DAYS,
        false_positive_rate=fpr, n_false_positives=len(fp_ids),
        false_positive_rate_ci=wilson_ci(len(fp_ids), n_n),
        n_fp_confounders=len(fp_conf),
        n_fp_plain=len(fp_ids) - len(fp_conf),
        # The decision criterion is the break-even, not the rate: the cost per wrongly
        # flagged merchant at which the drift losses avoided stop covering the review bill.
        break_even_cost_per_fp_inr=(
            int(caught * COST_MISSED_DRIFT_INR / len(fp_ids)) if fp_ids else None),
        missed_by_type=pd.Series(missed_type).value_counts().to_dict(),
        expected_cost_inr=int(exp_cost),
        do_nothing_cost_inr=int(do_nothing_cost),
        cost_avoided_inr=int(do_nothing_cost - exp_cost),
        leads=leads, fp_ids=fp_ids, fp_confounder_ids=fp_conf,
    )


def calibrate(sig: pd.DataFrame, truth: pd.DataFrame, dev: set[str],
              max_fp_rate: float = 0.10,
              signals: list[str] | None = None,
              fp_budget: str = "point") -> tuple[dict, dict, list]:
    """Grid-search q on the DEVELOPMENT split only.

    Objective: maximise TOTAL lead-days bought, subject to dev FP rate <= max_fp_rate.
    (Not median-lead-among-those-caught, which is degenerate -- see docs/EVALUATION.md.)

    `signals` selects the participating families. The ablation passes SIGNALS_NO_CONTENT,
    which drops the content grid axis entirely rather than searching a threshold for a
    family that is not in play.
    """
    signals = signals or SIGNALS
    if fp_budget not in ("point", "upper"):
        raise ValueError("fp_budget must be 'point' or 'upper'")
    use_content = "category_mismatch" in signals
    dsig = sig[sig.merchant_id.isin(dev)]
    # content: portfolio quantile (no canonical scale). A single sentinel when ablated,
    # so the remaining grid is searched at exactly the same resolution.
    grid_content = [0.86, 0.91, 0.95, 0.98] if use_content else [None]
    # PSI: canonical interpretation -- 0.10 minor shift, 0.25 significant shift
    grid_dist = [0.15, 0.25, 0.40]
    # peer z-score: standard deviations above the portfolio median that day
    grid_vel = [1.5, 2.0, 2.5]
    # Jaccard overlap of payer-VPA populations; 0.35 is the shared-account floor
    grid_net = [0.20, 0.35]

    trials, best, best_thr = [], None, None
    for qc in grid_content:
        for qd in grid_dist:
            for qv in grid_vel:
                for qn in grid_net:
                    q = dict(ticket_psi=qd, velocity_peer_z=qv, network_overlap=qn)
                    if use_content:
                        q["category_mismatch"] = qc
                    thr = thresholds_at_q(dsig, q)
                    fired = run_triggers(dsig, thr, signals)
                    s = score(fired, truth, dev)
                    # OBJECTIVE: total lead-days bought across the portfolio.
                    # Deliberately NOT median-lead-among-those-caught, which is
                    # degenerate: it rewards catching two easy merchants and
                    # ignoring everything else.
                    total_lead = float(np.sum(s["leads"]))
                    trials.append(dict(q=q, thr=thr, catch=s["catch_rate"],
                                       fpr=s["false_positive_rate"],
                                       lead=s["median_lead_days"], total_lead=total_lead))
                    # 'point' constrains the dev point estimate -- the conventional
                    # choice, and the one the headline numbers use. It does NOT bound the
                    # population rate: a point estimate on 105 non-drifters carries an
                    # interval wide enough to contain values well above the budget, which
                    # is precisely why held-out breaches it. 'upper' constrains the upper
                    # Wilson bound instead, which is the version that actually gives an
                    # operator a guarantee. See docs/EVALUATION.md.
                    observed = (s["false_positive_rate"] if fp_budget == "point"
                                else s["false_positive_rate_ci"][1] / 100.0)
                    if observed > max_fp_rate:
                        continue
                    key = (total_lead, s["catch_rate"])
                    if best is None or key > best:
                        best, best_thr, best_q = key, thr, q
    if best_thr is None:  # no config met the FP budget; take the lowest-FP one
        t0 = min(trials, key=lambda x: x["fpr"])
        best_thr, best_q = t0["thr"], t0["q"]
    return best_thr, best_q, trials


def main(datadir: str = "data", outdir: str = "out", max_fp_rate: float = 0.10,
         ablate_content: bool = False, fp_budget: str = "point") -> dict:
    """Calibrate on dev, score held-out once, write evaluation.json.

    ablate_content removes the content family (category_mismatch) from the signal set
    entirely -- not zeroed, removed -- and recalibrates from scratch. Branch A still
    requires two DISTINCT families; three remain. See docs/EVALUATION.md.
    """
    datadir, outdir = Path(datadir), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    sig = pd.read_parquet(datadir / "signals.parquet")
    truth = pd.read_csv(datadir / "ground_truth.csv")

    signals = SIGNALS_NO_CONTENT if ablate_content else SIGNALS
    dev, hold = split_merchants(truth)

    thr, q, trials = calibrate(sig, truth, dev, max_fp_rate=max_fp_rate,
                               signals=signals, fp_budget=fp_budget)

    dev_fired = run_triggers(sig[sig.merchant_id.isin(dev)], thr, signals)
    dev_res = score(dev_fired, truth, dev)

    # ---- the held-out split is touched exactly once, here ----
    hold_sig = sig[sig.merchant_id.isin(hold)]
    hold_fired = run_triggers(hold_sig, thr, signals)
    hold_res = score(hold_fired, truth, hold)

    # per-drift-type breakdown on held-out
    t = truth.set_index("merchant_id")
    det = dict(zip(hold_fired.merchant_id, hold_fired.trigger_day)) if len(hold_fired) else {}
    by_type, earliest = {}, None
    for dt in ["prohibited_category", "third_party_layering", "bust_out"]:
        rows = t[(t.index.isin(hold)) & (t.drifts) & (t.drift_type == dt)]
        ld = [int(r.t_lag - det[m]) for m, r in rows.iterrows()
              if m in det and det[m] < r.t_lag]
        by_type[dt] = dict(n=len(rows), caught=len(ld),
                           median_lead=float(np.median(ld)) if ld else 0.0,
                           catch_rate_ci=wilson_ci(len(ld), len(rows)))
        # Track the thinnest margin in the whole held-out set. A lead of a few days is
        # nearly no lead against a 72-hour clock, so it gets named rather than averaged
        # away inside the range.
        for mid, r in rows.iterrows():
            if mid in det and det[mid] < r.t_lag:
                lead = int(r.t_lag - det[mid])
                if earliest is None or lead < earliest["lead_days"]:
                    earliest = dict(merchant_id=mid, drift_type=dt, lead_days=lead,
                                    trigger_day=int(det[mid]), t_lag=int(r.t_lag),
                                    subtlety=float(r.subtlety))

    hold_fired.to_json(outdir / "held_out_triggers.json", orient="records", indent=2)
    result = dict(variant=("no_content_ablation" if ablate_content else "full"),
                  signals_used=signals, fp_budget=fp_budget, max_fp_rate=max_fp_rate,
                  thresholds=thr, quantiles=q, n_dev=len(dev), n_held_out=len(hold),
                  development=dev_res, held_out=hold_res, held_out_by_type=by_type,
                  held_out_min_lead_case=earliest)
    clean = json.loads(json.dumps(result, default=float))
    (outdir / "evaluation.json").write_text(json.dumps(clean, indent=2))
    return result


if __name__ == "__main__":
    r = main()
    h = r["held_out"]
    print(json.dumps({k: v for k, v in h.items() if k not in ("leads", "fp_ids")},
                     indent=2, default=float))
