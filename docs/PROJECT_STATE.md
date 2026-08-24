# Project state

Orientation for anyone (or any assistant session) picking this up cold. It records
decisions that are settled, so they are not re-litigated, and the current numbers, so
stale ones are not carried forward.

Submission: Razorpay AI Buildathon, Track 02 (AI Risk Manager). The deliverable is a public
repo plus a pitch, judged by engineers who will interrogate the architecture and the
numbers. Depth and defensibility beat polish. A number that cannot survive "how did you
validate that" is worse than no number.

---

## Current numbers — held-out, scored once

Regenerate with `python run_all.py`; never hand-edit these into docs.

| | Full (4 families) | No content (3 families) |
|---|---|---|
| Caught before `T_lag` | 14/17 — 82.4% (CI 59.0–93.8) | 9/17 — 52.9% (CI 31.0–73.8) |
| Caught with lead > 7 d | 13/17 — 76.5% (CI 52.7–90.4) | 8/17 — 47.1% (CI 26.2–69.0) |
| Median lead | 32.5 d (IQR 20–40, range 4–68) | 36.0 d (IQR 22–45) |
| False-positive rate | 12.7% — 9/71 (CI 6.8–22.4) | 11.3% — 8/71 (CI 5.8–20.7) |
| Break-even FP cost | ₹13.2 L | ₹9.6 L |

Development split (full): 19/27 — 70.4%, median lead 34.0 d, FP 8.6% (9/105).

By drift type, held-out full → ablated: `third_party_layering` 7/7 → 6/7,
`bust_out` 3/5 → 3/5, `prohibited_category` 4/5 → **0/5**.

Thresholds (full): `category_mismatch` 0.1895 (p91), `ticket_psi` 0.25,
`velocity_peer_z` 2.5, `network_overlap` 0.20.

Seed 20260823 is deterministic: two independent runs produced byte-identical
`evaluation.json`.

---

## Settled decisions — do not undo

**Velocity is peer-relative.** Robust z-scored cross-sectionally against the whole
portfolio on the same day. This is what makes the portfolio-wide Diwali surge invisible.
Reading other merchants' data at day *t* is contemporaneous, not lookahead, and it is the
view a PA has that a single merchant does not.

**The trigger is a rule, not a learned combiner.** ML lives inside individual signals; the
combination is an explicit two-branch rule a reviewer can read and an auditor can replay. A
learned combiner would score better and be indefensible in an audit.

**The LLM synthesises, never judges.** Descriptor classification (a text task) and case
narratives (a language task). It is never asked whether a merchant is fraudulent. The
fire/no-fire decision is entirely quantitative. A test enforces this.

**LLM calls are O(vocabulary), not O(volume).** 63 unique descriptors across 1.03M
transactions. Never call per transaction.

**The output is a case file, not a score.** SMMP requires showing when the trigger fired,
what was reviewed, and the basis for the decision.

**Fallback mode is always labelled** in `provenance`. Never silently substituted.

**PSI and z thresholds are canonical absolute values, not portfolio quantiles.** Drifted
merchant-days inflate the tail; a p93 lands near PSI 2.1, roughly 8x the 0.25 significance
line, which makes the distribution family unreachable and hides every bust-out. Only
`category_mismatch`, which has no canonical scale, uses a quantile.

**Bust-outs are structurally single-family.** They cross velocity at z≈5 and cross nothing
else, because a volume ramp is what a bust-out is. Handled with the tiered Branch B (2.5x,
5 consecutive days, weaker recommended action) — *not* by lowering other thresholds until a
second family fired by accident.

**UPI-native, defense-only.** No TC40/TC15, no card-chargeback reporting. The generator
produces behavioural consequences of drift; no evasion logic, no threshold-probing.

**`ground_truth.csv` is read by `evaluate.py` alone.** Enforced by a static-scan test.

---

## Evaluation discipline

- Thresholds calibrate on the **development split only**. Held-out is scored **once**.
- Any change to a signal, threshold, or rule requires **full recalibration** and
  re-reported held-out numbers. Never carry old numbers into the docs.
- Report the generalisation gap honestly, including when it is unflattering.
- No cherry-picked demo merchants; the demo deliberately shows a real false positive.
- Never fabricate a regulatory clause number.

---

## Provider

**Google Gemini (`gemini-3.5-flash`), by the project owner's decision** — chosen for
prototyping. `driftwatch/llm.py` is Gemini-only; there is no Claude/Anthropic path. The
model ID is pinned rather than `-latest`, because a floating alias would silently
invalidate the numbers in EVALUATION.md. Verified against Google's model list:
`models/gemini-3.5-flash`, displayName "Gemini 3.5 Flash".

