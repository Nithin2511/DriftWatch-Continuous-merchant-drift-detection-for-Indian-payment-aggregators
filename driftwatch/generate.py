"""
Synthetic merchant + UPI transaction generator with held-back ground truth.

Design contract
---------------
The detector must be able to separate *drift* from *organic change*. A generator that
produces flat, well-behaved non-drifters and loud drifters would make the lead-time
number meaningless. So this generator deliberately gives NON-drifting merchants:

  - per-merchant growth trends (positive and negative)
  - weekday seasonality that differs by category
  - a portfolio-wide festival surge (all merchants ramp together)
  - a subset of "confounder" merchants with genuine, legitimate structural change
    (product-mix pivots, viral growth spikes) -- these are expected to produce real
    false positives, and we report them rather than hide them

and gives DRIFTING merchants a subtlety parameter, so a meaningful share of drift is
gradual and hard rather than obvious.

Ground truth (T0, drift_type, T_lag) is written to a separate file that components
2-4 never open. Only evaluate.py reads it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------------
# Portfolio configuration
# ----------------------------------------------------------------------------------

HORIZON_DAYS = 200          # global observation window
N_MERCHANTS = 220
DRIFT_FRACTION = 0.20       # share of merchants that drift
CONFOUNDER_FRACTION = 0.08  # non-drifters with legitimate structural change
BASELINE_DAYS = 30          # per-merchant baseline window (no signal fires inside it)
FESTIVAL_WINDOW = (96, 116)  # portfolio-wide surge, Diwali-shaped

PSPS = ["okhdfcbank", "okicici", "oksbi", "okaxis", "ybl", "paytm", "ibl", "axl"]

# Declared categories in Razorpay-style vocabulary, not raw 4-digit MCCs.
# ticket_mu/sigma parameterise a lognormal in INR.
CATEGORIES = {
    "ecommerce":          dict(ticket_mu=6.4, ticket_sigma=0.75, daily_vol=32, weekend_lift=1.25),
    "food_and_beverage":  dict(ticket_mu=5.7, ticket_sigma=0.55, daily_vol=48, weekend_lift=1.45),
    "it_and_software":    dict(ticket_mu=8.1, ticket_sigma=0.85, daily_vol=9,  weekend_lift=0.55),
    "travel_agency":      dict(ticket_mu=8.6, ticket_sigma=0.95, daily_vol=11, weekend_lift=1.10),
    "financial_services": dict(ticket_mu=7.6, ticket_sigma=0.90, daily_vol=14, weekend_lift=0.70),
    "education":          dict(ticket_mu=7.9, ticket_sigma=0.70, daily_vol=13, weekend_lift=0.80),
}

# Transaction descriptors. These are the text the category-mismatch signal reads.
DESCRIPTORS = {
    "ecommerce": [
        "cotton kurta set", "running shoes size 9", "bluetooth earbuds", "steel water bottle",
        "wall clock", "yoga mat", "backpack 30l", "phone case", "bedsheet double",
        "kitchen storage set", "denim jacket", "sunglasses", "table lamp",
    ],
    "food_and_beverage": [
        "paneer butter masala", "veg biryani", "cold coffee", "masala dosa", "chicken roll",
        "family combo meal", "filter coffee 2x", "gulab jamun 4pc", "thali lunch",
        "cheese pizza medium", "samosa plate", "iced tea",
    ],
    "it_and_software": [
        "saas subscription monthly", "api usage overage", "seat licence renewal",
        "cloud storage tier2", "support plan annual", "developer seat addon",
        "integration setup fee", "priority sla upgrade",
    ],
    "travel_agency": [
        "flight booking del-bom", "hotel 2 nights goa", "cab airport transfer",
        "holiday package 4n5d", "visa processing fee", "travel insurance addon",
        "train ticket booking", "bus ticket blr-mys",
    ],
    "financial_services": [
        "advisory fee quarterly", "portfolio review", "insurance premium",
        "loan processing charge", "demat maintenance", "tax filing assistance",
        "financial planning session",
    ],
    "education": [
        "course fee semester", "test series enrolment", "live batch access",
        "study material kit", "doubt clearing addon", "certification exam fee",
        "workshop registration",
    ],
}

# Categories that trigger prohibited-category drift. Deliberately generic labels:
# these are risk *classifications*, not operational detail.
RESTRICTED_DESCRIPTORS = [
    "nutraceutical rx pack", "replica branded watch", "gaming credit topup",
    "forex signal subscription", "unlicensed supplement bundle", "replica handbag",
    "offshore wallet loadup", "prediction contest entry",
]


@dataclass
class GroundTruth:
    merchant_id: str
    drifts: bool
    drift_type: str | None
    t0: int | None
    t_lag: int | None
    subtlety: float | None       # 1.0 = obvious, 0.35 = very subtle
    principal_id: str | None     # for third_party_layering
    confounder: bool             # legitimate structural change, NOT drift


def _weekday_factor(day: int, weekend_lift: float) -> float:
    dow = day % 7
    return weekend_lift if dow in (5, 6) else 1.0


def _festival_factor(day: int, category: str) -> float:
    """Portfolio-wide surge. Every merchant ramps -- this is what defeats a naive
    absolute-velocity detector and is why the velocity signal is peer-relative."""
    lo, hi = FESTIVAL_WINDOW
    if not (lo <= day <= hi):
        return 1.0
    peak = (lo + hi) / 2
    width = (hi - lo) / 2
    shape = np.exp(-((day - peak) ** 2) / (2 * (width / 1.6) ** 2))
    magnitude = {
        "ecommerce": 2.4, "food_and_beverage": 1.7, "travel_agency": 1.9,
        "it_and_software": 1.15, "financial_services": 1.2, "education": 1.3,
    }[category]
    return 1.0 + (magnitude - 1.0) * shape


def _make_vpa(rng: np.random.Generator, pool_seed: int, idx: int) -> str:
    return f"u{pool_seed:04d}{idx:05d}@{PSPS[(pool_seed + idx) % len(PSPS)]}"


def generate(seed: int = 20260823, outdir: str | Path = "data") -> dict:
    rng = np.random.default_rng(seed)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cat_names = list(CATEGORIES)

    # ---------------- merchant declared profiles ----------------
    merchants = []
    for i in range(N_MERCHANTS):
        cat = cat_names[i % len(cat_names)]
        cfg = CATEGORIES[cat]
        onboard = int(rng.integers(0, HORIZON_DAYS - 75))
        scale = float(np.exp(rng.normal(0, 0.45)))
        declared_vol = max(3.0, cfg["daily_vol"] * scale)
        declared_ticket = float(np.exp(cfg["ticket_mu"] + rng.normal(0, 0.18)))
        merchants.append(dict(
            merchant_id=f"MID{i:04d}",
            declared_category=cat,
            declared_avg_ticket_inr=round(declared_ticket, 2),
            declared_monthly_volume=int(declared_vol * 30),
            onboarding_day=onboard,
            settlement_account=f"ACC{rng.integers(10**7, 10**8)}",
            _scale=scale,
        ))
    mdf = pd.DataFrame(merchants)

    # ---------------- assign drift / confounder roles ----------------
    idx = rng.permutation(N_MERCHANTS)
    n_drift = int(N_MERCHANTS * DRIFT_FRACTION)
    n_conf = int(N_MERCHANTS * CONFOUNDER_FRACTION)
    drift_idx = set(idx[:n_drift].tolist())
    conf_idx = set(idx[n_drift:n_drift + n_conf].tolist())

    drift_types = ["prohibited_category", "third_party_layering", "bust_out"]
    truth: list[GroundTruth] = []
    # candidate "principals" for layering: established non-drifting merchants
    principal_pool = [i for i in range(N_MERCHANTS)
                      if i not in drift_idx and i not in conf_idx]

    for i in range(N_MERCHANTS):
        row = mdf.iloc[i]
        onboard = int(row.onboarding_day)
        active_days = HORIZON_DAYS - onboard
        if i in drift_idx:
            dtype = drift_types[int(rng.integers(0, 3))]
            # drift must start after the baseline window and leave room to observe
            earliest = onboard + BASELINE_DAYS + 5
            latest = HORIZON_DAYS - 35
            if earliest >= latest:
                t0 = earliest
            else:
                t0 = int(rng.integers(earliest, latest))
            lag_lo, lag_hi = {
                "bust_out": (30, 55),
                "third_party_layering": (45, 90),
                "prohibited_category": (40, 90),
            }[dtype]
            t_lag = t0 + int(rng.integers(lag_lo, lag_hi))
            # ~25% of drifters are genuinely subtle
            subtlety = float(rng.choice([1.0, 0.75, 0.5, 0.35], p=[0.35, 0.4, 0.15, 0.10]))
            principal = (f"MID{int(rng.choice(principal_pool)):04d}"
                         if dtype == "third_party_layering" else None)
            truth.append(GroundTruth(row.merchant_id, True, dtype, t0, t_lag,
                                     subtlety, principal, False))
        elif i in conf_idx:
            t0 = int(rng.integers(onboard + BASELINE_DAYS + 5, max(onboard + BASELINE_DAYS + 6,
                                                                  HORIZON_DAYS - 25)))
            truth.append(GroundTruth(row.merchant_id, False, None, t0, None,
                                     None, None, True))
        else:
            truth.append(GroundTruth(row.merchant_id, False, None, None, None,
                                     None, None, False))

    tdf = pd.DataFrame([asdict(t) for t in truth])
    gt_by_mid = {t.merchant_id: t for t in truth}

    # ---------------- customer pools ----------------
    pool_size = {}
    for i in range(N_MERCHANTS):
        row = mdf.iloc[i]
        pool_size[row.merchant_id] = int(max(40, row.declared_monthly_volume * 0.9))

    # ---------------- transaction stream ----------------
    records = []
    for i in range(N_MERCHANTS):
        row = mdf.iloc[i]
        mid = row.merchant_id
        cat = row.declared_category
        cfg = CATEGORIES[cat]
        gt = gt_by_mid[mid]
        onboard = int(row.onboarding_day)

        base_vol = cfg["daily_vol"] * row._scale
        growth = float(rng.normal(0.0022, 0.0035))       # organic trend, can be negative
        vol_noise = float(rng.uniform(0.16, 0.34))
        mu, sigma = cfg["ticket_mu"] + rng.normal(0, 0.18), cfg["ticket_sigma"]
        vocab = DESCRIPTORS[cat]
        leak_rate = float(rng.uniform(0.02, 0.10))       # legit cross-category items
        settle = row.settlement_account
        pool_seed = i
        psize = pool_size[mid]

        # confounder pivot target
        conf_target = None
        if gt.confounder:
            conf_target = str(rng.choice([c for c in cat_names if c != cat]))
            conf_kind = str(rng.choice(["pivot", "viral"]))

        # layering principal characteristics
        prin_cfg = prin_vocab = prin_seed = None
        share_settlement = False
        if gt.drift_type == "third_party_layering":
            p_idx = int(gt.principal_id[3:])
            prin_row = mdf.iloc[p_idx]
            prin_cfg = CATEGORIES[prin_row.declared_category]
            prin_vocab = DESCRIPTORS[prin_row.declared_category]
            prin_seed = p_idx
            share_settlement = bool(rng.random() < 0.5)   # half share an account, half don't

        for day in range(onboard, HORIZON_DAYS):
            age = day - onboard
            f = (_weekday_factor(day, cfg["weekend_lift"])
                 * _festival_factor(day, cat)
                 * (1.0 + growth * age)
                 * float(np.exp(rng.normal(0, vol_noise))))

            d_mu, d_sigma, d_vocab, d_leak = mu, sigma, vocab, leak_rate
            restricted_mix = 0.0
            foreign_pool_mix = 0.0
            refund_rate = 0.004

            # ---- inject drift ----
            if gt.drifts and day >= gt.t0:
                prog = min(1.0, (day - gt.t0) / 30.0)     # ramp-in over 30 days
                s = gt.subtlety

                if gt.drift_type == "prohibited_category":
                    restricted_mix = 0.55 * prog * s
                    d_mu = mu + 0.35 * prog * s
                    f *= (1.0 + 0.25 * prog * s)

                elif gt.drift_type == "third_party_layering":
                    foreign_pool_mix = 0.60 * prog * s
                    d_mu = mu + (prin_cfg["ticket_mu"] - mu) * 0.7 * prog * s
                    d_sigma = sigma + (prin_cfg["ticket_sigma"] - sigma) * 0.7 * prog * s
                    f *= (1.0 + 0.9 * prog * s)

                elif gt.drift_type == "bust_out":
                    ramp_len = 21
                    if day - gt.t0 <= ramp_len:
                        r = (day - gt.t0) / ramp_len
                        f *= (1.0 + 3.4 * r * s)
                        d_mu = mu + 0.55 * r * s
                    else:                                   # the break
                        f *= max(0.05, 1.0 - 0.9 * s)
                        refund_rate = 0.05 + 0.15 * s

            # ---- inject legitimate confounder change (NOT drift) ----
            if gt.confounder and day >= gt.t0:
                prog = min(1.0, (day - gt.t0) / 25.0)
                if conf_kind == "pivot":
                    d_vocab = vocab + DESCRIPTORS[conf_target]
                    d_leak = leak_rate + 0.45 * prog
                    d_mu = mu + (CATEGORIES[conf_target]["ticket_mu"] - mu) * 0.5 * prog
                else:                                       # viral growth
                    f *= (1.0 + 2.2 * prog)

            n = int(max(0, rng.poisson(max(0.2, base_vol * f))))
            if n == 0:
                continue

            tickets = np.exp(rng.normal(d_mu, d_sigma, n))
            for k in range(n):
                u = rng.random()
                if u < restricted_mix:
                    desc = str(rng.choice(RESTRICTED_DESCRIPTORS))
                elif u < restricted_mix + d_leak:
                    other = str(rng.choice([c for c in cat_names if c != cat]))
                    desc = str(rng.choice(DESCRIPTORS[other]))
                elif foreign_pool_mix > 0 and rng.random() < foreign_pool_mix:
                    desc = str(rng.choice(prin_vocab))
                else:
                    desc = str(rng.choice(d_vocab))

                if foreign_pool_mix > 0 and rng.random() < foreign_pool_mix:
                    payer = _make_vpa(rng, prin_seed, int(rng.integers(0, pool_size[gt.principal_id])))
                else:
                    payer = _make_vpa(rng, pool_seed, int(rng.integers(0, psize)))

                # Half of layering cases route a share of settlements to the
                # principal's account -- the strongest network signal. The other
                # half do not, so the network signal cannot carry that class alone.
                use_principal_account = (
                    share_settlement
                    and gt.drift_type == "third_party_layering"
                    and day >= gt.t0
                    and rng.random() < 0.6
                )
                acct = (mdf.iloc[prin_seed].settlement_account
                        if use_principal_account else settle)

                records.append((
                    mid, day, round(float(tickets[k]), 2), desc, payer,
                    payer.split("@")[1], acct, int(rng.random() < refund_rate),
                ))

    txn = pd.DataFrame.from_records(records, columns=[
        "merchant_id", "day", "amount_inr", "descriptor", "payer_vpa",
        "payer_psp", "settlement_account", "is_refund",
    ])

    mdf = mdf.drop(columns=["_scale"])
    mdf.to_csv(outdir / "merchants.csv", index=False)
    txn.to_parquet(outdir / "transactions.parquet", index=False)
    tdf.to_csv(outdir / "ground_truth.csv", index=False)

    meta = dict(
        seed=seed, horizon_days=HORIZON_DAYS, n_merchants=N_MERCHANTS,
        n_transactions=int(len(txn)), n_drifters=int(tdf.drifts.sum()),
        n_confounders=int(tdf.confounder.sum()),
        baseline_days=BASELINE_DAYS, festival_window=list(FESTIVAL_WINDOW),
        drift_type_counts=tdf.drift_type.value_counts().to_dict(),
    )
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
