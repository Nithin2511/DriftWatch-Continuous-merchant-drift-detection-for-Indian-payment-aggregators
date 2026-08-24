"""
The language-model layer (Google Gemini).

The LLM is used for exactly two things, both of which are genuine language problems:

  1. classify_descriptors() -- map free-text transaction descriptors to an implied
     merchant category. This is a text-understanding task.
  2. write_narrative()      -- turn a fired trigger's numeric evidence into prose a
     compliance reviewer can act on.

The model is NEVER asked whether a merchant is fraudulent. The fire/no-fire decision is
made in trigger.py by quantitative signals against thresholds calibrated on the
development split. That separation is deliberate and is the difference between an
auditable system and an LLM wrapper.

Both calls degrade to a deterministic fallback when no API key is present, so the
pipeline is reproducible by anyone cloning the repo. Fallback mode is always LABELLED in
the output -- it is never silently substituted, because a case file that does not say how
it was produced is not auditable.

Cost note: descriptor classification is called once per unique descriptor string, not once
per transaction. Over 1.03M transactions there are 63 unique descriptors, so the classifier
is O(vocabulary), not O(volume). That is also how you would build it in production.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

# Pinned rather than "-latest": the evaluation numbers in docs/EVALUATION.md were
# produced by this model, and a floating alias would silently invalidate them.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

#: Minimum gap between calls. Free-tier keys are rate-limited per minute, and 23 narrative
#: calls fired back to back will trip it. Pacing the client is cheaper than retrying.
MIN_CALL_INTERVAL_S = 6.0
#: Backoff schedule for retryable failures (429 / 5xx / transport). Deliberately long:
#: a per-minute limit needs to be waited out, not hammered.
BACKOFF_S = (5.0, 15.0, 45.0, 90.0)
_last_call_at = 0.0
ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/models/"
            "{model}:generateContent")
CACHE = Path("data/descriptor_categories.json")

#: Modes that mean "no model was actually consulted". Used to decide whether a cached
#: classification may be reused once an API key becomes available.
FALLBACK_MODES = {"fallback-lexicon", "fallback-template", "fallback"}

CATEGORY_SET = [
    "ecommerce", "food_and_beverage", "it_and_software",
    "travel_agency", "financial_services", "education", "restricted",
]

# Deterministic fallback lexicon. Written from domain knowledge, the way a risk analyst
# would write a starter lexicon -- NOT copied from the generator's vocabulary. Its accuracy
# against the generator's true categories is measured and reported, not assumed.
_LEXICON = {
    "ecommerce": ["kurta", "shoes", "earbuds", "bottle", "clock", "mat", "backpack",
                  "case", "bedsheet", "kitchen", "denim", "jacket", "sunglasses",
                  "lamp", "storage", "shirt", "shoe"],
    "food_and_beverage": ["paneer", "biryani", "coffee", "dosa", "roll", "meal", "thali",
                          "pizza", "samosa", "tea", "jamun", "combo", "lunch", "masala"],
    "it_and_software": ["saas", "api", "licence", "license", "cloud", "seat", "sla",
                        "subscription", "hosting", "server", "dashboard", "integration",
                        "platform", "workspace"],
    "travel_agency": ["flight", "hotel", "visa", "train", "cab", "tour", "booking",
                      "itinerary", "travel", "holiday", "package"],
    "financial_services": ["premium", "policy", "loan", "emi", "insurance", "advisory",
                           "portfolio", "mutual", "broking", "settlement"],
    "education": ["course", "tuition", "exam", "class", "lecture", "semester", "coaching",
                  "workshop", "certification", "batch"],
    "restricted": ["nutraceutical", "replica", "first copy", "prediction", "fantasy",
                   "wallet load", "forex signal", "offshore", "supplement", "herbal",
                   "betting", "casino", "rummy", "teen patti"],
}


def api_key() -> str | None:
    """The Gemini key, or None. GOOGLE_API_KEY is accepted as an alias."""
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def _fallback_classify(descriptors: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for d in descriptors:
        low = d.lower()
        best, best_hits = "ecommerce", 0
        for cat, words in _LEXICON.items():
            hits = sum(1 for w in words if w in low)
            if hits > best_hits:
                best, best_hits = cat, hits
        out[d] = best
    return out


def _call_gemini(prompt: str, max_tokens: int = 4000) -> str | None:
    """One generateContent call. Returns None on any failure so the caller falls back.

    Failures always print the HTTP status and the API's own error message. A silent
    fallback would let a bad key or a stale model name look like a clean run, and every
    number downstream would quietly be a fallback-mode number.
    """
    global _last_call_at
    key = api_key()
    if not key:
        return None

    url = ENDPOINT.format(model=MODEL) + f"?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        # Near-deterministic: this is a classification/summarisation task, not creative
        # writing, and the run needs to be reproducible.
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens},
    }
    body_bytes = json.dumps(payload).encode()

    attempts = len(BACKOFF_S) + 1
    for attempt in range(attempts):
        # Client-side pacing, applied before every attempt including the first.
        gap = MIN_CALL_INTERVAL_S - (time.monotonic() - _last_call_at)
        if gap > 0:
            time.sleep(gap)
        try:
            req = urllib.request.Request(
                url, data=body_bytes, headers={"content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                body = json.loads(r.read())
            _last_call_at = time.monotonic()
        except urllib.error.HTTPError as e:
            _last_call_at = time.monotonic()
            detail = e.read().decode("utf-8", "replace")[:200]
            retryable = e.code == 429 or 500 <= e.code < 600
            if retryable and attempt < attempts - 1:
                # Honour Retry-After when the API sends one, else use the schedule.
                try:
                    wait = float(e.headers.get("retry-after") or 0) or BACKOFF_S[attempt]
                except (TypeError, ValueError):
                    wait = BACKOFF_S[attempt]
                print(f"  [llm] HTTP {e.code}; retrying in {wait:.0f}s "
                      f"({attempt + 1}/{attempts - 1})")
                time.sleep(wait)
                continue
            # The key never appears in the message; only the status and API detail do.
            print(f"  [llm] Gemini call failed: HTTP {e.code} -- {detail}")
            return None
        except Exception as e:
            _last_call_at = time.monotonic()
            if attempt < attempts - 1:
                wait = BACKOFF_S[attempt]
                print(f"  [llm] {type(e).__name__}; retrying in {wait:.0f}s "
                      f"({attempt + 1}/{attempts - 1})")
                time.sleep(wait)
                continue
            print(f"  [llm] Gemini call failed ({type(e).__name__}: {e}), using fallback")
            return None

        candidates = body.get("candidates") or []
        if not candidates:
            reason = (body.get("promptFeedback") or {}).get("blockReason", "no candidates")
            print(f"  [llm] Gemini returned nothing ({reason}); using fallback")
            return None

        cand = candidates[0]
        finish = cand.get("finishReason")
        if finish in ("SAFETY", "RECITATION", "PROHIBITED_CONTENT"):
            print(f"  [llm] Gemini declined this request ({finish}); using fallback")
            return None

        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        if not text.strip():
            print(f"  [llm] Gemini returned empty text (finishReason={finish}); "
                  f"using fallback")
            return None
        return text
    return None


def classify_descriptors(descriptors: list[str],
                         use_cache: bool = True) -> tuple[dict[str, str], str]:
    """Map each unique descriptor to a category.

    Returns (mapping, mode) where mode is 'gemini' or 'fallback-lexicon'.
    """
    descriptors = sorted(set(descriptors))

    if use_cache and CACHE.exists():
        cached = json.loads(CACHE.read_text(encoding="utf-8"))
        covers = set(cached.get("mapping", {})) >= set(descriptors)
        cached_mode = cached.get("mode", "fallback-lexicon")
        # Never let a cached FALLBACK result suppress a real model call once a key is
        # available. Without this check, one keyless run poisons every later run and the
        # pipeline reports fallback mode forever while looking perfectly healthy.
        stale_fallback = cached_mode in FALLBACK_MODES and api_key() is not None
        if covers and not stale_fallback:
            return cached["mapping"], cached_mode

    prompt = (
        "You are classifying merchant transaction descriptors into a business category, "
        "for a payment aggregator's merchant-monitoring system.\n\n"
        f"Allowed categories: {', '.join(CATEGORY_SET)}\n\n"
        "'restricted' means goods/services that card schemes and Indian regulators treat "
        "as prohibited or high-risk for a general merchant account (unlicensed "
        "nutraceuticals, replica/counterfeit goods, unlicensed gaming or prediction "
        "contests, offshore wallet loading, unregulated forex advisory).\n\n"
        "Return ONLY a JSON object mapping each descriptor to exactly one category. "
        "No prose, no markdown fences.\n\n"
        "Descriptors:\n" + json.dumps(descriptors, indent=0)
    )

    raw = _call_gemini(prompt, max_tokens=4000)
    mode = "gemini"
    mapping: dict[str, str] = {}
    if raw:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                parsed = json.loads(m.group(0))
                # Keep only descriptors we asked about, mapped to categories we allow.
                mapping = {k: v for k, v in parsed.items()
                           if k in set(descriptors) and v in CATEGORY_SET}
            except json.JSONDecodeError:
                mapping = {}

    if not mapping:
        mapping, mode = _fallback_classify(descriptors), "fallback-lexicon"
    else:
        missing = [d for d in descriptors if d not in mapping]
        if missing:
            # Partial model output: fill the gaps deterministically rather than dropping
            # descriptors, and say so in the mode label.
            mapping.update(_fallback_classify(missing))
            mode = f"gemini+lexicon({len(missing)} of {len(descriptors)} filled)"

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"mode": mode, "model": MODEL, "mapping": mapping},
                                indent=2), encoding="utf-8")
    return mapping, mode


#: Cases per narrative request. The free tier allows 20 generateContent calls per day per
#: model; one call per case would need 23 and cannot complete. Batching makes narrative
#: generation O(batches) rather than O(cases) -- the same reasoning that keeps descriptor
#: classification O(vocabulary) rather than O(volume).
NARRATIVE_BATCH_SIZE = 8


def _batch_prompt(cases: list[dict]) -> str:
    rules = [
        "You are a risk analyst at an Indian payment aggregator writing the narrative",
        "section of merchant-monitoring case files. Each quantitative trigger has",
        "ALREADY fired -- do not re-assess whether it should have. Explain, in plain",
        "language for a compliance reviewer, what each case shows and what happens next.",
        "",
        "Rules, applied to EVERY case:",
        "- 120-180 words, three short paragraphs.",
        "- Cite only the numbers belonging to THAT case. Never carry a figure from one",
        "  case into another, and never invent one.",
        "- State clearly that this is a behavioural signal requiring investigation,",
        "  NOT a finding of wrongdoing.",
        "- Do not cite regulatory clause numbers.",
        "",
        "Return ONLY a JSON object mapping each case_id to its narrative string.",
        "No prose, no markdown fences.",
        "",
        "Cases:",
    ]
    return "\n".join(rules) + "\n" + json.dumps(cases, indent=1, default=str)


def write_narratives(cases: list[dict],
                     batch_size: int = NARRATIVE_BATCH_SIZE) -> tuple[dict[str, str], str]:
    """Generate narratives for many cases in few requests.

    Returns (mapping case_id -> narrative, mode). Cases the model does not return are
    left out of the mapping; the caller falls back per case and labels each one.
    """
    if not api_key() or not cases:
        return {}, "fallback-template"

    out: dict[str, str] = {}
    for i in range(0, len(cases), batch_size):
        chunk = cases[i:i + batch_size]
        raw = _call_gemini(_batch_prompt(chunk), max_tokens=8000)
        if not raw:
            continue
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            continue
        try:
            parsed = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        wanted = {c["case_id"] for c in chunk}
        for cid, text in parsed.items():
            if cid in wanted and isinstance(text, str) and text.strip():
                out[cid] = text.strip()

    if not out:
        return {}, "fallback-template"
    return out, "gemini"


def write_narrative(case: dict) -> tuple[str, str]:
    """Turn a fired trigger's evidence into reviewer-readable prose.

    Returns (narrative, mode) where mode is 'gemini' or 'fallback-template'.
    """
    prompt = (
        "You are a risk analyst at an Indian payment aggregator writing the narrative "
        "section of a merchant-monitoring case file. The quantitative trigger has ALREADY "
        "fired -- do not re-assess whether it should have. Your job is to explain, in "
        "plain language for a compliance reviewer, what the evidence shows and what "
        "happens next.\n\n"
        "Rules:\n"
        "- 120-180 words, three short paragraphs.\n"
        "- Cite the actual numbers given. Do not invent any figure not present below.\n"
        "- State clearly that this is a behavioural signal requiring investigation, NOT a "
        "finding of wrongdoing.\n"
        "- Do not cite regulatory clause numbers.\n\n"
        f"Case evidence:\n{json.dumps(case, indent=2, default=str)}"
    )
    raw = _call_gemini(prompt, max_tokens=2000)
    if raw and raw.strip():
        return raw.strip(), "gemini"

    sigs = case.get("signals_fired", [])
    lines = [
        f"Merchant {case['merchant_id']} (declared category: {case['declared_category']}) "
        f"crossed the corroboration threshold on observation day {case['trigger_day']}, "
        f"{case['days_since_onboarding']} days after onboarding. "
        f"{len(sigs)} independent signal families fired inside the review window.",
        "",
        "Evidence: " + "; ".join(
            f"{s['signal']} = {s['value']:.3f} against a threshold of {s['threshold']:.3f} "
            f"(first crossed day {s['first_crossed_day']})" for s in sigs) + ".",
        "",
        "This is a behavioural divergence between the merchant's declared profile and its "
        "observed transaction activity. It is a signal requiring investigation, not a "
        "finding of wrongdoing. Recommended action: "
        f"{case['recommended_action']}. A reviewer should confirm whether a legitimate "
        "business change explains the divergence before any settlement action is taken.",
    ]
    return "\n".join(lines), "fallback-template"
