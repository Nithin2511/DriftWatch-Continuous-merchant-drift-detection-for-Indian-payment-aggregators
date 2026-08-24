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

**This is the system's result: 82.4% catch, 12.7% false positives, 32.5-day median lead,
on held-out, scored once.** Two other configurations appear later in this document — a
no-content *ablation* and an upper-bound-budget *sensitivity analysis*. Neither is an
alternative headline. Both exist to show what happens under a stated stress, and both are
labelled as such wherever they appear.


| | Development (132) | **Held-out (88)** |
|---|---|---|
| Drifters | 27 | 17 |
| Caught before `T_lag` | 19 (70.4%) | **14 (82.4%)** |
| Median lead | 34.0 d | **32.5 d** |
| Caught with lead > 7 d | 17/27 | **13/17 — 76.5% (CI 52.7–90.4)** |
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

## Not every catch is worth the same: the 4-day case

The median is 32.5 days, but the range starts at **4 days**, and a 4-day lead against a
72-hour investigation clock is very nearly no lead at all. Averaging that into a median
flatters the result, so it is reported separately and the case is named.

**Held-out lead distribution (full signal set), sorted:**
`4, 12, 18, 19, 22, 22, 32, 33, 34, 36, 41, 51, 65, 68`

| | Full | No content |
|---|---|---|
| Caught | 14/17 (82.4%) | 9/17 (52.9%) |
| **Caught with lead > 7 days** | **13/17 — 76.5% (CI 52.7–90.4)** | **8/17 — 47.1% (CI 26.2–69.0)** |
| Share of catches clearing 7 days | 92.9% | 88.9% |

`ACTIONABLE_LEAD_DAYS = 7` in `evaluate.py`. Seven days is chosen as roughly double the
72-hour duty — enough room to open a case, request merchant evidence, and dispose of it
before the lagging signal arrives.

**The thinnest margin: `MID0054`.** A `bust_out`, subtlety 1.0 (the *least* subtle band),
triggered on observation day 166 against a `T_lag` of 170 — **4 days**. It is the only
catch in either variant that fails the 7-day bar, and it is the same merchant in both. A
bust-out ramps and then breaks hard; this one broke early relative to its own ramp, so
Branch B's five-day persistence requirement consumed most of the available warning. The
system caught it, but a reviewer would have had four days to act on a case that scheme
evidence was about to confirm anyway. That is close to zero product value, and it is
counted as a catch in the headline 82.4%. The `> 7 days` row is the number to quote when
that distinction matters.

`evaluation.json` records this case by name under `held_out_min_lead_case`, so it cannot
quietly disappear from a future run.

## Named limitation: the false-positive budget is not a guarantee

This is the weakest part of the evaluation and it gets its own section rather than a
footnote.

`calibrate()` enforces `max_fp_rate = 0.10` as a hard constraint on the development split.
Dev lands at 8.6% (9/105). Held-out lands at **12.7%** (9/71) — over budget.

**The position: the constraint does less than its name implies, and the breach is a
property of the constraint, not a failure of generalisation.**

A budget enforced on a *point estimate* over 105 non-drifters bounds nothing about the
population rate. That 8.6% carries a 95% Wilson interval of **4.6–15.5%**. The
configuration that "satisfied" a 10% budget was one whose plausible range already reached
half again above it. Held-out's 12.7% sits inside that interval. Nothing generalised badly;
the constraint was never a guarantee to begin with.

**What a real guarantee would cost, measured.** The statistically correct fix is to
constrain the *upper* confidence bound rather than the point estimate. That mode is
implemented (`fp_budget="upper"` in `calibrate()`), and on this data it is infeasible:

| | |
|---|---|
| Grid points satisfying point-estimate budget ≤10% | 18 of 72 |
| Grid points satisfying **upper-bound** budget ≤10% | **0 of 72** |
| Dev FPs needed for a 10% upper bound at n=105 | ≤ 4/105 (≤3.8%) |
| Lowest dev FP any grid point reaches | 6/105 (5.7%, upper bound 11.9%) |

### Sensitivity analysis, not an alternative result

Pushed as close to an upper-bound budget as the grid allows, held-out FP does fall to
**9.9% (7/71)** — but held-out catch drops from 82.4% to **52.9% (9/17)** and dev catch from
70.4% to 55.6%. Buying a defensible-sounding budget costs roughly a third of the detections,
for a number that still is not guaranteed.

**This 9.9% is a sensitivity result and must never be quoted as the system's
false-positive rate.** The headline configuration is the point-estimate budget, and it is
the defensible choice precisely because the measurement above shows no grid point does
better without gutting detection. A 52.9% catch rate is a worse product than a 12.7%
false-positive rate is a problem.

