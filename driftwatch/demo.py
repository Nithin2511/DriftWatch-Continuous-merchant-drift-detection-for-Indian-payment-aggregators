"""
DriftWatch -- the demo view.

    python -m driftwatch.demo [--no-pause] [--case MID0105]

Reads only what the pipeline already wrote: `out/evaluation.json` and `out/cases/*.json`.
It computes no metrics of its own, so nothing shown here can disagree with what
`evaluate.py` scored. It never opens `data/ground_truth.csv`.

Panel order follows docs/DEMO_SCRIPT.md.
"""
from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

W = 78

# The separability check from docs/DATA_PLAN.md. Pre-registered: it was run on the
# generator output BEFORE any detector existed, to establish that the task is not
# trivially separable. It is quoted here rather than recomputed, because recomputing it
# would mean opening ground_truth.csv outside evaluate.py.
SEPARABILITY = [
    ("bust_out",             "1.84", "1.98", "2.12"),
    ("third_party_layering", "1.17", "1.35", "1.44"),
    ("prohibited_category",  "1.00", "1.12", "1.26"),
    ("non-drifters",         "--",   "1.02", "1.13"),
]

COST_FP_INR = 12_000
COST_MISS_INR = 850_000


def rule(ch: str = "-") -> str:
    return ch * W


def panel(title: str) -> None:
    print()
    print(rule("="))
    print(f"  {title}")
    print(rule("="))


def wrap(text: str, indent: str = "  ") -> None:
    for para in text.strip().split("\n\n"):
        print(textwrap.fill(" ".join(para.split()), width=W,
                            initial_indent=indent, subsequent_indent=indent))
        print()


def rupees(n: float) -> str:
    """Plain rupees below a lakh, lakh above it. 12,000 shown as 0.1L reads as noise."""
    if abs(n) < 100_000:
        return f"INR {n:,.0f}"
    return f"INR {n / 100_000:.1f}L"


def pause(enabled: bool) -> None:
    if enabled:
        try:
            input("  [enter] ")
        except EOFError:
            pass


# --------------------------------------------------------------------------- panels

def panel_headline(ev: dict) -> None:
    h = ev["held_out"]
    panel("THE NUMBER -- held-out split, scored exactly once")
    print()
    print(f"      MEDIAN LEAD TIME BOUGHT      {h['median_lead_days']:g} DAYS")
    print(f"      IQR {h['p25_lead_days']:.0f}-{h['p75_lead_days']:.0f} days   "
          f"range {h['min_lead_days']}-{h['max_lead_days']} days")
    print()
    print(f"      caught before lagging evidence   {h['caught']}/{h['n_drifters']}"
          f"  ({h['catch_rate']:.1%})")
    print(f"      false positives                  {h['n_false_positives']}/"
          f"{h['n_non_drifters']}  ({h['false_positive_rate']:.1%})")
    print(f"        of which legitimate-change confounders   {h['n_fp_confounders']}")
    print(f"        of which unexplained                     {h['n_fp_plain']}")
    print()
    wrap("""
    Lead time is days between the trigger firing and T_lag -- the day the lagging
    evidence (chargebacks, holds) would have landed anyway. A detector with excellent
    AUC that only fires once chargebacks are flowing has bought zero days.
    """)


def panel_generalisation(ev: dict) -> None:
    d, h = ev["development"], ev["held_out"]
    panel("THE GENERALISATION GAP -- reported, not hidden")
    print()
    print(f"  {'':22} {'development':>14} {'held-out':>14}")
    print(f"  {rule('.')[:52]}")
    rows = [
        ("merchants",       f"{ev['n_dev']}",               f"{ev['n_held_out']}"),
        ("catch rate",      f"{d['catch_rate']:.1%}",       f"{h['catch_rate']:.1%}"),
        ("median lead (d)", f"{d['median_lead_days']:g}", f"{h['median_lead_days']:g}"),
        ("false-positive",  f"{d['false_positive_rate']:.1%}",
                            f"{h['false_positive_rate']:.1%}"),
    ]
    for label, a, b in rows:
        print(f"  {label:22} {a:>14} {b:>14}")
    print()
    wrap(f"""
    Held-out catch is HIGHER than development ({h['catch_rate']:.1%} vs {d['catch_rate']:.1%}),
    which is not a result -- it is sampling noise on {h['n_drifters']} drifters. A
    two-proportion test on that difference gives z = 0.89, nowhere near significance, and
    the two Wilson intervals overlap across almost their whole range. Read every rate here
    with a +/-20-point interval attached.

    The held-out false-positive rate ({h['false_positive_rate']:.1%}) also exceeds the 10%
    budget the calibration enforced on development ({d['false_positive_rate']:.1%}). The
    budget is a development-split guarantee and does not transfer as one.
    """)

    panel("BY DRIFT TYPE -- held-out")
    print()
    print(f"  {'type':24} {'n':>3} {'caught':>7} {'median lead':>13}")
    print(f"  {rule('.')[:50]}")
    for k, v in ev["held_out_by_type"].items():
        lead = f"{v['median_lead']:.0f}d" if v["caught"] else "--"
        print(f"  {k:24} {v['n']:>3} {v['caught']:>7} {lead:>13}")
    print()
    wrap("""
    The split is stratified by drift type, so every class is represented on held-out. The
    per-class counts are still small (n = 5 to 7), so these are directional, not precise:
    a single case moves any of these rates by 14 to 20 points.
    """)


