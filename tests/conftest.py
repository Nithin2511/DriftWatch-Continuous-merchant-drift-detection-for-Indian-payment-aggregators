"""
Pytest configuration.

Its one job is to make skipped tests impossible to miss.

The docs-consistency suite guards every number quoted in README.md and
docs/EVALUATION.md against `out/evaluation.json`. Those tests skip when the artifact is
absent, which is correct behaviour -- but `out/` was gitignored, so on CI nineteen of them
skipped on every pull request, plus one invariant test, and the guard enforced nothing.
The suite was green the whole time. A skipped test is indistinguishable from a passing one
in the summary line, and that is exactly how the gap survived.

`out/evaluation.json` is now committed so that cannot recur. This hook is the backstop: if
anything skips, the run ends with a banner saying how many, why, and which.
"""
from __future__ import annotations


def _reason(report) -> str:
    lr = getattr(report, "longrepr", None)
    if isinstance(lr, tuple) and len(lr) == 3:
        return str(lr[2]).removeprefix("Skipped: ")
    return str(lr) if lr else "unknown"


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Report every skip in the suite, grouped by reason.

    Deliberately covers the whole suite rather than one module. The gap that hid was 19
    docs-consistency tests *plus* one invariant test, and a filter narrow enough to miss
    that twentieth test would have been part of the same blind spot.
    """
    skipped = terminalreporter.stats.get("skipped", [])
    if not skipped:
        return

    by_reason: dict[str, list[str]] = {}
    for rep in skipped:
        by_reason.setdefault(_reason(rep), []).append(str(getattr(rep, "nodeid", "?")))

    w = terminalreporter
    w.write_sep("=", f"{len(skipped)} TEST(S) SKIPPED - GUARD PARTIALLY UNENFORCED",
                yellow=True, bold=True)
    for reason, nodes in sorted(by_reason.items()):
        w.write_line(f"{len(nodes)} skipped: {reason}")
        for node in sorted(nodes)[:4]:
            w.write_line(f"    {node}")
        if len(nodes) > 4:
            w.write_line(f"    ... and {len(nodes) - 4} more")
    w.write_line("")
    w.write_line("A skipped test looks identical to a passing one in the summary line. That is")
    w.write_line("how 20 of 39 tests sat inert on every pull request without anyone noticing.")
    w.write_line("")
    w.write_line("Expected in CI: the tests needing out/cases/ and out/held_out_triggers.json,")
    w.write_line("which are generated and deliberately not committed. Run `python run_all.py`")
    w.write_line("locally to exercise them. Anything ELSE skipping -- above all a missing")
    w.write_line("out/evaluation.json, which IS committed -- means something is wrong.")
    w.write_sep("=", yellow=True, bold=True)
