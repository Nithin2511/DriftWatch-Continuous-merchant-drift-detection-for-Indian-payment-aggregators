# The three hardest questions, answered

These are the three questions most likely to end the interview badly. Written out with
real answers, including where the answer is "I haven't solved that."

---

## 1. "Your data is synthetic. You wrote the drift and then detected it. What did you actually prove?"

**The honest scope of the claim.** I proved the detector buys lead time against a stated
threat model. I did not prove it holds at 32.5 days on Razorpay's real book, and I won't
claim that.

**What stops it being circular.** The generator was written to be adversarial to the
detector, not convenient for it:

- Non-drifting merchants carry organic growth trends (positive and negative), weekday
  seasonality that differs by category, and a portfolio-wide festival surge.
- 17 of 176 non-drifters are **confounders** with genuine legitimate structural change —
  category pivots and viral growth spikes. They are expected to produce false positives,
  and 6 of the 9 held-out false positives are exactly these. They are reported, not hidden.
- Drift magnitude is scaled by a subtlety parameter; 25% of drifters are at 0.35–0.5.
- The critical check: `prohibited_category` drift has a **median volume ratio of 1.12**,
  which sits inside the non-drifter range (p90 = 1.21, max 1.64). Volume alone cannot
  separate it. That was verified before any detector was built.

**Where the design was changed by the data rather than the data by the design.** Bust-outs
were initially caught 0 out of 7 under a pure two-family corroboration rule. Diagnostics showed they cross the velocity family 13/13 at z≈5
and cross *nothing else* — because a volume ramp is what a bust-out physically is. The
options were to lower every other threshold until a second family fired by accident, or to
add a tiered rule branch. I added Branch B with a higher bar, a persistence requirement,
and a weaker recommended action. The data changed the rule; the rule did not change the data.

**What would falsify it.** Run the same pipeline on 6–12 months of real merchant history
using terminated/BRAM-flagged merchants as labels and the date of the first scheme notice
as `T_lag`. The calibration procedure is deliberately transferable: PSI and z-score
thresholds are canonical absolute values, and only `category_mismatch` uses a portfolio
quantile, which is computable from an unlabelled book. Nothing in the calibration needs
labels except the choice of FP budget.

**What actually transfers** is the methodology: lead time as the headline metric, the
dev/held-out discipline, peer-relative velocity, and the corroboration rule. That is the
contribution. The numbers are an existence proof that the methodology produces a usable
signal, not a performance claim.

---

## 2. "We shipped Vulcan in August and Bumblebee already screens merchants. Why do we need this?"

**They solve adjacent problems, and I'd say so before you do.**

- **Bumblebee** flags risky merchants at onboarding, in under 90 seconds. That is a day-1
  decision. DriftWatch is about day 40. A merchant that was genuinely clean at onboarding
  and mutated later is invisible to onboarding screening by construction.
- **Vulcan** is transaction-level and consumer-fraud-shaped. Its network-level capability
  spots a stolen card used across unrelated sellers — that is detecting bad *cardholders*.
  DriftWatch's unit of analysis is the merchant *entity* measured against its own declared
  profile over time. Opposite side of the table.
- **The output shape differs, and that is the regulatory point.** Vulcan produces a score.
  SMMP requires a documented investigation with a timestamp, the signals reviewed, and the
  basis for the decision. A score does not satisfy that; a case file does.

**The RBI hook is the strongest part of this argument.** The 2025 PA Directions impose a
positive obligation to monitor merchant transactions on an ongoing basis *for consistency
with the merchant's declared business profile*. That is a duty written almost exactly as a
product spec, and neither Bumblebee nor Vulcan is publicly positioned against it.

**Where I concede.** If Razorpay pointed Vulcan's feature store at this problem you would
almost certainly beat my detection numbers within a quarter — you have three trillion data
points and I have a synthetic generator. My claim is not that the model is better. It is
that the *framing* is missing: continuous entity-level monitoring, graded on lead time,
producing an audit artifact. That framing is what I would want to be hired to build.

**On Ballerine, before you raise it.** Ballerine is a Mastercard-certified MMSP doing
merchant monitoring well, and their existence is evidence the problem is worth money. Their
frame is card-scheme: BRAM, VIRP, MMSP. India's binding constraints are different — UPI
rails, CKYCR, FIU-IND and PMLA reporting, LEA settlement holds via CFCFRMS. This system is
built UPI-native: payer VPA populations, PSP handles, settlement accounts. There is no
TC40/TC15 anywhere in it.

---

## 3. "12.7% false-positive rate. At 10 million merchants that's over a million investigations. This is unusable."

**Correct, at that framing. Four things reduce it, and one of them I have not solved.**

**First, the rate is per-merchant over the full ~150-day observation window, not per-day.**
Nine false positives across 71 merchants over roughly five months. That is on the order of
one new false case per merchant every three years, which is a very different operational
picture from "12.7% of the book, today."

**Second, the FP budget is an input, not a property.** `calibrate()` takes `max_fp_rate` as
a parameter and the grid search respects it as a hard constraint. You set it from analyst
headcount and work backwards. Tightening it trades lead time, and the trade is visible in
the calibration trials the harness records.

**Third, the decision criterion is the break-even, not the rate.** The demo prints it:
given ₹12,000 per wrongly-flagged merchant and ₹850,000 per missed drift, the system stops
paying above roughly ₹13.2 lakh of cost per false positive — about 110x the assumed review
cost. The rate is only alarming if
you never price it. Both cost inputs are stated in `evaluate.py` and are the first thing I'd
want replaced with your real numbers.

**Fourth, 6 of the 9 false positives are confounders** — merchants with genuine structural
change, such as a category pivot. Those are arguably not waste: a merchant whose actual
business has moved away from its declared category needs MCC re-coding, which is itself an
RBI obligation. The tiered rule already separates `escalate` from `investigate`.

**What I have not solved.** None of the above makes 10M merchants tractable with a single
global threshold. What I would build next, in order: per-segment thresholds (category ×
tenure × volume band, since a 45-day-old F&B merchant and a 3-year-old SaaS merchant should
not share a bar); a reviewer feedback loop so dispositioned cases retrain the thresholds; and
a cheap pre-filter so the expensive signals only run on a candidate set. I did not build
these — they are in [CUT_LIST.md](CUT_LIST.md) with the reasoning. Claiming the FP problem
is solved at scale would be the least defensible thing I could say in this room.
