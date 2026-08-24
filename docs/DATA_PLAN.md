# Data plan

## What the generator produces

`driftwatch/generate.py`, seed `20260823`, three artifacts:

| File | Contents | Read by |
|---|---|---|
| `merchants.csv` | 220 declared profiles: category, avg ticket, monthly volume, onboarding day, settlement account | signals, casefile |
| `transactions.parquet` | 1,034,052 UPI-shaped transactions: day, amount, descriptor, payer VPA, payer PSP, settlement account, refund flag | signals, casefile |
| `ground_truth.csv` | `drifts`, `drift_type`, `T0`, `T_lag`, `subtlety`, `principal_id`, `confounder` | **`evaluate.py` only** |

Ground truth is never opened by the data, signal, trigger or case-file layers.

- 220 merchants over a 200-day horizon, staggered onboarding
- 44 drifters (20%), 17 confounders (8%), 159 clean
- Categories in Razorpay-style vocabulary (`ecommerce`, `food_and_beverage`,
  `it_and_software`, `travel_agency`, `financial_services`, `education`), not raw MCCs
- Ticket sizes lognormal per category, in INR

## Where `descriptor` comes from, and why that matters

This is the field a Razorpay risk engineer will ask about first, so it is worth being
precise about what it is here and what it maps to in production.

**In this schema.** Every synthetic transaction carries a `descriptor`: a short free-text
item string such as `cotton kurta set`, `paneer butter masala`, or `saas seat licence`.
There are 63 unique values across 1.03M transactions. `signals.py` maps each descriptor to
an implied merchant category (via Gemini, with a deterministic lexicon fallback) and
`category_mismatch` measures the excess share of transactions whose implied category is not
the merchant's declared one.

**In production.** There is no single guaranteed equivalent. A UPI transaction record
reliably carries an amount, a timestamp, a payer VPA, a payer PSP handle, a settlement
account, and merchant identifiers. Item-level text is *optional and merchant-supplied*:
it may arrive as an order note, an invoice line, a payment-page description, or a merchant
reference string — and for a large share of merchants it arrives as an order ID, a
templated constant, or nothing at all. Coverage is best among large integrated merchants
with structured catalogues and worst across exactly the long tail where drift risk
concentrates. **We have not measured real-world population rates and do not assert one.**

**The classifier scoring 63/63 is a property of the vocabulary, not evidence the problem is
solved.** We authored `DESCRIPTORS` and `RESTRICTED_DESCRIPTORS` in `generate.py`, so every
string is unambiguous by construction: `replica designer handbag` has exactly one defensible
category. Real descriptors are abbreviated, misspelled, transliterated, bilingual, padded
with SKU codes, or deliberately neutral — `ORDER 88213`, `PAYMENT`, `INV/2026/0412`. A 100%
score here says the pipeline wires up correctly and that Gemini beats a hand-written lexicon
on a clean vocabulary (63/63 vs 51/63). It says nothing about accuracy on a real descriptor
distribution, and it should not be quoted as if it did.

**So the honest question is what the system does without it.** That is answered as a number,
not a caveat: see
[EVALUATION.md → Ablation: performance without the content signal](EVALUATION.md#ablation-performance-without-the-content-signal).
With the content family removed and the rule fully recalibrated, DriftWatch still buys a
median 36 days of lead on 9 of 17 held-out drifters at an 11.3% false-positive rate, using
only amount, timing and counterparty identifiers. `prohibited_category` detection collapses
from 4/5 to 0/5 — that threat model depends on content entirely. Run it with
`python run_all.py --ablate-content`.

## Why it is a fair test

The failure mode of any synthetic evaluation is a generator that makes non-drifters boring.
Then the detector wins by flagging *any* change and the lead-time number means nothing.
Four deliberate defences:

**1. Non-drifters are not flat.** Every merchant gets an organic growth trend (which can be
negative), weekday seasonality that differs by category (F&B lifts 1.45x at weekends,
SaaS drops to 0.55x), and multiplicative volume noise.

**2. A portfolio-wide festival surge.** Days 96–116, Diwali-shaped, magnitude varying by
category (ecommerce 2.4x, SaaS 1.15x). Every merchant ramps together. This exists
specifically to defeat a naive absolute-velocity detector, and is why the velocity signal
had to be built peer-relative.

**3. Seventeen confounders.** Non-drifting merchants with genuine legitimate structural
change — a category pivot (descriptor mix and ticket sizes migrate toward another real
category) or viral growth (2.2x ramp). These *should* be hard, and 6 of the 9 held-out
false positives are confounders. They are reported as false positives, not excused.

**4. A subtlety parameter.** Drift magnitude scales by `subtlety` ∈ {1.0, 0.75, 0.5, 0.35}
drawn at p = {0.35, 0.40, 0.15, 0.10}, so a quarter of drifters are genuinely faint.

## The separability check, run before any detector existed

14-day volume ratio around `T0`, drifters vs non-drifters at a matched pseudo-`T0`:

| Cohort | p25 | p50 | p75 |
|---|---|---|---|
| `bust_out` | 1.84 | 1.98 | 2.12 |
| `third_party_layering` | 1.17 | 1.35 | 1.44 |
| `prohibited_category` | 1.00 | **1.12** | 1.26 |
| non-drifters | — | 1.02 | 1.13 (p90 1.21, max 1.64) |

`prohibited_category` sits **inside** the non-drifter distribution on volume. It cannot be
caught by a volume detector at all, which forces genuine multi-signal corroboration rather
than one loud feature doing all the work.

## How each drift type is injected

Ramp-in over 30 days from `T0`, scaled by `subtlety`:

- **`prohibited_category`** — descriptor mix migrates toward a restricted vocabulary
  (up to 55%), ticket sizes shift +0.35 in log space, volume +25%. Gradual by construction.
- **`third_party_layering`** — up to 60% of payer VPAs begin drawing from a *principal*
  merchant's customer pool, ticket distribution converges 70% toward the principal's,
  descriptors shift toward the principal's category, volume +90%. Half of these cases also
  route settlements to the principal's account; **half deliberately do not**, so the network
  signal cannot carry the class on its own.
- **`bust_out`** — 21-day ramp to ~4.4x volume with ticket inflation, then a sharp break to
  ≤10% of baseline with a refund-rate spike. Detection is graded on catching the ramp.

`T_lag` is drawn per drift type inside the 30–90 day band: `bust_out` 30–55 (chargebacks
arrive faster), `third_party_layering` 45–90, `prohibited_category` 40–90.

## Defense-only

The generator produces the *behavioural consequences* of drift. It contains no evasion
logic, no threshold-probing, and no adversarial mode. There is deliberately no facility for
testing whether a merchant could avoid detection.
