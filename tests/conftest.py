"""
Pytest configuration.

Its one job is to make skipped consistency tests impossible to miss.

The docs-consistency suite guards every number quoted in README.md and
docs/EVALUATION.md against `out/evaluation.json`. Those tests skip when the artifact is
absent, which is correct behaviour -- but for a while CI had no artifact, so nineteen of
them skipped on every pull request and the guard silently enforced nothing. The suite was
green the entire time. A quiet skip is indistinguishable from a pass at a glance, and that
is exactly how the gap survived.

So: if any consistency test skips, the run ends with a banner saying how many and why.
"""
from __future__ import annotations

import pytest

CONSISTENCY_MODULE = "test_docs_consistency"


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    skipped = [r for r in terminalreporter.stats.get("skipped", [])
               if CONSISTENCY_MODULE in str(getattr(r, "nodeid", ""))]
    if not skipped:
        return

    reasons = sorted({
        (r.longrepr[2] if isinstance(getattr(r, "longrepr", None), tuple) and len(r.longrepr) == 3
         else str(getattr(r, "longrepr", "unknown")))
        for r in skipped
    })

    w = terminalreporter
    w.write_sep("=", "DOCS-CONSISTENCY GUARD NOT ENFORCED", red=True, bold=True)
    w.write_line(f"{len(skipped)} consistency test(s) skipped. Reason(s):")
    for reason in reasons:
        w.write_line(f"  - {reason}")
    w.write_line("")
    w.write_line("These tests are the only thing checking that the numbers in README.md and")
    w.write_line("docs/EVALUATION.md still match out/evaluation.json. While they skip, a")
    w.write_line("documentation number can drift from the pipeline and the suite stays green.")
    w.write_line("")
    w.write_line("out/evaluation.json is committed precisely so this does not happen in CI.")
    w.write_line("If it is missing, either the checkout is incomplete or the file was removed")
    w.write_line("from version control -- fix that rather than accepting the skip.")
    w.write_sep("=", red=True, bold=True)
