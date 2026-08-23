# Lead-time evaluation design

## Why lead time and not AUC

`lead_time = T_lag − T_detect`

- `T_lag` — the day the lagging confirming evidence (chargeback surge / LEA hold) would
  have arrived. Held-back ground truth, 30–90 days after true onset.
- `T_detect` — the first day the trigger rule fired.

A detector with excellent AUC that fires once chargebacks are already flowing has bought
**zero days**, because the lagging signal would have caught it anyway. The whole value
proposition is closing the gap between a 72-hour regulatory clock and a 30–90 day evidence
lag, so the metric has to be denominated in days.

## Walk-forward protocol

For each observation day `t`, every signal uses only transactions with `day <= t`. Each
merchant has a 30-day post-onboarding baseline window; no signal fires inside it, and all
drift onsets are generated after it. The trigger walks days in order and records the
**first** firing day per merchant, then stops evaluating that merchant — a real case opens
once.

**The one apparent leak, stated deliberately.** `velocity_peer_z` reads other merchants'
data at the *same* day `t`. That is contemporaneous cross-sectional information, not future
information. It is the view a payment aggregator has and an individual merchant does not,
and it is what makes a portfolio-wide festival surge invisible to the detector.

## Split discipline

Merchants split 60/40 by a fixed seed into development (132) and held-out (88). Thresholds
are grid-searched on **development only**. The held-out split is scored exactly once, at the
end. No threshold was ever selected by looking at held-out performance.

**Calibration objective:** maximise *total lead-days bought across the portfolio*, subject to
dev FP rate ≤ 10%.

This objective was corrected mid-build. The first version maximised *median lead among those
caught*, which is degenerate — it rewards catching two easy merchants and ignoring
everything else, and it produced 18.5% catch on dev with a flattering 66-day median. The
correction is recorded here because the failure mode is exactly the cherry-picking the
brief warns about.

**Threshold parameterisation.** `ticket_psi` and `velocity_peer_z` sit on canonical scales
(PSI 0.10 minor / 0.25 significant; z-scores in standard deviations), so their thresholds
are absolute values from the literature. Only `category_mismatch`, which has no canonical
scale, is a portfolio quantile. Using quantiles for PSI was the second bug found: drifted
merchant-days inflate the tail, pushing the 93rd percentile to PSI 2.1 — about eight times
the standard significance line — which made the distribution family unreachable and hid all
bust-outs.

Selected thresholds: `category_mismatch` 0.190 (p91), `ticket_psi` 0.25, `velocity_peer_z`
2.5, `network_overlap` 0.20.

## Results

| | Development (132) | **Held-out (88)** |
|---|---|---|
| Drifters | 27 | 17 |
| Caught before `T_lag` | 19 (70.4%) | **14 (82.4%)** |
| Median lead | 34.0 d | **32.5 d** |
| Lead IQR | 22–57 d | **20–40 d** |
| False-positive rate | 8.6% (9/105) | **12.7% (9/71)** |
| of which confounders | 5 | 6 |

By drift type, held-out:

| Type | Caught | Median lead | Note |
|---|---|---|---|
| `third_party_layering` | 7/7 | 41.0 d | Strongest multi-signal corroboration (network + mismatch) |
| `bust_out` | 3/5 | 19.0 d | All via Branch B sustained single-family extreme |
| `prohibited_category` | 4/5 | 27.0 d | Content mismatch + ticket PSI shift |

## The generalisation gap, stated plainly

The split is stratified across drift types and confounders. On held-out, 14 of 17 drifters are
caught (82.4%) with a median lead time of 32.5 days. Lead time is consistently maintained
across splits (34.0d dev → 32.5d held-out).

**The held-out catch rate is higher than development, and that is not a result.** 82.4%
(14/17) against 70.4% (19/27) looks like the detector generalises better than it fits, which
would be nonsense. It is sampling noise on 17 drifters:

| | Rate | 95% CI (Wilson) |
|---|---|---|
| Development catch | 70.4% (19/27) | 51.5% – 84.1% |
| **Held-out catch** | **82.4% (14/17)** | **59.0% – 93.8%** |
| Development FP | 8.6% (9/105) | 4.6% – 15.5% |
| **Held-out FP** | **12.7% (9/71)** | **6.8% – 22.4%** |

The two catch intervals overlap across almost their entire range; a two-proportion test on
the difference gives z = 0.89, nowhere near significance. The correct reading is that this
evaluation cannot distinguish the two splits' catch rates at all — not that held-out is
better. Any single number quoted from a 17-drifter split should be read with a ±20-point
interval attached, and the point estimate should not be treated as precise.

**The held-out false-positive rate exceeded its own budget.** Calibration runs with
`max_fp_rate = 0.10` enforced as a hard constraint *on the development split*, where it
lands at 8.6%. On held-out it comes in at 12.7% — over budget. That is the honest cost of
fitting a threshold on one split and applying it to another. It is within the dev
confidence interval, so it is not evidence the constraint is broken, but the budget is a
development-split guarantee and does not transfer as a guarantee. An operator sizing
analyst headcount from the 10% figure would be under-provisioned by roughly a quarter.

The honest summary is: **lead time generalises, all three threat models are caught at substantial
lead time (19–41 days), legitimate-change confounders explain the majority (6 of 9) of held-out
false positives, and the split sizes are too small to support precise rate claims.**

## Provenance of the committed run

| | |
|---|---|
| Descriptor classification | **Gemini 3.5 Flash — 63/63 correct (100%), 8/8 restricted** |
| Fallback lexicon, for comparison | 51/63 (81.0%), 5/8 restricted |
| Case narratives | 19 of 23 Gemini; 4 deterministic template (free-tier quota exhausted mid-run) |
| Seed | 20260823, deterministic — two independent runs produced byte-identical `evaluation.json` |

Every case file records its own `descriptor_classifier_mode` and `narrative_mode`. The four
template narratives are labelled as such rather than quietly presented as model output.

## False-positive cost, stated not buried

| | |
|---|---|
| Cost per wrongly flagged merchant | ₹12,000 (analyst review + relationship friction) — *order-of-magnitude estimate* |
| Cost per missed drift | ₹850,000 (scheme assessment + chargeback write-off + remediation) |
| Expected cost with DriftWatch (held-out) | ₹26.6 lakh |
| Expected cost doing nothing | ₹1.45 crore |
| Net avoided | ₹1.18 crore |
| **Break-even FP cost** | **₹13.2 lakh** — above this the system stops paying |

Both cost inputs live in `evaluate.py` and are the first thing that should be replaced with
real figures. The break-even, not the rate, is the decision criterion.

## Reproducing

```bash
python run_all.py          # 10-25 min; regenerates data, signals, calibration, cases
python -m driftwatch.demo  # prints the table above plus two case files
```

Outputs: `out/evaluation.json`, `out/held_out_triggers.json`, `out/cases/*.json`.
