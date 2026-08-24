"""
Trigger layer.

THE RULE, in full. Two branches, deliberately tiered.

  Branch A -- CORROBORATION
      >= 2 distinct signal FAMILIES each cross threshold within a rolling 14-day window.
      Action tier: escalate.

  Branch B -- SUSTAINED SINGLE-FAMILY EXTREME
      1 family exceeds EXTREME_MULT x its threshold on >= SUSTAIN_DAYS consecutive
      observation days.
      Action tier: investigate (lower than Branch A).

Why Branch B exists, and why it is not a cop-out
------------------------------------------------
Branch B was added because the data said so, not to hit a number. Diagnostics showed
bust-out merchants cross the velocity family 13/13 at z~5 and cross NOTHING else --
because a volume ramp is what a bust-out physically is. A pure corroboration rule
cannot catch that class at all, structurally.

Forcing bust-outs to fit a 2-family rule would have meant lowering every other
threshold until a second family fired by accident. That trades a real detection for a
fake one. Instead the policy is tiered, the way an actual risk policy is written: a
much higher bar, a persistence requirement so a one-day spike cannot open a case, and
a weaker recommended action.

Threshold parameterisation
--------------------------
ticket_psi and velocity_peer_z sit on canonical scales (PSI: 0.1 minor / 0.25
significant; z-score: standard deviations), so their thresholds are ABSOLUTE values
from the literature, not portfolio quantiles. Only category_mismatch, which has no
canonical scale, is quantile-parameterised.

Using a portfolio quantile for PSI was the original bug: drifted merchant-days inflate
the tail, which pushed the 93rd percentile to PSI 2.1 -- about eight times the standard
"significant" line -- and made the distribution family unreachable.

Velocity is taken as max(z, 0): we alert on abnormal acceleration, not decline. A
declining merchant is a business problem. This is the harder choice -- it forces
bust-outs to be caught on the ramp rather than the crash, which is where lead time is.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .signals import SIGNAL_FAMILY

TRIGGER_WINDOW = 14
MIN_FAMILIES = 2
EXTREME_MULT = 2.5      # Branch B: this multiple of the family threshold
SUSTAIN_DAYS = 5        # Branch B: consecutive observation days required

SIGNALS = ["category_mismatch", "ticket_psi", "velocity_peer_z", "network_overlap"]

#: Signal set with the content family removed. Used by the ablation in evaluate.py to
#: answer "what does DriftWatch buy when the PA's descriptor field is sparse or opaque?"
#: The family is REMOVED, not zeroed: Branch A still requires two DISTINCT families, and
#: the three that remain (distribution, velocity, network) are all derivable from amount,
#: timing and counterparty identifiers alone.
SIGNALS_NO_CONTENT = [s for s in SIGNALS if s != "category_mismatch"]


def apply_thresholds(sig: pd.DataFrame, thr: dict[str, float],
                     signals: list[str] | None = None) -> pd.DataFrame:
    signals = signals or SIGNALS
    out = sig.copy()
    out["_vel"] = np.maximum(out["velocity_peer_z"], 0.0)
    for s in signals:
        col = "_vel" if s == "velocity_peer_z" else s
        out[f"cross_{s}"] = (out[col] >= thr[s]).astype(np.int8)
        out[f"extreme_{s}"] = (out[col] >= thr[s] * EXTREME_MULT).astype(np.int8)
    return out


def run_triggers(sig: pd.DataFrame, thr: dict[str, float],
                 signals: list[str] | None = None) -> pd.DataFrame:
    """Walk each merchant forward in day order; record the FIRST day either branch
    fires. Once a case is opened the merchant is not re-evaluated.

    `signals` selects which families participate. It defaults to all four; the ablation
    passes SIGNALS_NO_CONTENT. The rule itself is identical either way.
    """
    signals = signals or SIGNALS
    crossed = apply_thresholds(sig, thr, signals)
    fired = []

    for mid, grp in crossed.groupby("merchant_id", sort=False):
        grp = grp.sort_values("day")
        days = grp["day"].to_numpy()
        last_cross = {s: -10**9 for s in signals}
        first_cross: dict[str, int | None] = {s: None for s in signals}
        first_cross_value: dict[str, float] = {s: float("nan") for s in signals}
        run_len = {s: 0 for s in signals}
        hit = None

        for i, t in enumerate(days):
            for s in signals:
                if grp[f"cross_{s}"].iat[i]:
                    last_cross[s] = int(t)
                    if first_cross[s] is None:
                        first_cross[s] = int(t)
                        first_cross_value[s] = float(grp[s].iat[i])
                run_len[s] = run_len[s] + 1 if grp[f"extreme_{s}"].iat[i] else 0

            active = [s for s in signals if t - last_cross[s] < TRIGGER_WINDOW]
            families = {SIGNAL_FAMILY[s] for s in active}

            branch = None
            chosen: list[str] = []
            if len(families) >= MIN_FAMILIES:
                branch, chosen = "A_corroboration", active
            else:
                ext = [s for s in signals if run_len[s] >= SUSTAIN_DAYS]
                if ext:
                    branch, chosen = "B_sustained_extreme", ext

            if branch:
                evidence = []
                for s in chosen:
                    fc = first_cross[s] if first_cross[s] is not None else int(t)
                    # A signal qualifies by crossing anywhere inside the rolling window,
                    # so the value at the trigger day may already have receded below the
                    # threshold. `value` is therefore the reading that actually satisfied
                    # the rule; `value_at_trigger_day` is carried alongside it so a reviewer
                    # can see the decay rather than having to reconcile a sub-threshold
                    # number against a fired signal.
                    fcv = first_cross_value[s]
                    at_trigger = float(grp[s].iat[i])
                    evidence.append(dict(
                        signal=s, family=SIGNAL_FAMILY[s],
                        value=at_trigger if np.isnan(fcv) else fcv,
                        value_at_trigger_day=at_trigger,
                        threshold=float(thr[s]),
                        first_crossed_day=int(fc),
                        consecutive_extreme_days=int(run_len[s]),
                    ))
                hit = dict(
                    merchant_id=mid, trigger_day=int(t), branch=branch,
                    families=sorted({SIGNAL_FAMILY[s] for s in chosen}),
                    signals_fired=evidence,
                    network_partner=str(grp["network_partner"].iat[i]),
                    shared_account=bool(grp["shared_account"].iat[i]),
                    n_txn_window=int(grp["n_txn_window"].iat[i]),
                )
                break

        if hit:
            fired.append(hit)

    cols = ["merchant_id", "trigger_day", "branch", "families", "signals_fired",
            "network_partner", "shared_account", "n_txn_window"]
    return pd.DataFrame(fired) if fired else pd.DataFrame(columns=cols)


def recommended_action(branch: str, families: list[str], shared_account: bool) -> str:
    """Framed in the Directions' own language, not in fraud-score language."""
    if branch == "B_sustained_extreme":
        return ("investigate - open review within 72 hours; single-family sustained "
                "extreme divergence, no corroborating signal family yet")
    if shared_account or "network" in families:
        return ("escalate - open investigation within 72 hours; structural link to another "
                "merchant entity suggests possible undisclosed third-party processing")
    if len(families) >= 3:
        return "escalate - open investigation within 72 hours; multiple independent divergences"
    return ("investigate - open review within 72 hours; hold settlement pending reviewer "
            "confirmation only if divergence is confirmed")
