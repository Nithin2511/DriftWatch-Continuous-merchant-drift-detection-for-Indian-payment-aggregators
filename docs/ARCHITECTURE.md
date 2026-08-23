# DriftWatch — Architecture

**Continuous merchant-drift detection for Indian payment aggregators.**

---

## 1. The problem this system exists to solve

A merchant clears KYC on day 1 and drifts by day 40 — into prohibited categories, into
processing for an undisclosed third party, or into a bust-out.

Two clocks are running, and they are badly mismatched:

| Clock | Duration | Set by |
|---|---|---|
| Time to investigate once a warning signal appears | **72 hours** | Mastercard SMMP (live 24 Jul 2026) |
| Time until confirming evidence arrives (chargebacks, LEA holds) | **30–90 days** | Reality |

A monitoring system that waits for chargebacks cannot meet a 72-hour clock, because by the
time it fires, the lagging evidence has already arrived and the exposure is already booked.

**DriftWatch closes that gap.** It fires on leading, behavioural signals available *now*, and
is graded on how many days of warning it bought before the lagging evidence would have landed.

> The headline metric is **lead time bought**, not AUC.

---

## 2. Design decisions, and why

### 2.1 The output is a case file, not a score

A score cannot be actioned or audited. SMMP requires an acquirer to show *when* a trigger
occurred, *what* was reviewed, and *the basis* for the decision. So the terminal artifact is a
structured case file with per-signal numeric evidence, the exact trigger rule that combined
them, a recommended action, and a plain-language narrative.

### 2.2 The trigger is a rule, not a model

A composite ML score would be more accurate and completely undefensible in an audit. The
trigger is an explicit corroboration rule — *N independent signal families crossing threshold
inside a rolling window* — that a compliance reviewer can read and a regulator can inspect.
The ML lives **inside individual signals**, where each one's output is a single number with a
stated threshold.

### 2.3 The LLM synthesises; it never judges

Gemini is used in exactly two places, both of which are language problems:

1. **Transaction-descriptor → implied category classification.** A genuine text task.
2. **Case-file narrative.** Turning fired evidence into reviewer-readable prose.

The model is never asked "is this merchant fraudulent." The fire/no-fire decision is made by
quantitative signals against thresholds calibrated on a development split. That split is the
difference between a system and an LLM wrapper.

Both Gemini calls degrade to deterministic fallbacks if no API key is present, so the pipeline
is reproducible by anyone cloning the repo. Fallback mode is labelled in the output — it is
never silently substituted.

### 2.4 Velocity is measured **peer-relative**, not absolute

This is the single most important modelling decision in the system.

During Diwali, every merchant's volume ramps. An absolute ramp detector fires on the entire
portfolio and is switched off by the ops team within a week. DriftWatch instead computes each
merchant's short-horizon growth ratio and then scores it **cross-sectionally against every
other merchant on the same day**.

- Everyone surges together → nobody is anomalous → no alerts.
- One merchant surges against a flat portfolio → anomalous.

This requires portfolio-wide visibility on the same day, which is precisely what a payment
aggregator has and an individual merchant does not. It is also the answer to the obvious panel
question about festival seasonality.

### 2.5 UPI-native by construction

No TC40/TC15 card-fraud reporting anywhere in the design. The entities are UPI-shaped: payer
VPA handles, payer PSP, settlement beneficiary account, INR ticket sizes drawn from Indian
commerce distributions. The network signal keys on VPA-population overlap and shared
settlement accounts, which is how undisclosed third-party processing actually surfaces on
UPI rails.

### 2.6 Strictly defense-only

The synthetic generator produces *behavioural consequences* of drift (distribution shifts,
population overlaps, ramp shapes). It contains no evasion logic, no threshold-probing, and no
component that would help a merchant avoid detection. There is deliberately no adversarial
"can I beat my own detector" mode.

---

## 3. The five components

