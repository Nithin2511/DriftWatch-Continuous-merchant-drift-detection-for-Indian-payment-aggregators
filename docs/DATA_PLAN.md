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
