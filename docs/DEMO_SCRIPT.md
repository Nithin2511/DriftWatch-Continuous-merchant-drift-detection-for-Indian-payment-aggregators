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

## 1:00–2:00 — Why the data is a fair test

> "It's synthetic, and I'll tell you exactly what that does and doesn't prove."

Show the separability table from `DATA_PLAN.md`. Land the one line that matters:

> "`prohibited_category` drift has a median volume ratio of **1.12**. Non-drifters go to
> 1.21 at p90. It sits *inside* the noise. A volume detector cannot catch it — which is why
> the rule needs two independent signal families, not one loud feature."

Mention the portfolio-wide Diwali surge and the 17 confounders.

## 2:00–3:00 — One design decision, argued

> "Velocity is measured **peer-relative**. During Diwali everyone ramps. An absolute detector
> fires on the whole book and gets switched off in a week. So each merchant's growth is
> z-scored against the same-day cross-section of the entire portfolio. Everyone surges
> together, nobody's anomalous. One merchant surges against a flat book, that's a signal.
> That requires portfolio-wide same-day visibility — which is exactly what a PA has and a
> single merchant doesn't."

## 3:00–4:00 — The case file, and a false positive

Show the true positive: signals with numbers, ticket shift, volume shift, the rule that
combined them, the recommended action in the Directions' language.

> "The output is a case file, not a score. SMMP requires you to show when the trigger fired,
> what was reviewed, and the basis for the decision. A score doesn't satisfy that."

Then show the false positive **on purpose**:

> "This one's wrong. It's a merchant that legitimately pivoted category. A demo with no false
> positives isn't a demo, it's a sales pitch."

## 4:00–4:40 — Where the design changed because the data said so

> "Bust-outs were caught 0 out of 7 initially. Diagnostics showed they cross velocity 13/13
> at z≈5 and cross nothing else — because a volume ramp is what a bust-out *is*. I could have
> lowered every other threshold until a second family fired by accident. Instead I added a
> tiered rule branch with a higher bar, a five-day persistence requirement, and a weaker
> recommended action. The data changed the rule. The rule didn't change the data."

## 4:40–5:00 — The concession, said first

> "Ballerine does this well for card-scheme markets, and their existence proves the problem
> is worth money. Their frame is BRAM and VIRP. India's constraints are UPI rails, CKYCR,
> FIU-IND. There's no TC40 anywhere in this system. And I haven't solved false positives at
> ten-million-merchant scale — per-segment thresholds are the next thing I'd build."

Stop there. Do not fill the remaining seconds.
