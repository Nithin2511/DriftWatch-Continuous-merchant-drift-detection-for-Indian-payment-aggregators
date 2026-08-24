"""
Documentation-consistency tests.

Every numeric inconsistency found in this project so far was found by a manual audit: a
headline that disagreed with the evaluation, a case-file count that outlived the run that
produced it, a call count that could not have happened under the API's own rate limit.
Manual audits are not durable. They are correct on the day they are run and stale after the
next edit, and the next edit is always coming.

These tests make that class of error impossible rather than merely absent. Every number
quoted in README.md and docs/EVALUATION.md is parsed back out of the prose and asserted
against `out/evaluation.json`, which is the only thing the pipeline actually produces. If a
result changes and a document does not follow, the suite fails and names the file, the
value the document claims, and the value the pipeline computed.

WHAT THESE TESTS DO NOT DO
--------------------------
They do not check that the numbers are *right*. A miscalibrated detector that reports its
miscalibration consistently across every surface passes cleanly. Correctness of the
evaluation is the job of test_invariants.py (ground-truth quarantine, no lookahead, the
trigger rule) and of the split discipline in docs/EVALUATION.md. These tests check only
that the repo tells one story about whatever numbers it has.

They also only cover surfaces that are hand-written. The dashboard is generated from
`out/` by export_frontend_data.py, which already refuses to export when case files and the
evaluation disagree, so it cannot drift independently.

Run:  python -m pytest tests -q
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVAL_JSON = ROOT / "out" / "evaluation.json"

CASES_DIR = ROOT / "out" / "cases"
TRIGGERS = ROOT / "out" / "held_out_triggers.json"

# out/evaluation.json is committed, so everything asserting doc-vs-artifact numbers runs
# everywhere including CI.
pytestmark = pytest.mark.skipif(
    not EVAL_JSON.exists(),
    reason="out/evaluation.json missing; it is committed, so this should never trigger",
)

# The case files and trigger list are NOT committed -- they are bulky and regenerable.
# The handful of tests that read them therefore need a local pipeline run. They are
# marked separately so the skip is attributable rather than lumped in with the rest.
needs_full_artifact = pytest.mark.skipif(
    not CASES_DIR.exists() or not TRIGGERS.exists(),
    reason="needs out/cases/ and out/held_out_triggers.json; run `python run_all.py` locally",
)


# --------------------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def ev() -> dict:
    return json.loads(EVAL_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def evaluation_md() -> str:
    return (ROOT / "docs" / "EVALUATION.md").read_text(encoding="utf-8")


# ----------------------------------------------------------------------------- helpers

def _fail(doc: str, label: str, claimed, computed) -> str:
    return (f"\n  {doc} claims {label} = {claimed!r}"
            f"\n  out/evaluation.json computes {computed!r}"
            f"\n  -> a result changed and {doc} was not updated."
            f"\n     Re-run the pipeline and correct the document; do not edit the JSON.")


def _find(pattern: str, text: str, doc: str, label: str) -> re.Match:
    m = re.search(pattern, text)
    assert m, (f"\n  Could not locate {label} in {doc} using /{pattern}/."
               f"\n  Either the number was removed or the wording changed. If the wording"
               f"\n  changed, update the pattern in tests/test_docs_consistency.py so the"
               f"\n  claim stays covered -- do not delete the assertion.")
    return m


def _pct(x: float) -> float:
    return round(100 * x, 1)


# ------------------------------------------------------------------ README: headline block

def test_readme_headline_catch_count_and_rate(ev, readme):
    h = ev["held_out"]
    m = _find(r"Caught before lagging evidence (\d+)/(\d+)\s+([\d.]+)%",
              readme, "README.md", "held-out catch line")
    caught, total, rate = int(m.group(1)), int(m.group(2)), float(m.group(3))
    assert caught == h["caught"], _fail("README.md", "held-out caught", caught, h["caught"])
    assert total == h["n_drifters"], _fail("README.md", "held-out drifters", total, h["n_drifters"])
    assert rate == _pct(h["catch_rate"]), _fail("README.md", "catch rate %", rate, _pct(h["catch_rate"]))


def test_readme_headline_actionable_lead(ev, readme):
    """The `lead > 7 days` row must track n_actionable, not be typed once and forgotten."""
    h = ev["held_out"]
    m = _find(r"\.\.\. with lead > 7 days\s+(\d+)/(\d+)\s+([\d.]+)%",
              readme, "README.md", "actionable-lead line")
    n, total, rate = int(m.group(1)), int(m.group(2)), float(m.group(3))
    assert n == h["n_actionable"], _fail("README.md", "lead>7d count", n, h["n_actionable"])
    assert total == h["n_drifters"], _fail("README.md", "lead>7d denominator", total, h["n_drifters"])
    assert rate == _pct(h["actionable_rate_of_drifters"]), _fail(
        "README.md", "lead>7d rate %", rate, _pct(h["actionable_rate_of_drifters"]))


def test_readme_headline_false_positives(ev, readme):
    h = ev["held_out"]
    m = _find(r"False-positive rate\s+(\d+)/(\d+)\s+([\d.]+)%",
              readme, "README.md", "held-out FP line")
    n, total, rate = int(m.group(1)), int(m.group(2)), float(m.group(3))
    assert n == h["n_false_positives"], _fail("README.md", "FP count", n, h["n_false_positives"])
    assert total == h["n_non_drifters"], _fail("README.md", "non-drifters", total, h["n_non_drifters"])
    assert rate == _pct(h["false_positive_rate"]), _fail(
        "README.md", "FP rate %", rate, _pct(h["false_positive_rate"]))


def test_readme_headline_median_lead_and_iqr(ev, readme):
    h = ev["held_out"]
    m = _find(r"Median LEAD TIME BOUGHT\s+([\d.]+) days\s+\(IQR (\d+)-(\d+), range (\d+)-(\d+)\)",
              readme, "README.md", "median lead line")
    median, p25, p75, lo, hi = (float(m.group(1)), int(m.group(2)), int(m.group(3)),
                                int(m.group(4)), int(m.group(5)))
    assert median == h["median_lead_days"], _fail(
        "README.md", "median lead", median, h["median_lead_days"])
    assert p25 == round(h["p25_lead_days"]), _fail("README.md", "IQR p25", p25, h["p25_lead_days"])
    assert p75 == round(h["p75_lead_days"]), _fail("README.md", "IQR p75", p75, h["p75_lead_days"])
    assert lo == h["min_lead_days"], _fail("README.md", "min lead", lo, h["min_lead_days"])
    assert hi == h["max_lead_days"], _fail("README.md", "max lead", hi, h["max_lead_days"])


def test_readme_confounder_count(ev, readme):
    h = ev["held_out"]
    m = _find(r"\((\d+) of the (\d+) are legitimate-change confounders\)",
              readme, "README.md", "confounder line")
    conf, total = int(m.group(1)), int(m.group(2))
    assert conf == h["n_fp_confounders"], _fail(
        "README.md", "FP confounders", conf, h["n_fp_confounders"])
    assert total == h["n_false_positives"], _fail(
        "README.md", "FP total", total, h["n_false_positives"])


def test_readme_development_split(ev, readme):
    d = ev["development"]
    m = _find(r"Development split: (\d+)/(\d+) caught \(([\d.]+)%\), median lead ([\d.]+) d, "
              r"FP ([\d.]+)% \((\d+)/(\d+)\)",
              readme, "README.md", "development split line")
    caught, total, rate, lead, fpr, fpn, fpd = (
        int(m.group(1)), int(m.group(2)), float(m.group(3)), float(m.group(4)),
        float(m.group(5)), int(m.group(6)), int(m.group(7)))
    assert caught == d["caught"], _fail("README.md", "dev caught", caught, d["caught"])
    assert total == d["n_drifters"], _fail("README.md", "dev drifters", total, d["n_drifters"])
    assert rate == _pct(d["catch_rate"]), _fail("README.md", "dev catch %", rate, _pct(d["catch_rate"]))
    assert lead == d["median_lead_days"], _fail(
        "README.md", "dev median lead", lead, d["median_lead_days"])
    assert fpr == _pct(d["false_positive_rate"]), _fail(
        "README.md", "dev FP %", fpr, _pct(d["false_positive_rate"]))
    assert fpn == d["n_false_positives"], _fail("README.md", "dev FP count", fpn, d["n_false_positives"])
    assert fpd == d["n_non_drifters"], _fail("README.md", "dev non-drifters", fpd, d["n_non_drifters"])


# ------------------------------------------------------- README: per-drift-type table

DRIFT_TYPES = ["third_party_layering", "bust_out", "prohibited_category"]


@pytest.mark.parametrize("dtype", DRIFT_TYPES)
def test_readme_per_drift_type_row(ev, readme, dtype):
    want = ev["held_out_by_type"][dtype]
    m = _find(rf"\| `{dtype}` \| (\d+)/(\d+) \| ([\d.]+) d \|",
              readme, "README.md", f"{dtype} row")
    caught, n, lead = int(m.group(1)), int(m.group(2)), float(m.group(3))
    assert caught == want["caught"], _fail("README.md", f"{dtype} caught", caught, want["caught"])
    assert n == want["n"], _fail("README.md", f"{dtype} n", n, want["n"])
    assert lead == want["median_lead"], _fail(
        "README.md", f"{dtype} median lead", lead, want["median_lead"])


# ------------------------------------------------------------ EVALUATION.md: results table

def test_evaluation_declares_the_headline(ev, evaluation_md):
    """EVALUATION.md must name one configuration as the result, matching the JSON."""
    h = ev["held_out"]
    m = _find(r"the system's result: ([\d.]+)% catch, ([\d.]+)% false positives, "
              r"([\d.]+)-day median lead",
              evaluation_md, "docs/EVALUATION.md", "headline declaration")
    catch, fp, lead = float(m.group(1)), float(m.group(2)), float(m.group(3))
    assert catch == _pct(h["catch_rate"]), _fail(
        "docs/EVALUATION.md", "declared catch %", catch, _pct(h["catch_rate"]))
    assert fp == _pct(h["false_positive_rate"]), _fail(
        "docs/EVALUATION.md", "declared FP %", fp, _pct(h["false_positive_rate"]))
    assert lead == h["median_lead_days"], _fail(
        "docs/EVALUATION.md", "declared median lead", lead, h["median_lead_days"])
    assert ev["variant"] == "full" and ev["fp_budget"] == "point", (
        f"\n  out/evaluation.json is variant={ev['variant']!r} fp_budget={ev['fp_budget']!r},"
        f"\n  but the docs present the full/point-estimate run as the headline."
        f"\n  Either out/ was overwritten by an ablation or sensitivity run, or the"
        f"\n  headline configuration changed and the docs were not updated.")


def test_evaluation_results_table_caught_row(ev, evaluation_md):
    d, h = ev["development"], ev["held_out"]
    m = _find(r"\| Caught before `T_lag` \| (\d+) \(([\d.]+)%\) \| \*\*(\d+) \(([\d.]+)%\)\*\* \|",
              evaluation_md, "docs/EVALUATION.md", "Results caught row")
    dev_c, dev_r, ho_c, ho_r = (int(m.group(1)), float(m.group(2)),
                                int(m.group(3)), float(m.group(4)))
    assert dev_c == d["caught"], _fail("docs/EVALUATION.md", "dev caught", dev_c, d["caught"])
    assert dev_r == _pct(d["catch_rate"]), _fail(
        "docs/EVALUATION.md", "dev catch %", dev_r, _pct(d["catch_rate"]))
    assert ho_c == h["caught"], _fail("docs/EVALUATION.md", "held-out caught", ho_c, h["caught"])
    assert ho_r == _pct(h["catch_rate"]), _fail(
        "docs/EVALUATION.md", "held-out catch %", ho_r, _pct(h["catch_rate"]))


def test_evaluation_results_table_median_lead_row(ev, evaluation_md):
    d, h = ev["development"], ev["held_out"]
    m = _find(r"\| Median lead \| ([\d.]+) d \| \*\*([\d.]+) d\*\* \|",
              evaluation_md, "docs/EVALUATION.md", "Results median-lead row")
    dev_lead, ho_lead = float(m.group(1)), float(m.group(2))
    assert dev_lead == d["median_lead_days"], _fail(
        "docs/EVALUATION.md", "dev median lead", dev_lead, d["median_lead_days"])
    assert ho_lead == h["median_lead_days"], _fail(
        "docs/EVALUATION.md", "held-out median lead", ho_lead, h["median_lead_days"])


def test_evaluation_results_table_fp_row(ev, evaluation_md):
    d, h = ev["development"], ev["held_out"]
    m = _find(r"\| False-positive rate \| ([\d.]+)% \((\d+)/(\d+)\) \| "
              r"\*\*([\d.]+)% \((\d+)/(\d+)\)\*\* \|",
              evaluation_md, "docs/EVALUATION.md", "Results FP row")
    dev_r, dev_n, dev_d = float(m.group(1)), int(m.group(2)), int(m.group(3))
    ho_r, ho_n, ho_d = float(m.group(4)), int(m.group(5)), int(m.group(6))
    assert dev_r == _pct(d["false_positive_rate"]), _fail(
        "docs/EVALUATION.md", "dev FP %", dev_r, _pct(d["false_positive_rate"]))
    assert (dev_n, dev_d) == (d["n_false_positives"], d["n_non_drifters"]), _fail(
        "docs/EVALUATION.md", "dev FP fraction", f"{dev_n}/{dev_d}",
        f"{d['n_false_positives']}/{d['n_non_drifters']}")
    assert ho_r == _pct(h["false_positive_rate"]), _fail(
        "docs/EVALUATION.md", "held-out FP %", ho_r, _pct(h["false_positive_rate"]))
    assert (ho_n, ho_d) == (h["n_false_positives"], h["n_non_drifters"]), _fail(
        "docs/EVALUATION.md", "held-out FP fraction", f"{ho_n}/{ho_d}",
        f"{h['n_false_positives']}/{h['n_non_drifters']}")


def test_evaluation_actionable_lead_row(ev, evaluation_md):
    h = ev["held_out"]
    m = _find(r"\| Caught with lead > 7 d \| (\d+)/(\d+) \| \*\*(\d+)/(\d+) — ([\d.]+)%",
              evaluation_md, "docs/EVALUATION.md", "Results lead>7d row")
    ho_n, ho_d, ho_r = int(m.group(3)), int(m.group(4)), float(m.group(5))
    assert ho_n == h["n_actionable"], _fail(
        "docs/EVALUATION.md", "held-out lead>7d", ho_n, h["n_actionable"])
    assert ho_d == h["n_drifters"], _fail(
        "docs/EVALUATION.md", "held-out drifters", ho_d, h["n_drifters"])
    assert ho_r == _pct(h["actionable_rate_of_drifters"]), _fail(
        "docs/EVALUATION.md", "held-out lead>7d %", ho_r, _pct(h["actionable_rate_of_drifters"]))


@pytest.mark.parametrize("dtype", DRIFT_TYPES)
def test_evaluation_per_drift_type_row(ev, evaluation_md, dtype):
    want = ev["held_out_by_type"][dtype]
    m = _find(rf"\| `{dtype}` \| (\d+)/(\d+) \| ([\d.]+) d \|",
              evaluation_md, "docs/EVALUATION.md", f"{dtype} row")
    caught, n, lead = int(m.group(1)), int(m.group(2)), float(m.group(3))
    assert caught == want["caught"], _fail(
        "docs/EVALUATION.md", f"{dtype} caught", caught, want["caught"])
    assert n == want["n"], _fail("docs/EVALUATION.md", f"{dtype} n", n, want["n"])
    assert lead == want["median_lead"], _fail(
        "docs/EVALUATION.md", f"{dtype} median lead", lead, want["median_lead"])


# ------------------------------------------------------------------ cross-surface agreement

@needs_full_artifact
def test_narrative_provenance_matches_the_case_files(readme, evaluation_md):
    """The 'N of M Gemini narratives' claim must match what is actually on disk."""
    cases = sorted((ROOT / "out" / "cases").glob("DW-*.json"))
    modes = [json.loads(p.read_text(encoding="utf-8"))["provenance"]["narrative_mode"]
             for p in cases]
    gemini, total = sum(1 for m in modes if m == "gemini"), len(modes)

    for doc, text in (("README.md", readme), ("docs/EVALUATION.md", evaluation_md)):
        m = _find(r"(\d+) of (\d+) (?:case files carry a Gemini narrative|Gemini)",
                  text, doc, "narrative provenance claim")
        claimed_g, claimed_t = int(m.group(1)), int(m.group(2))
        assert (claimed_g, claimed_t) == (gemini, total), _fail(
            doc, "Gemini narratives", f"{claimed_g} of {claimed_t}", f"{gemini} of {total}")


@needs_full_artifact
def test_case_file_count_matches_triggers(ev):
    """Guards the stale-case-file failure mode: ids embed the trigger day, so a
    recalibration that moves a trigger writes a new file and orphans the old one."""
    triggers = json.loads((ROOT / "out" / "held_out_triggers.json").read_text(encoding="utf-8"))
    cases = sorted((ROOT / "out" / "cases").glob("DW-*.json"))
    assert len(cases) == len(triggers), (
        f"\n  out/cases/ holds {len(cases)} files but this run produced {len(triggers)}"
        f" triggers."
        f"\n  Stale case files from an earlier calibration are still on disk."
        f"\n  Re-run `python run_all.py`; write_cases() clears DW-*.json first.")
    expected = ev["held_out"]["caught"] + ev["held_out"]["n_false_positives"]
    assert len(cases) == expected, _fail(
        "out/cases/", "case count", len(cases), expected)