```
                    ┌────────────────────────────────────────────┐
                    │  1. SYNTHETIC DATA LAYER                   │
                    │  generate.py                               │
                    │                                            │
                    │  merchants.csv     — declared profile      │
                    │  transactions.pq   — daily UPI-shaped txns │
                    │  ground_truth.csv  — T0, drift_type, T_lag │
                    │                      (HELD BACK)           │
                    └──────────────┬─────────────────────────────┘
                                   │ transactions + declared profile ONLY
                                   ▼
                    ┌────────────────────────────────────────────┐
                    │  2. SIGNAL ENGINE                          │
                    │  signals.py       (walk-forward, no peek)  │
                    │                                            │
                    │  S1 category_mismatch  (Gemini / fallback) │
                    │  S2 ticket_psi         (PSI vs baseline)   │
                    │  S3 velocity_peer_z    (cross-sectional)   │
                    │  S4 network_overlap    (VPA/account graph) │
                    └──────────────┬─────────────────────────────┘
                                   │ per-merchant-per-day signal frame
                                   ▼
                    ┌────────────────────────────────────────────┐
                    │  3. TRIGGER LAYER                          │
                    │  trigger.py                                │
                    │                                            │
                    │  RULE: >= 2 independent signal families    │
                    │  above threshold within a 14-day window    │
                    │  -> fire, record T_detect + evidence       │
                    └──────────────┬─────────────────────────────┘
                                   │ fired trigger + evidence bundle
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
   ┌────────────────────────────┐   ┌────────────────────────────────┐
   │  4. CASE-FILE SYNTHESIS    │   │  5. EVALUATION HARNESS         │
   │  casefile.py  (Gemini)     │   │  evaluate.py                   │
   │                            │   │                                │
   │  structured JSON + prose   │   │  dev split (60%): calibrate    │
   │  evidence, rule, action    │   │  held-out (40%): report only   │
   │  STR/PMLA-recognisable     │   │                                │
   │                            │   │  lead_time = T_lag - T_detect  │
   └────────────────────────────┘   │  catch rate / FP rate / FP cost│
                                    └────────────────────────────────┘
```

---

## 4. Data flow, precisely

1. `generate.py` writes three artifacts. **`ground_truth.csv` is never read by components 2–4.**
   Only `evaluate.py` opens it, and only after `T_detect` has been recorded.

2. For each day `t` in the observation window, the signal engine computes every signal for
   every merchant using **only transactions with `day <= t`**. There is one deliberate
   exception, documented here because it looks like leakage and is not: the peer-relative
   velocity signal uses other merchants' data *at the same day t*. That is contemporaneous
   cross-sectional information, not future information, and it is exactly what a PA sees.

3. Each merchant has a **baseline window** — the first 30 days after onboarding — used as the
   PSI reference distribution and the mismatch-rate reference. No signal fires inside the
   baseline window. Drift onset `T0` is always generated after it.

4. The trigger layer walks days in order and records the **first** day the rule fires per
   merchant. Once fired, a merchant is not re-evaluated (a real case is opened once).

5. `evaluate.py` joins `T_detect` against held-back `T_lag` and reports lead time.

---

## 5. What each signal is, and its failure mode

| Signal | Family | What it measures | Known failure mode |
|---|---|---|---|
| `category_mismatch` | content | Share of recent transactions whose descriptor implies a category other than the declared one, in excess of the merchant's own baseline mismatch rate | Merchants with legitimately broad catalogues have a high baseline; handled by differencing against own baseline, not an absolute rate |
| `ticket_psi` | distribution | Population Stability Index of the trailing 14-day ticket-size distribution against the merchant's 30-day baseline, fixed decile bins | Genuine product-mix expansion looks identical to drift; this is why one signal alone never fires a case |
| `velocity_peer_z` | velocity | Robust z-score of the merchant's 7-day volume growth ratio against the cross-sectional distribution of that ratio across the portfolio on the same day | A portfolio-wide event that affects only one vertical will make that vertical's merchants look anomalous |
| `network_overlap` | network | Max Jaccard overlap of trailing payer-VPA population against any other merchant, plus shared settlement-account edges | Legitimately related entities (same group, franchise) overlap heavily and will flag; needs a whitelist in production |

Four families. The trigger requires **two different families**, so no single failure mode above
can open a case on its own. That is the entire point of the corroboration rule.

---

## 6. Honest limitations

- **The data is synthetic.** Distribution shapes are chosen to be plausible for Indian
  commerce, not fitted to a real portfolio. What this evaluation demonstrates is that the
  detector buys lead time *against a stated threat model*, not that it will hold at those exact
  numbers on Razorpay's real book. This is stated in the README and should be stated out loud
  in the pitch.
- **Non-drifting merchants carry organic volatility** — growth trends, weekday seasonality, and
  a portfolio-wide festival surge — specifically so the detector cannot win by flagging any
  change at all. Without that, the lead-time number would be meaningless.
- **Thresholds are calibrated on the development split only.** The held-out split is touched
  once, at the end, to produce the reported numbers.
- **Regulatory clause numbers are not fabricated.** Case files cite the programs and duties
  that have been verified (SMMP 72-hour investigation duty, RBI PA Directions ongoing-monitoring
  obligation, VAMP portfolio ratio). Anything not verified is marked `illustrative`.