> **Do not confuse this with the ablation.** Both land on 9/17 caught — coincidentally the
> same count — but they are different experiments. The **ablation** removes the content
> *signal family* and keeps the point-estimate budget (held-out FP **11.3%**, 8/71). This
> **sensitivity analysis** keeps all four families and changes the *budget rule* (held-out
> FP **9.9%**, 7/71). Tell them apart by the false-positive figure.

**What this means operationally.** Three honest statements, in order of usefulness:

1. **Size analyst headcount off the interval's upper bound, not the point estimate.** Plan
   for 15.5%, not 10%. An operator provisioning from the 10% figure is under-resourced by
   roughly half.
2. **The budget is a development-split point constraint.** It should be read as "the
   calibration did not select an obviously reckless configuration", not as a service level.
3. **Fixing it properly needs more non-drifters, not a tighter threshold.** At n=105 the
   interval is simply too wide to certify a 10% rate. The remedy is a larger portfolio or a
   real book — not re-tuning, which only trades detections for a number that still is not
   guaranteed.

The same breach appears in the ablation (dev 7.6%, held-out 11.3%) for the same reason.

The honest summary is: **lead time generalises, all three threat models are caught at substantial
lead time (19–41 days), legitimate-change confounders explain the majority (6 of 9) of held-out
false positives, and the split sizes are too small to support precise rate claims.**

## Ablation: performance without the content signal

`category_mismatch` reads item-level descriptor text. **A real payment aggregator often
does not have that.** A UPI record reliably carries an amount, a timestamp, a payer VPA, a
PSP handle and a settlement account; item descriptors exist only when the merchant chooses
to pass them, and across a long tail of merchants they are sparse, templated, or absent.
See [DATA_PLAN.md](DATA_PLAN.md) for what `descriptor` is in this schema.

So the honest question is not "how well does DriftWatch do?" but "how well does it do when
the content family is unavailable?" That is a number, not a caveat:

```bash
python run_all.py --ablate-content     # writes out-ablation/
```

> Not to be confused with the upper-bound *sensitivity analysis* above, which also lands
> on 9/17 caught. That one keeps all four families and changes the budget rule; this one
> removes a family and keeps the budget rule. Distinguishing figure: ablation FP is 11.3%,
> sensitivity FP is 9.9%.

The content family is **removed from the signal set**, not zeroed. Branch A still requires
two *distinct* families; three remain (distribution, velocity, network), all derivable from
amount, timing and counterparty identifiers alone. The full grid is then re-searched on the
development split under the same objective and the same FP budget, and held-out is scored
once. No threshold, rule, or objective was changed to flatter the ablation.

### Held-out, full signal set vs no content family

| | Full (4 families) | **No content (3 families)** |
|---|---|---|
| Caught before `T_lag` | 14/17 — 82.4% (CI 59.0–93.8) | **9/17 — 52.9% (CI 31.0–73.8)** |
| Median lead | 32.5 d | **36.0 d** |
| Caught with lead > 7 d | 13/17 — 76.5% (CI 52.7–90.4) | **8/17 — 47.1% (CI 26.2–69.0)** |
| Lead IQR | 20–40 d | **22–45 d** |
| Lead range | 4–68 d | **4–68 d** |
| False-positive rate | 12.7% — 9/71 (CI 6.8–22.4) | **11.3% — 8/71 (CI 5.8–20.7)** |
| of which confounders | 6 | **5** |
| Break-even FP cost | ₹13.2 lakh | **₹9.6 lakh** |
| Dev FP (budget ≤ 10%) | 8.6% | **7.6%** |

### By drift type, held-out

| Type | Full | No content | What carries it |
|---|---|---|---|
| `third_party_layering` | 7/7 @ 41.0 d | **6/7 @ 42.5 d** (CI 48.7–97.4) | network overlap + ticket PSI — barely affected |
| `bust_out` | 3/5 @ 19.0 d | **3/5 @ 19.0 d** (CI 23.1–88.2) | Branch B on velocity alone — unaffected |
| `prohibited_category` | 4/5 @ 27.0 d | **0/5** (CI 0.0–43.4) | content only — collapses completely |

### Reading it

**A prediction registered in advance, confirmed afterwards.** This is the part worth more
than any single metric in this document, so it is stated plainly:

