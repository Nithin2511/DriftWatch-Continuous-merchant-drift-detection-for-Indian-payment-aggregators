# 5-minute demo script

Lead with the number. Do not build up to it.

## 0:00–0:30 — The two clocks

> "A merchant clears KYC on day one and drifts by day forty. Since 24 July, Mastercard's
> scam-merchant rules give the acquirer **72 hours** to investigate once a warning signal
> appears. The evidence that proves drift — chargebacks, law-enforcement holds — arrives
> **30 to 90 days** later. Every monitoring system I could find waits for the evidence. That
> means it structurally cannot meet the clock."

## 0:30–1:00 — The number

Run `python -m driftwatch.demo`. Stop on the first panel.

> "**32.5 days of median lead time**, on a held-out split I scored exactly once. That's 32.5 days
> of warning before the lagging signal would have landed. Not AUC — days. If a model has
> great AUC but only fires when chargebacks are already flowing, it bought zero days and the
> chargebacks would have caught it anyway."

Then: 82.4% catch (14/17), 12.7% FP (9/71), 6 of 9 FPs are legitimate-change confounders.

## 1:00–1:45 — Why the data is a fair test (the prediction)

> "It's synthetic, and I'll tell you exactly what that does and doesn't prove."

Show the separability table from `DATA_PLAN.md`. Land the one line that matters:

> "`prohibited_category` drift has a median volume ratio of **1.12**. Non-drifters go to
> 1.21 at p90. It sits *inside* the noise. A volume detector cannot catch it — which is why
> the rule needs two independent signal families, not one loud feature."

Mention the portfolio-wide Diwali surge and the 17 confounders. Do **not** resolve the
`prohibited_category` claim here — leave it hanging. The next beat pays it off.

## 1:45–2:30 — The prediction, confirmed (the strongest thing in the project)

This beat is the one to protect if you run long. It is the only place where something was
predicted *before* the detector existed and then confirmed *after* it was built.

> "A risk engineer is going to ask where `descriptor` comes from in your schema. Fair
> question — item-level text is merchant-supplied, and across the long tail it's an order
> ID or nothing. So I removed that signal family entirely and recalibrated from scratch."

Run it, or show the table:

```bash
python run_all.py --ablate-content
```

| Drift type | Full | Content family removed |
|---|---|---|
| `third_party_layering` | 7/7 | 6/7 |
| `bust_out` | 3/5 | 3/5 |
| **`prohibited_category`** | **4/5** | **0/5** |

> "Two of the three threat models barely move. `prohibited_category` goes to **zero**.
>
> That's not a surprise — it's the prediction from ninety seconds ago. Before I wrote a
> single detector, the separability check said that class sits at a 1.12 volume ratio,
> inside the non-drifter range. Volume, timing and counterparty *cannot* see it. The
> ablation is that prediction being paid off. The signal I said was necessary turned out to
> be exactly the one that class depends on, and nothing else."

Then give the floor, because it is a strong number and it is honest:

> "Stripped of any dependence on merchant-supplied text, this still buys a median **36 days**
> on **9 of 17** held-out drifters at an 11.3% false-positive rate — using only amount,
> timing and counterparty identifiers, which every PA has for every transaction."

**Say the caveat before they spot it.** The median goes *up*, 32.5 to 36.0 days:

> "And before you ask why the median went up when the system got worse — that's
> survivorship, not improvement. The cases that still fire are the strongly corroborated
> ones, and those were always the ones that fired early. Fewer drifters caught; the
> survivors were the easy ones. Read the catch rate, not the median."

## 2:30–3:15 — One design decision, argued

> "Velocity is measured **peer-relative**. During Diwali everyone ramps. An absolute detector
> fires on the whole book and gets switched off in a week. So each merchant's growth is
> z-scored against the same-day cross-section of the entire portfolio. Everyone surges
> together, nobody's anomalous. One merchant surges against a flat book, that's a signal.
> That requires portfolio-wide same-day visibility — which is exactly what a PA has and a
> single merchant doesn't."

## 3:15–4:15 — The case file, and a false positive

Show the true positive: signals with numbers, ticket shift, volume shift, the rule that
combined them, the recommended action in the Directions' language.

> "The output is a case file, not a score. SMMP requires you to show when the trigger fired,
> what was reviewed, and the basis for the decision. A score doesn't satisfy that."

Then show the false positive **on purpose**:

> "This one's wrong. It's a merchant that legitimately pivoted category. A demo with no false
> positives isn't a demo, it's a sales pitch."

## 4:15–4:45 — Where the design changed because the data said so

> "Bust-outs were caught 0 out of 7 initially. Diagnostics showed they cross velocity 13/13
> at z≈5 and cross nothing else — because a volume ramp is what a bust-out *is*. I could have
> lowered every other threshold until a second family fired by accident. Instead I added a
> tiered rule branch with a higher bar, a five-day persistence requirement, and a weaker
> recommended action. The data changed the rule. The rule didn't change the data."

## 4:45–5:00 — The concession, said first

> "Ballerine does this well for card-scheme markets, and their existence proves the problem
> is worth money. Their frame is BRAM and VIRP. India's constraints are UPI rails, CKYCR,
> FIU-IND. There's no TC40 anywhere in this system. And I haven't solved false positives at
> ten-million-merchant scale — per-segment thresholds are the next thing I'd build."

Stop there. Do not fill the remaining seconds.
