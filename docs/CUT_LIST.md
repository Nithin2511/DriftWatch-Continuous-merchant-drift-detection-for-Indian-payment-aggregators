# Cut list

What was cut, and why. Cutting from P2 first, then P1, never from P0 — as planned.

## Delivered (P0, complete end to end)

Synthetic generator with dual ground truth → four walk-forward signals → two-branch rule →
Gemini case-file synthesis → walk-forward lead-time evaluation on a held-out split → CLI
demo. All of it runs from `python run_all.py`: about 2.2 minutes of compute and 4 API calls.

## Delivered from P1

- **Network / shared-identifier signal.** Kept because it is the strongest signal for
  undisclosed third-party processing specifically, and it is cheap: an inverted index over
  payer VPAs plus a weekly graph refresh. It carries 7/7 of the held-out layering catches.

## Cut from P1

- **Web dashboard.** *Originally cut, later built.* The reasoning for cutting it still
  stands and is worth stating: a dashboard is presentation, and the credible thing to spend
  finite time on first was the evaluation harness. It was only built once the harness was
  done. It is a strict presentation layer — `export_frontend_data.py` generates its two data
  modules from `out/`, and the build refuses to run if the case files and the evaluation
  disagree, so the dashboard cannot drift from the numbers it claims to display. The CLI
  demo (`python -m driftwatch.demo`) remains the reference view and reads the same files.
- **Razorpay test-mode API / MCP wiring.** Cut deliberately, and this is the cut I would
  defend hardest. Wiring merchant and order objects through test mode would make the schema
  realistic, but the drift logic would still be layered on top by me — so it buys schema
  fidelity, not evidential strength, at meaningful integration cost. The honest trade was to
  spend that time on the confounder cohort and the separability check, which are what make
  the lead-time number mean something. Named as future work rather than quietly dropped.

## Cut from P2

- **True streaming simulation.** The walk-forward backtest is equivalent for measuring lead
  time and far easier to audit. Streaming is an engineering concern, not an evidential one.
- **Exotic signal types** beyond the core four.
- **Automated regulatory clause-citation mapping.** Cut on principle: I could not verify
  clause-level citations, so case files name the programs and duties that were verified and
  cite no clause numbers at all. Fabricating a clause number in a compliance artifact is
  worse than omitting it.

## Known gaps, not cut but not solved

- **Per-segment thresholds.** A single global threshold set is wrong at portfolio scale — a
  45-day-old F&B merchant and a 3-year-old SaaS merchant should not share a bar. Segmenting
  by category × tenure × volume band is the highest-value next increment.
- **Reviewer feedback loop.** Dispositioned cases should retrain thresholds. Nothing here
  closes that loop.
- **Stratified split implemented.** `prohibited_category` is now balanced across dev and
  held-out splits via stratified splitting ($n=5$ held-out, 4/5 caught @ 28.0d lead time).
