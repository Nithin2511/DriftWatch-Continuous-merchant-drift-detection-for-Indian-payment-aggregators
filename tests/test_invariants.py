"""
Invariant tests.

These do not test that DriftWatch scores well. They test the properties that make the
score *believable*, which are the properties a reviewer would try to break:

  - ground truth is quarantined inside evaluate.py
  - signals are walk-forward (no lookahead)
  - the trigger is a readable rule, not a fitted combiner
  - distribution thresholds are canonical constants, not portfolio quantiles
  - the LLM is never asked for a verdict
  - fallback mode is always labelled, and a cached fallback never suppresses a real call

Run with:  python -m pytest tests -q
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from driftwatch import llm, signals, trigger

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "driftwatch"


# --------------------------------------------------------------- ground-truth quarantine

def _source(name: str) -> str:
    return (PKG / name).read_text(encoding="utf-8")


def test_ground_truth_is_read_only_by_evaluate():
    """No component except evaluate.py may reference the label file.

    The lead-time claim is worthless if a signal, the trigger, or the case-file writer
    can see T0/T_lag. This is a static check over the package source so it fails at
    review time rather than at interview time.
    """
    offenders = []
    for path in sorted(PKG.glob("*.py")):
        if path.name in ("evaluate.py", "generate.py"):
            continue  # generate.py writes it; evaluate.py is the only permitted reader
        src = path.read_text(encoding="utf-8")
        if "ground_truth" in src:
            for i, line in enumerate(src.splitlines(), 1):
                if "ground_truth" in line and not line.lstrip().startswith("#"):
                    stripped = line.strip().strip('"').strip("'")
                    # Docstring mentions that assert the rule are fine; reads are not.
                    if any(tok in line for tok in ("read_csv", "open(", "Path(", "load")):
                        offenders.append(f"{path.name}:{i}: {stripped}")
    assert not offenders, "ground_truth.csv accessed outside evaluate.py:\n" + "\n".join(offenders)


def test_generate_writes_ground_truth_separately_from_features():
    """Labels must not be a column on the feature tables."""
    src = _source("generate.py")
    assert 'ground_truth.csv' in src
    for leaked in ("t_lag", "drift_type", "subtlety"):
        assert f'merchants["{leaked}"]' not in src
        assert f"merchants['{leaked}']" not in src


# ------------------------------------------------------------------ canonical thresholds

def test_distribution_thresholds_are_canonical_not_quantiles():
    """PSI and z-score thresholds must be absolute literature values.

    Portfolio quantiles are inflated by the drifted merchant-days themselves: a p93 on
    this book lands near PSI 2.1, roughly 8x the canonical 0.25 significance line, which
    makes the distribution family unreachable and hides every bust-out.
    """
    from driftwatch.evaluate import thresholds_at_q
    q = {"category_mismatch": 0.91, "ticket_psi": 0.25,
         "velocity_peer_z": 2.5, "network_overlap": 0.20}
    sig = pd.DataFrame({
        "merchant_id": ["M1"] * 100,
        "day": range(100),
        # Deliberately extreme: if these were read as quantiles the thresholds would move.
        "category_mismatch": np.linspace(0, 1, 100),
        "ticket_psi": np.linspace(0, 5, 100),
        "velocity_peer_z": np.linspace(-2, 12, 100),
        "network_overlap": np.linspace(0, 1, 100),
    })
    thr = thresholds_at_q(sig, q)
    assert thr["ticket_psi"] == 0.25, "ticket_psi must stay the canonical 0.25"
    assert thr["velocity_peer_z"] == 2.5, "velocity_peer_z must stay the canonical 2.5"
    assert thr["network_overlap"] == 0.20, "network_overlap must stay the canonical 0.20"
    # Only category_mismatch, which has no canonical scale, is allowed to be a quantile.
    assert 0.0 < thr["category_mismatch"] < 1.0


def test_trigger_constants_match_documented_rule():
    assert trigger.MIN_FAMILIES == 2
    assert trigger.TRIGGER_WINDOW == 14
    assert trigger.EXTREME_MULT == 2.5
    assert trigger.SUSTAIN_DAYS == 5
    assert set(trigger.SIGNALS) == {
        "category_mismatch", "ticket_psi", "velocity_peer_z", "network_overlap"}


def test_signal_families_are_distinct_per_signal():
    """Branch A counts *families*, so the mapping must not collapse to one family."""
    fams = {signals.SIGNAL_FAMILY[s] for s in trigger.SIGNALS}
    assert len(fams) >= 3, f"expected independent families, got {fams}"


# ------------------------------------------------------------------------- trigger logic

def _flat_signals(n_days: int = 40, **overrides) -> pd.DataFrame:
    base = {
        "merchant_id": ["M1"] * n_days,
        "day": list(range(n_days)),
        "category_mismatch": [0.0] * n_days,
        "ticket_psi": [0.0] * n_days,
        "velocity_peer_z": [0.0] * n_days,
        "network_overlap": [0.0] * n_days,
        "network_partner": [""] * n_days,
        "shared_account": [False] * n_days,
        "n_txn_window": [100] * n_days,
    }
    base.update(overrides)
    return pd.DataFrame(base)


THR = {"category_mismatch": 0.30, "ticket_psi": 0.25,
       "velocity_peer_z": 2.5, "network_overlap": 0.20}


def test_quiet_merchant_never_fires():
    fired = trigger.run_triggers(_flat_signals(), THR)
    assert len(fired) == 0


def test_single_family_below_extreme_does_not_fire():
    """One family crossing the plain threshold is not corroboration."""
    psi = [0.0] * 40
    for d in range(10, 40):
        psi[d] = 0.30          # over 0.25, under the 2.5x extreme bar
    fired = trigger.run_triggers(_flat_signals(ticket_psi=psi), THR)
    assert len(fired) == 0, "a single non-extreme family must not open a case"


def test_branch_a_requires_two_distinct_families():
    psi = [0.0] * 40
    vel = [0.0] * 40
    for d in range(10, 40):
        psi[d] = 0.30
        vel[d] = 3.0
    fired = trigger.run_triggers(_flat_signals(ticket_psi=psi, velocity_peer_z=vel), THR)
    assert len(fired) == 1
    hit = fired.iloc[0]
    assert hit.branch == "A_corroboration"
    assert len(hit.families) >= trigger.MIN_FAMILIES


def test_branch_b_needs_sustained_extreme():
    """A bust-out is single-family by construction, so Branch B carries it -- but only
    after SUSTAIN_DAYS consecutive days above 2.5x, not on the first spike."""
    vel = [0.0] * 40
    for d in range(10, 10 + trigger.SUSTAIN_DAYS):
        vel[d] = 2.5 * THR["velocity_peer_z"] + 1.0
    fired = trigger.run_triggers(_flat_signals(velocity_peer_z=vel), THR)
    assert len(fired) == 1
    hit = fired.iloc[0]
    assert hit.branch == "B_sustained_extreme"
    assert hit.trigger_day == 10 + trigger.SUSTAIN_DAYS - 1, "must fire on the Nth day, not the 1st"


def test_branch_b_does_not_fire_one_day_early():
    vel = [0.0] * 40
    for d in range(10, 10 + trigger.SUSTAIN_DAYS - 1):
        vel[d] = 2.5 * THR["velocity_peer_z"] + 1.0
    fired = trigger.run_triggers(_flat_signals(velocity_peer_z=vel), THR)
    assert len(fired) == 0


def test_reported_value_is_the_reading_that_crossed():
    """A signal qualifies by crossing anywhere in the 14-day window, so the trigger-day
    reading may be below threshold. The case file must report the crossing value, or a
    reviewer sees evidence that contradicts its own threshold."""
    psi = [0.0] * 40
    vel = [0.0] * 40
    psi[10] = 0.90                     # crosses once, then decays
    for d in range(11, 40):
        psi[d] = 0.01
    for d in range(12, 40):
        vel[d] = 3.0                   # second family arrives later, inside the window
    fired = trigger.run_triggers(_flat_signals(ticket_psi=psi, velocity_peer_z=vel), THR)
    assert len(fired) == 1
    ev = {s["signal"]: s for s in fired.iloc[0].signals_fired}
    assert ev["ticket_psi"]["value"] >= THR["ticket_psi"], "reported value must be >= threshold"
    assert ev["ticket_psi"]["value_at_trigger_day"] < THR["ticket_psi"], "decay must be visible"


def test_case_is_opened_once_per_merchant():
    psi = [0.30] * 40
    vel = [3.0] * 40
    fired = trigger.run_triggers(_flat_signals(ticket_psi=psi, velocity_peer_z=vel), THR)
    assert len(fired) == 1, "a merchant under review must not re-trigger"


# ------------------------------------------------------------------------ no lookahead

def test_velocity_is_peer_relative_and_zero_centred_on_uniform_surge():
    """A portfolio-wide festival surge must not be anomalous for anybody.

    If every merchant grows by the same factor on the same day, the cross-sectional
    robust z of that growth is ~0 for all of them. This is what stops the detector
    firing on the whole book during Diwali.
    """
    z = signals._robust_z(np.full(200, 3.7))
    assert np.allclose(z, 0.0), "uniform growth must produce no peer-relative anomaly"

    x = np.full(200, 1.0)
    x[0] = 50.0                       # one merchant surging against a flat book
    z = signals._robust_z(x)
    assert z[0] > 3.0, "an idiosyncratic surge must remain detectable"
    assert np.all(np.abs(z[1:]) < 1.0)


def test_psi_is_zero_for_identical_distributions_and_grows_with_shift():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 5000)
    b = rng.normal(0, 1, 5000)
    assert signals.psi(a, b) < 0.10, "same distribution must not look like drift"
    shifted = rng.normal(2.5, 1, 5000)
    assert signals.psi(a, shifted) > 0.25, "a real shift must clear the canonical line"


# ------------------------------------------------------------------------- the LLM layer

def test_llm_is_never_asked_for_a_verdict():
    """The model classifies and writes prose. It must not be asked to decide risk."""
    src = _source("llm.py").lower()
    banned = ["is this merchant fraudulent?", "should we block", "assign a risk score",
              "rate the risk", "decide whether to", "is this fraud"]
    # The docstring states the rule using one of these phrases; strip quoted rule text.
    prompts = "\n".join(
        line for line in src.splitlines() if "never" not in line and "not " not in line)
    for phrase in banned:
        assert phrase not in prompts, f"llm.py appears to ask for a verdict: {phrase!r}"


def test_narrative_prompt_forbids_inventing_numbers_and_clause_numbers():
    src = _source("llm.py")
    assert "Do not invent any figure not present below." in src
    assert "Do not cite regulatory clause numbers." in src


def test_keyless_run_is_labelled_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(llm, "CACHE", tmp_path / "cache.json")
    mapping, mode = llm.classify_descriptors(["paneer tikka roll", "replica handbag"])
    assert mode == "fallback-lexicon", "fallback must be labelled, never silent"
    assert set(mapping) == {"paneer tikka roll", "replica handbag"}

    narrative, nmode = llm.write_narrative({
        "merchant_id": "M1", "declared_category": "ecommerce", "trigger_day": 100,
        "days_since_onboarding": 40, "recommended_action": "investigate",
        "signals_fired": [{"signal": "ticket_psi", "value": 0.4, "threshold": 0.25,
                           "first_crossed_day": 95}],
    })
    assert nmode == "fallback-template"
    assert "not a finding of wrongdoing" in narrative


def test_cached_fallback_does_not_suppress_a_real_call(monkeypatch, tmp_path):
    """Regression: a keyless run used to poison the cache permanently.

    classify_descriptors returned any cache that covered the descriptor set, so once a
    fallback mapping was written, every later run reported fallback mode even with a
    valid key -- while looking completely healthy.
    """
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({
        "mode": "fallback-lexicon",
        "mapping": {"paneer tikka roll": "food_and_beverage"},
    }), encoding="utf-8")
    monkeypatch.setattr(llm, "CACHE", cache)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")

    called = {"n": 0}

    def fake_call(prompt, max_tokens=4000):
        called["n"] += 1
        return json.dumps({"paneer tikka roll": "food_and_beverage"})

    monkeypatch.setattr(llm, "_call_gemini", fake_call)
    _, mode = llm.classify_descriptors(["paneer tikka roll"])
    assert called["n"] == 1, "a key was present; the cached fallback must be re-derived"
    assert mode == "gemini"


def test_api_key_is_never_logged(capsys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "SUPERSECRETKEY123")
    monkeypatch.setattr(llm, "ENDPOINT", "http://127.0.0.1:9/{model}")  # refused instantly
    llm._call_gemini("hello", max_tokens=10)
    out = capsys.readouterr().out
    assert "SUPERSECRETKEY123" not in out, "the API key must never reach stdout"


# ---------------------------------------------------------------- case-file consistency

@pytest.mark.skipif(not (ROOT / "out" / "evaluation.json").exists(),
                    reason="no pipeline output; run `python run_all.py` first")
def test_emitted_case_files_agree_with_the_evaluation():
    ev = json.loads((ROOT / "out" / "evaluation.json").read_text(encoding="utf-8"))
    triggers = json.loads((ROOT / "out" / "held_out_triggers.json").read_text(encoding="utf-8"))
    cases = [json.loads(p.read_text(encoding="utf-8"))
             for p in sorted((ROOT / "out" / "cases").glob("DW-*.json"))]

    assert len(cases) == len(triggers), "stale case files from a previous calibration"
    assert len({c["merchant_id"] for c in cases}) == len(cases), "duplicate merchant ids"

    thresholds = {json.dumps(c["provenance"]["thresholds"], sort_keys=True) for c in cases}
    assert len(thresholds) == 1, "case files span more than one calibration"

    fp = set(ev["held_out"]["fp_ids"])
    n_tp = sum(1 for c in cases if c["merchant_id"] not in fp)
    assert n_tp == ev["held_out"]["caught"]

    for c in cases:
        for s in c["signals_fired"]:
            assert s["value"] >= s["threshold"], (
                f"{c['case_id']} cites {s['signal']} below its own threshold")
        assert c["provenance"]["descriptor_classifier_mode"]
        assert c["provenance"]["narrative_mode"]
