"""
Signal engine.

Four independent signal families, computed walk-forward. For observation day t, every
signal uses only transactions with day <= t.

  S1 category_mismatch  (content)      excess share of recent transactions whose descriptor
                                       implies a category other than the declared one
  S2 ticket_psi         (distribution) PSI of trailing ticket-size distribution vs the
                                       merchant's own 30-day baseline
  S3 velocity_peer_z    (velocity)     merchant's short-horizon growth ratio, robust
                                       z-scored CROSS-SECTIONALLY against the portfolio
                                       on the same day
  S4 network_overlap    (network)      payer-VPA population overlap with any other
                                       merchant, plus shared settlement-account edges

The one apparent leak, documented deliberately
----------------------------------------------
S3 reads other merchants' data at the same day t. That is contemporaneous cross-sectional
information, not future information. It is exactly the view a payment aggregator has and an
individual merchant does not, and it is what makes the signal survive a festival surge:
when the whole portfolio ramps together, no one merchant is anomalous.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import pandas as pd

BASELINE_DAYS = 30
CURRENT_WINDOW = 14      # trailing window for S1/S2
VELOCITY_SHORT = 7
VELOCITY_LONG = 35
NETWORK_WINDOW = 21
NETWORK_EVERY = 7        # network graph refreshed weekly, as it would be in production
MIN_BASELINE_TXNS = 60
MIN_CURRENT_TXNS = 15

SIGNAL_FAMILY = {
    "category_mismatch": "content",
    "ticket_psi": "distribution",
    "velocity_peer_z": "velocity",
    "network_overlap": "network",
}


def psi(ref: np.ndarray, cur: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index. Bin edges are fixed from the reference (baseline)
    distribution, which is the standard construction -- re-binning on the current
    window would mask exactly the shift we are trying to measure."""
    if len(ref) < 20 or len(cur) < 5:
        return 0.0
    edges = np.quantile(ref, np.linspace(0, 1, bins + 1))
    edges = np.unique(edges)
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    r, _ = np.histogram(ref, edges)
    c, _ = np.histogram(cur, edges)
    r = r / max(1, r.sum())
    c = c / max(1, c.sum())
    eps = 1e-4
    r = np.clip(r, eps, None)
    c = np.clip(c, eps, None)
    return float(np.sum((c - r) * np.log(c / r)))


def _robust_z(x: np.ndarray) -> np.ndarray:
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    scale = 1.4826 * mad
    if scale < 1e-6:
        scale = np.std(x) if np.std(x) > 1e-6 else 1.0
    return (x - med) / scale