> Before a single detector existed, the separability check in
> [DATA_PLAN.md](DATA_PLAN.md#the-separability-check-run-before-any-detector-existed)
> recorded that `prohibited_category` drift has a **median 14-day volume ratio of 1.12**,
> sitting *inside* the non-drifter range (p90 = 1.21). The written conclusion was that
> volume alone cannot separate that class, and that catching it would require a signal
> reading *what is being sold* rather than *how much*.
>
> The ablation is the test of that claim. Remove the content family and
> `prohibited_category` goes **4/5 → 0/5**, while the two classes the prediction did not
> implicate barely move. The prediction was specific, it was written down before the
> evidence existed, and it was falsifiable — had `prohibited_category` survived on volume
> and timing alone, the separability analysis would have been wrong.

The mechanism is unremarkable once stated: a merchant that starts selling a prohibited
product while keeping its ticket sizes, growth rate and payer population stable is, by
construction, invisible to amount/timing/counterparty signals. **The content family is
load-bearing for exactly one threat model, and the analysis said which one in advance.**

**The other two threat models are essentially unaffected.** `third_party_layering` loses one
case of seven; `bust_out` loses none. Layering is caught by payer-VPA overlap and ticket
distribution; a bust-out is a volume ramp, which is what Branch B detects.

**Median lead goes up, not down, and that is not an improvement.** 32.5 → 36.0 days is a
survivorship effect: the cases that still fire are the strongly corroborated ones, which
also tend to fire early. Fewer drifters caught, and the ones caught were always the easy
ones. Do not read the higher median as the ablation performing better.

**The floor.** Stripped of any dependence on merchant-supplied text, DriftWatch still buys a
median **36 days** of lead time on **9 of 17** held-out drifters at an 11.3% false-positive
rate, using only signals every PA already has for every transaction. Both catch intervals
(31.0–73.8 vs 59.0–93.8) overlap, so this evaluation cannot claim the drop is significant at
n=17 either — but the per-class collapse of `prohibited_category` from 4/5 to 0/5 is not a
statistical artefact, it is a structural one.

**Same budget caveat as the headline run.** Dev FP is 7.6%, inside the 10% budget the
calibration enforces; held-out lands at 11.3%, outside it. The budget is a development-split
guarantee and does not transfer as one.

## Provenance of the committed run

| | |
|---|---|
| Descriptor classification | **Gemini 3.5 Flash — 63/63 correct (100%), 8/8 restricted** |
| Fallback lexicon, for comparison | 51/63 (81.0%), 5/8 restricted |
| Case narratives | 21 of 23 Gemini; 2 deterministic template — see note below |
| Narrative requests | 3 batched calls for 23 cases (was 23 calls) |
| Seed | 20260823, deterministic — two independent runs produced byte-identical `evaluation.json` |

Every case file records its own `descriptor_classifier_mode` and `narrative_mode`. The
template narratives are labelled as such rather than quietly presented as model output.

**Why two cases are still template.** The Gemini free tier enforces
`GenerateRequestsPerDayPerProjectPerModel = 20`. One request per case needs 23, plus one
for descriptor classification — 24 against a ceiling of 20, so the run could not complete
however patiently it retried. Exponential backoff with `Retry-After` was added and does not
help against a *daily* cap.

The structural fix is to stop making one call per case. `write_narratives()` batches eight
cases per request, so 23 narratives cost **3 requests** instead of 23 — the same reasoning
that keeps descriptor classification O(vocabulary) rather than O(volume). Verified end to
end: 23 cases in, 23 narratives out, none missing, and every narrative names its own
merchant (no cross-contamination between cases in a batch).

A fresh run therefore needs 4 requests in total and finishes clean. The committed artifact
was produced before the day's quota reset and still shows 2 template narratives; re-running
`python run_all.py` on a fresh daily allowance yields 23/23.

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
python run_all.py                     # full signal set        -> out/
python run_all.py --ablate-content    # no content family      -> out-ablation/
python -m driftwatch.demo             # the CLI demo view
python -m pytest tests -q             # 20 invariant tests
```

Outputs per run: `evaluation.json`, `held_out_triggers.json`, `cases/*.json`.

**Measured stage timings** (220 merchants, 1.03M transactions, seed 20260823):

| Stage | Time |
|---|---|
| `generate()` — 220 merchants, 1.03M transactions | 57.5 s |
| load transactions | 4.1 s |
| `classify_descriptors()` — 1 API call, cached thereafter | 0.7 s |
| `signals.compute()` — 23,643 merchant-days | 14.5 s |
| calibration (72 grid points) + held-out scoring | 56.2 s |
| **compute total** | **~2.2 min** (75.6 s with `--skip-generate`) |
| case narratives | 3 API calls, network-bound |

Compute is roughly **2.2 minutes** end to end. Timings vary by maybe 30% with machine load;
these were taken on an otherwise idle laptop.

The calibration grid is **not** the bottleneck, which is the intuition most people bring to
it: one grid point costs 1.32 s and the whole 72-point search is under a minute. Nor are the
API calls, now that both LLM paths are batched — a full run makes **4 requests** total.
Running without `GEMINI_API_KEY` skips them entirely (labelled fallback) and changes the
wall-clock very little.