Classifier accuracy on the 63-descriptor vocabulary: Gemini **63/63 (100%)**, deterministic
lexicon fallback **51/63 (81.0%)**, restricted subset 8/8 vs 5/8.

**Free-tier ceiling is `GenerateRequestsPerDayPerProjectPerModel = 20`** — per day, per
model. One narrative request per case needs 23 plus one classification call = 24, which
cannot complete however patiently it retries. Backoff does not solve a *daily* cap.

Fix: `write_narratives()` batches eight cases per request, so 23 narratives cost 3 requests
and a full run costs 4. Verified: 23 in, 23 out, none missing, no cross-contamination
between cases sharing a batch. `llm.py` also paces calls (`MIN_CALL_INTERVAL_S = 6`) and
retries 429/5xx with exponential backoff honouring `Retry-After`, which handles per-minute
limits. `GEMINI_MODEL` overrides the pinned model (quota is per-model, useful when one is
exhausted). Without a key the pipeline runs end to end on deterministic fallbacks, labelled
in every output.

Committed artifact currently shows 21/23 Gemini narratives — produced before the batching
fix and before a quota reset. A fresh `python run_all.py` yields 23/23.

---

## Named limitations — already written up, do not "discover" them again

1. **The FP budget is not a guarantee.** It constrains a point estimate on 105 dev
   non-drifters (8.6%, CI 4.6–15.5). Held-out's 12.7% is inside that interval. Constraining
   the *upper* bound instead is implemented (`fp_budget="upper"`) and infeasible here: 0 of
   72 grid points qualify, since a 10% upper bound needs ≤4/105 and the grid floor is 6/105.
   Forcing it costs catch 82.4% → 52.9%. Operators should size headcount off 15.5%.
2. **One catch had a 4-day lead** (`MID0054`, bust_out, subtlety 1.0, trigger day 166 vs
   `T_lag` 170) — nearly no lead against a 72-hour clock. Hence `ACTIONABLE_LEAD_DAYS = 7`
   and the "caught with lead > 7 d" row reported alongside the median.
3. **`descriptor` is merchant-supplied and often absent in production.** 63/63 reflects an
   authored vocabulary, not a solved problem. The ablation is the answer.
4. **Held-out beats dev on catch rate** (82.4% vs 70.4%). Sampling noise at n=17, z = 0.89.
   Not a result; documented as such.
5. **Small splits.** Every rate carries roughly a ±20-point interval. Quote intervals.

---

## Runtime, measured

| Stage | Time |
|---|---|
| `generate()` | 57.5 s |
| load transactions | 1 s |
| `signals.compute()` | 20 s |
| calibration (72 grid points) + scoring | 82 s |
| 23 narrative calls | rate-limit bound |

The calibration grid is **not** the bottleneck — a common wrong assumption. One grid point
is 1.32 s. The LLM stage dominates wall-clock.

---

## Repo shape

```
driftwatch/   generate · signals · trigger · casefile · evaluate · llm · demo
tests/        20 invariant tests (run: python -m pytest tests -q)
docs/         ARCHITECTURE · DATA_PLAN · EVALUATION · PANEL_QA · CUT_LIST · DEMO_SCRIPT
frontend/     React dashboard, static, deployed to GitHub Pages
```

`run_all.py` is the pipeline; `export_frontend_data.py` regenerates the dashboard's data
modules from `out/` and **refuses to export** if case files and evaluation disagree.

Live dashboard:
<https://nithin2511.github.io/DriftWatch-Continuous-merchant-drift-detection-for-Indian-payment-aggregators/>

Generated directories (`data/`, `out/`, `out-ablation/`) are gitignored. `data/` and `out/`
are unanchored-glob hazards: the ignore rules are root-anchored (`/data/`) because a bare
`data/` also matches `frontend/src/data/`, which **is** committed.

---

## Traps hit before — don't repeat

- **Case files accumulate.** Case ids embed the trigger day, so recalibration writes new
  files and orphans old ones. `write_cases()` clears `DW-*.json` first. Two case files for
  one merchant at different trigger days destroys the audit-replay property.
- **A cached fallback used to poison every later run.** `classify_descriptors` returned any
  cache covering the descriptor set regardless of mode, so one keyless run pinned the
  pipeline to fallback forever while looking healthy. Fixed and regression-tested.
- **Mermaid on GitHub renders client-side and fails intermittently.** The architecture
  diagram is a committed SVG (`docs/architecture.svg`), generated with `htmlLabels: false`
  — Mermaid's default `<foreignObject>` labels do not render when an SVG is loaded via
  `<img>`, which is how GitHub embeds it, and the diagram would show no text at all.
- **GitHub Pages serves project sites from `/<repo>/`.** `vite.config.js` takes `base` from
  `BASE_PATH`, set by the deploy workflow from the repo name. Without it the page is blank
  and 404s on its own bundle.