class SignalEngine:
    def __init__(self, txn: pd.DataFrame, merchants: pd.DataFrame,
                 descriptor_category: dict[str, str]):
        self.merchants = merchants.set_index("merchant_id")
        self.desc_cat = descriptor_category
        txn = txn.sort_values(["merchant_id", "day"], kind="stable").reset_index(drop=True)
        txn["implied_category"] = txn["descriptor"].map(descriptor_category).fillna("unknown")
        decl = self.merchants["declared_category"]
        txn["is_mismatch"] = (
            txn["implied_category"].values != txn["merchant_id"].map(decl).values
        ).astype(np.int8)
        self.txn = txn

        # per-merchant column views for fast windowed slicing
        self.M = {}
        for mid, grp in txn.groupby("merchant_id", sort=False):
            self.M[mid] = dict(
                days=grp["day"].to_numpy(),
                amt=grp["amount_inr"].to_numpy(),
                mism=grp["is_mismatch"].to_numpy(),
                vpa=grp["payer_vpa"].to_numpy(),
                acct=grp["settlement_account"].to_numpy(),
            )

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _slice(days: np.ndarray, lo: int, hi: int) -> slice:
        """transactions with lo <= day <= hi"""
        return slice(int(np.searchsorted(days, lo, "left")),
                     int(np.searchsorted(days, hi, "right")))

    # -------------------------------------------------------------- network
    def _network_scores(self, horizon: int) -> dict[tuple[str, int], dict]:
        """Recompute the shared-identifier graph every NETWORK_EVERY days.
        Returns {(merchant_id, refresh_day): {overlap, partner, shared_account}}."""
        out: dict[tuple[str, int], dict] = {}
        for t in range(BASELINE_DAYS, horizon, NETWORK_EVERY):
            vpa_sets, acct_sets = {}, {}
            for mid, cols in self.M.items():
                s = self._slice(cols["days"], t - NETWORK_WINDOW + 1, t)
                if s.stop - s.start < MIN_CURRENT_TXNS:
                    continue
                vpa_sets[mid] = set(cols["vpa"][s])
                acct_sets[mid] = set(cols["acct"][s])
            if len(vpa_sets) < 2:
                continue

            # inverted index -> only compare merchants that actually share an identifier
            inv = defaultdict(list)
            for mid, s in vpa_sets.items():
                for v in s:
                    inv[v].append(mid)
            pair_hits: Counter = Counter()
            for v, mids in inv.items():
                if len(mids) < 2:
                    continue
                for i in range(len(mids)):
                    for j in range(i + 1, len(mids)):
                        pair_hits[tuple(sorted((mids[i], mids[j])))] += 1

            best: dict[str, tuple[float, str]] = defaultdict(lambda: (0.0, ""))
            for (a, b), hits in pair_hits.items():
                union = len(vpa_sets[a] | vpa_sets[b])
                jac = hits / union if union else 0.0
                if jac > best[a][0]:
                    best[a] = (jac, b)
                if jac > best[b][0]:
                    best[b] = (jac, a)

            acct_inv = defaultdict(set)
            for mid, s in acct_sets.items():
                for a in s:
                    acct_inv[a].add(mid)
            shared_acct = {mid: any(len(acct_inv[a]) > 1 for a in s)
                           for mid, s in acct_sets.items()}

            for mid in vpa_sets:
                jac, partner = best[mid]
                # a shared settlement account is a hard structural link; floor the score
                score = max(jac, 0.35 if shared_acct.get(mid) else 0.0)
                out[(mid, t)] = dict(overlap=float(score), partner=partner,
                                     shared_account=bool(shared_acct.get(mid)))
        return out

    # -------------------------------------------------------------- main
    def compute(self, horizon: int) -> pd.DataFrame:
        net = self._network_scores(horizon)
        net_days = sorted({d for _, d in net})
        rows = []

        for mid, cols in self.M.items():
            days, amt, mism = cols["days"], cols["amt"], cols["mism"]
            onboard = int(self.merchants.at[mid, "onboarding_day"])
            b_lo, b_hi = onboard, onboard + BASELINE_DAYS - 1
            bs = self._slice(days, b_lo, b_hi)
            base_amt = amt[bs]
            if len(base_amt) < MIN_BASELINE_TXNS:
                continue
            base_mismatch_rate = float(mism[bs].mean())

            for t in range(onboard + BASELINE_DAYS, horizon):
                cs = self._slice(days, t - CURRENT_WINDOW + 1, t)
                n_cur = cs.stop - cs.start
                if n_cur < MIN_CURRENT_TXNS:
                    continue

                s1 = float(mism[cs].mean()) - base_mismatch_rate
                s2 = psi(base_amt, amt[cs])

                short = self._slice(days, t - VELOCITY_SHORT + 1, t)
                long_ = self._slice(days, t - VELOCITY_LONG + 1, t - VELOCITY_SHORT)
                n_s = (short.stop - short.start) / VELOCITY_SHORT
                n_l = (long_.stop - long_.start) / (VELOCITY_LONG - VELOCITY_SHORT)
                vel_raw = np.log((n_s + 0.5) / (n_l + 0.5))

                nd = max([d for d in net_days if d <= t], default=None)
                nrec = net.get((mid, nd)) if nd is not None else None

                rows.append((mid, t, s1, s2, vel_raw,
                             (nrec or {}).get("overlap", 0.0),
                             (nrec or {}).get("partner", ""),
                             (nrec or {}).get("shared_account", False),
                             n_cur))

        df = pd.DataFrame(rows, columns=[
            "merchant_id", "day", "category_mismatch", "ticket_psi", "_vel_raw",
            "network_overlap", "network_partner", "shared_account", "n_txn_window"])

        # ---- cross-sectional robust z-score of the velocity ratio, per day ----
        # This is what makes the portfolio-wide festival surge invisible to the detector.
        df["velocity_peer_z"] = 0.0
        for t, grp in df.groupby("day", sort=False):
            if len(grp) < 12:
                continue
            df.loc[grp.index, "velocity_peer_z"] = _robust_z(grp["_vel_raw"].to_numpy())
        return df.drop(columns=["_vel_raw"])