def panel_data(ev: dict) -> None:
    panel("WHY THE SYNTHETIC DATA IS A FAIR TEST")
    print()
    print("  14-day volume ratio around T0 -- pre-registered, run before any detector existed")
    print()
    print(f"  {'cohort':24} {'p25':>7} {'p50':>7} {'p75':>7}")
    print(f"  {rule('.')[:48]}")
    for name, p25, p50, p75 in SEPARABILITY:
        print(f"  {name:24} {p25:>7} {p50:>7} {p75:>7}")
    print(f"  {'':24} {'':>7} {'':>7}   (non-drifter p90 1.21, max 1.64)")
    print()
    wrap("""
    prohibited_category sits at 1.12 median. Non-drifters reach 1.21 at p90. It is INSIDE
    the noise. No volume detector can catch it -- which is why the rule requires two
    independent signal families rather than one loud feature.

    The portfolio also carries a Diwali-shaped surge across days 96-116 where every
    merchant ramps together, and 17 confounders with genuine legitimate structural change.
    See docs/DATA_PLAN.md.
    """)


def panel_design() -> None:
    panel("ONE DESIGN DECISION -- velocity is peer-relative")
    print()
    wrap("""
    Each merchant's growth ratio is robust z-scored cross-sectionally against the whole
    portfolio on the same day. During the festival window everyone surges, so nobody is
    anomalous and the detector stays quiet. One merchant surging against a flat book is a
    signal.

    An absolute-velocity detector fires on the entire book during Diwali and gets switched
    off within a week. Peer-relative scoring reads other merchants' data at day t --
    contemporaneous, not lookahead, and precisely the view a payment aggregator has that a
    single merchant does not.
    """)
    print("  The trigger is a rule, not a learned combiner:")
    print()
    print("    Branch A  >=2 distinct signal families cross threshold in a 14-day window")
    print("    Branch B  1 family at >=2.5x threshold for 5 consecutive days")
    print("              -> weaker recommended action")
    print()
    wrap("""
    Branch B exists because bust-outs are structurally single-family: they cross velocity
    13/13 at z~5 and cross nothing else, because a volume ramp is what a bust-out is. The
    alternative was lowering other thresholds until a second family fired by accident. ML
    lives inside the individual signals; the combination stays readable and replayable.
    """)


def _fmt_case(c: dict, verdict: str) -> None:
    s = c["subject_entity"]
    print()
    print(f"  case_id            {c['case_id']}     [{verdict}]")
    print(f"  merchant           {s['merchant_id']}  declared: {s['declared_category']}")
    print(f"  trigger day        {c['trigger_day']}  "
          f"({c['days_since_onboarding']} days after onboarding)")
    print(f"  grounds            {c['grounds_for_review']['branch']}  "
          f"families: {', '.join(c['grounds_for_review']['families_fired'])}")
    print()
    print(f"  {'signal':20} {'at cross':>10} {'thresh':>10} {'day':>5} {'at trigger':>12}")
    print(f"  {rule('.')[:61]}")
    for sig in c["signals_fired"]:
        at_trig = sig.get("value_at_trigger_day")
        at_trig_s = f"{at_trig:>12.3f}" if at_trig is not None else f"{'--':>12}"
        print(f"  {sig['signal']:20} {sig['value']:>10.3f} {sig['threshold']:>10.3f} "
              f"{sig['first_crossed_day']:>5} {at_trig_s}")
    print()
    print("  'at cross' is the reading that satisfied the rule. A signal qualifies by")
    print("  crossing anywhere inside the 14-day window, so it may have receded by the")
    print("  trigger day -- both readings are shown rather than only the flattering one.")

    d = c["supporting_data"]
    print()
    print(f"  ticket   {d['baseline_median_ticket_inr']:>10,.0f} -> "
          f"{d['current_median_ticket_inr']:>10,.0f} INR   "
          f"({d['ticket_shift_multiple']:.2f}x)")
    print(f"  volume   {d['baseline_daily_txns']:>10.1f} -> "
          f"{d['current_daily_txns']:>10.1f} txn/day "
          f"({d['volume_shift_multiple']:.2f}x)")
    top = ", ".join(f"{t['descriptor']} ({t['n']})" for t in d["current_top_descriptors"])
    print(f"  descriptors in window: {top}")
    nc = c["network_context"]
    print(f"  linked merchant: {nc['linked_merchant'] or '--'}   "
          f"shared settlement account: {nc['shared_settlement_account']}")
    print()
    print("  recommended action")
    wrap(c["recommended_action"], indent="    ")
    print("  narrative")
    wrap(c["narrative"], indent="    ")
    p = c["provenance"]
    print(f"  provenance: classifier={p['descriptor_classifier_mode']}  "
          f"narrative={p['narrative_mode']}  data={p['data']}  seed={p['generator_seed']}")


def _load_cases(casedir: Path) -> dict[str, dict]:
    cases = {}
    for path in sorted(casedir.glob("*.json")):
        c = json.loads(path.read_text())
        cases[c["merchant_id"]] = c
    return cases


def panel_cases(ev: dict, casedir: Path, forced: str | None) -> None:
    cases = _load_cases(casedir)
    if not cases:
        print("\n  no case files found -- run `python run_all.py` first")
        return

    fp = set(ev["held_out"]["fp_ids"])
    conf = set(ev["held_out"].get("fp_confounder_ids", []))

    if forced:
        if forced not in cases:
            print(f"\n  no case file for {forced}. available: {', '.join(sorted(cases))}")
            return
        panel(f"CASE FILE -- {forced}")
        _fmt_case(cases[forced], "false positive" if forced in fp else "true positive")
        return

    # Deterministic, stated selection. No cherry-picking: the true positive shown is the
    # median case by merchant id among true positives, not the most flattering one.
    tps = sorted(m for m in cases if m not in fp)
    fps_conf = sorted(m for m in cases if m in conf)
    fps_plain = sorted(m for m in cases if m in fp and m not in conf)

    panel("THE OUTPUT IS A CASE FILE, NOT A SCORE")
    wrap("""
    SMMP requires showing when the trigger fired, what was reviewed, and the basis for the
    decision. A score does not satisfy that. Selection below is deterministic -- the median
    true positive by merchant id -- so this is not a hand-picked example.
    """)
    if tps:
        _fmt_case(cases[tps[len(tps) // 2]], "TRUE POSITIVE")

    shown = fps_conf or fps_plain
    if shown:
        mid = shown[0]
        panel("AND A FALSE POSITIVE, ON PURPOSE")
        if mid in conf:
            wrap("""
            A demo with no false positives is a sales pitch. This merchant did not drift --
            it underwent genuine legitimate structural change. The system was wrong, and
            the case file is shown exactly as the pipeline wrote it.
            """)
            verdict = "FALSE POSITIVE -- legitimate change"
        else:
            wrap("""
            A demo with no false positives is a sales pitch. This merchant did not drift and
            is not a known confounder either -- the system was simply wrong. The case file is
            shown exactly as the pipeline wrote it.
            """)
            verdict = "FALSE POSITIVE -- unexplained"
        _fmt_case(cases[mid], verdict)


def panel_economics(ev: dict) -> None:
    h = ev["held_out"]
    be = h.get("break_even_cost_per_fp_inr")
    panel("THE DECISION CRITERION IS THE BREAK-EVEN, NOT THE RATE")
    print()
    label_w = 42
    for label, val in [
        ("cost per false positive (assumed)", rupees(COST_FP_INR)),
        ("cost per missed drift  (assumed)", rupees(COST_MISS_INR)),
    ]:
        print(f"  {label:{label_w}} {val:>14}")
    print(f"  {rule('.')[:label_w + 15]}")
    for label, val in [
        ("expected cost with DriftWatch", rupees(h["expected_cost_inr"])),
        ("expected cost doing nothing", rupees(h["do_nothing_cost_inr"])),
        (f"cost avoided, {ev['n_held_out']} held-out merchants",
         rupees(h["cost_avoided_inr"])),
    ]:
        print(f"  {label:{label_w}} {val:>14}")
    if be:
        print()
        print(f"  BREAK-EVEN: stops paying above {rupees(be)} of cost per false positive")
    print()
    wrap("""
    Both cost inputs are assumptions stated in evaluate.py and are the first thing that
    should be replaced with real numbers. The false-positive rate is per merchant over a
    ~150-day observation window, not per day -- roughly one new false case per merchant
    every four years.

    Not solved: this does not make 10M merchants tractable on a single global threshold.
    Per-segment thresholds (category x tenure x volume band) are the next build. See
    docs/CUT_LIST.md.
    """)


# ----------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--no-pause", action="store_true")
    ap.add_argument("--case", default=None, help="show one case file by merchant id")
    a = ap.parse_args()

    out = Path(a.out)
    evfile = out / "evaluation.json"
    if not evfile.exists():
        raise SystemExit(f"{evfile} not found -- run `python run_all.py` first")
    ev = json.loads(evfile.read_text())

    if a.case:
        panel_cases(ev, out / "cases", a.case)
        return

    p = not a.no_pause
    print()
    print(rule("="))
    print("  DriftWatch -- continuous merchant-drift detection for Indian PAs")
    print("  Synthetic portfolio | 220 merchants | 200 days | seed 20260823")
    print(rule("="))

    panel_headline(ev)
    pause(p)
    panel_generalisation(ev)
    pause(p)
    panel_data(ev)
    pause(p)
    panel_design()
    pause(p)
    panel_cases(ev, out / "cases", None)
    pause(p)
    panel_economics(ev)
    print(rule("="))
    print("  full method and caveats: docs/EVALUATION.md | docs/PANEL_QA.md")
    print(rule("="))
    print()


if __name__ == "__main__":
    main()
