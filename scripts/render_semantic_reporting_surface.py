"""Render a static HTML preview for the fixture-backed semantic eval lane.

The output is a local reporting-surface mock, not the final public website.
It reads generated eval reports and the adversarial dataset, then renders a
public-safe HTML file that shows how the semantic unsupported-claim lane would
be explained to a reviewer.
"""

from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from typing import Any

from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.run import CaseEvalResult, EvalReport  # noqa: E402


SEMANTIC_GRADER_NAME = "unsupported_claim_semantic"
LEXICAL_GRADER_NAME = "unsupported_claim"
LAUNCH_POSTURE = (
    "NOT READY FOR PILOT — local synthetic vertical slice only; this fixture "
    "lane demonstrates an audit contract, not model safety, production "
    "readiness, regulatory compliance, or partner acceptance."
)
SYNTHETIC_DISCLAIMER = (
    "Synthetic Financial Links adversarial v1 data only. Semantic decisions "
    "are local fixtures; no model or network call is made by this report."
)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON ({exc})")


def _load_report(path: Path) -> EvalReport:
    if not path.exists():
        raise SystemExit(f"eval report not found: {path}")
    try:
        return EvalReport.model_validate(_load_json(path))
    except ValidationError as exc:
        raise SystemExit(f"{path}: does not match EvalReport shape:\n{exc}")


def _load_dataset(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"dataset not found: {path}")
    cases: dict[str, dict[str, Any]] = {}
    for line_no, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}: line {line_no}: invalid JSON ({exc})")
        case_id = str(record.get("case_id", ""))
        if not case_id:
            raise SystemExit(f"{path}: line {line_no}: missing case_id")
        if case_id in cases:
            raise SystemExit(f"{path}: duplicate case_id {case_id!r}")
        cases[case_id] = record
    return cases


def _rate_map(report: EvalReport) -> dict[str, tuple[int, int, float]]:
    return {
        rate.name: (rate.passed, rate.total, rate.pass_rate)
        for rate in report.aggregate_grader_pass_rates
    }


def _case_map(report: EvalReport) -> dict[str, CaseEvalResult]:
    return {case.case_id: case for case in report.per_case}


def _result_map(report: EvalReport, case: CaseEvalResult) -> dict[str, Any]:
    names = [rate.name for rate in report.aggregate_grader_pass_rates]
    if len(names) != len(case.grader_results):
        raise SystemExit(
            f"{report.agent_system_version}/{case.case_id}: grader result count "
            f"{len(case.grader_results)} does not match aggregate grader names "
            f"{len(names)}"
        )
    return dict(zip(names, case.grader_results, strict=True))


def _require_semantic_lane(report: EvalReport, label: str) -> None:
    names = [rate.name for rate in report.aggregate_grader_pass_rates]
    if SEMANTIC_GRADER_NAME not in names:
        raise SystemExit(
            f"{label} report does not include {SEMANTIC_GRADER_NAME!r}; "
            "rerun scripts/run_eval.py with --semantic-decisions."
        )


def _validate_pair(
    dataset: dict[str, dict[str, Any]],
    baseline: EvalReport,
    improved: EvalReport,
) -> None:
    _require_semantic_lane(baseline, "baseline")
    _require_semantic_lane(improved, "improved")
    if baseline.dataset_path != improved.dataset_path:
        raise SystemExit(
            "baseline and improved reports use different datasets: "
            f"{baseline.dataset_path!r} vs {improved.dataset_path!r}"
        )
    if baseline.case_count != improved.case_count:
        raise SystemExit(
            "baseline and improved reports have different case counts: "
            f"{baseline.case_count} vs {improved.case_count}"
        )
    dataset_ids = set(dataset)
    baseline_ids = set(_case_map(baseline))
    improved_ids = set(_case_map(improved))
    if dataset_ids != baseline_ids or dataset_ids != improved_ids:
        raise SystemExit(
            "dataset and report case IDs do not match; regenerate the semantic "
            "reports from the same dataset."
        )


def _status_text(passed: bool, failure_label: str | None) -> str:
    if passed:
        return "Pass"
    return failure_label or "Fail"


def _semantic_summary(report: EvalReport) -> tuple[int, int, int]:
    passed, total, _ = _rate_map(report)[SEMANTIC_GRADER_NAME]
    return passed, total - passed, total


def _comparison_label(lexical_passed: bool, semantic_passed: bool) -> str:
    if lexical_passed and semantic_passed:
        return "Both pass"
    if not lexical_passed and not semantic_passed:
        return "Both fail"
    if lexical_passed and not semantic_passed:
        return "Semantic-only fail"
    return "Lexical-only fail"


def _grader_rate_rows(baseline: EvalReport, improved: EvalReport) -> str:
    baseline_rates = _rate_map(baseline)
    improved_rates = _rate_map(improved)
    rows: list[str] = []
    for name in baseline_rates:
        other = improved_rates.get(name)
        if other is None:
            continue
        b_passed, b_total, b_rate = baseline_rates[name]
        i_passed, i_total, i_rate = other
        rows.append(
            "<tr>"
            f"<th scope=\"row\"><code>{escape(name)}</code></th>"
            f"<td>{b_passed}/{b_total} <span>({b_rate:.2f})</span></td>"
            f"<td>{i_passed}/{i_total} <span>({i_rate:.2f})</span></td>"
            f"<td>{i_rate - b_rate:+.2f}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _case_rows(
    dataset: dict[str, dict[str, Any]],
    baseline: EvalReport,
    improved: EvalReport,
) -> str:
    baseline_cases = _case_map(baseline)
    improved_cases = _case_map(improved)
    rows: list[str] = []
    for case_id, record in dataset.items():
        baseline_results = _result_map(baseline, baseline_cases[case_id])
        improved_results = _result_map(improved, improved_cases[case_id])
        b_lex = baseline_results[LEXICAL_GRADER_NAME]
        b_sem = baseline_results[SEMANTIC_GRADER_NAME]
        i_sem = improved_results[SEMANTIC_GRADER_NAME]
        evidence = b_sem.evidence or {}
        tags = ", ".join(str(tag) for tag in record.get("category_tags", []))
        rationale = str(evidence.get("rationale", ""))
        spans = evidence.get("evidence_spans") or []
        span_text = ", ".join(str(span) for span in spans) if spans else "none"
        comparison = _comparison_label(b_lex.passed, b_sem.passed)
        rows.append(
            "<tr>"
            f"<th scope=\"row\"><code>{escape(case_id)}</code></th>"
            f"<td>{escape(str(record.get('risk_band', '')))}</td>"
            f"<td>{escape(tags)}</td>"
            f"<td>{escape(_status_text(b_lex.passed, b_lex.failure_label))}</td>"
            f"<td>{escape(_status_text(b_sem.passed, b_sem.failure_label))}</td>"
            f"<td>{escape(_status_text(i_sem.passed, i_sem.failure_label))}</td>"
            f"<td>{escape(comparison)}</td>"
            f"<td><span class=\"calibration\">{escape(str(evidence.get('calibration', 'none')))}</span>"
            f"<br><small>{escape(rationale)}</small>"
            f"<br><small>Evidence spans: {escape(span_text)}</small></td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_html(
    *,
    dataset_path: Path,
    baseline_report_path: Path,
    improved_report_path: Path,
) -> str:
    dataset = _load_dataset(dataset_path)
    baseline = _load_report(baseline_report_path)
    improved = _load_report(improved_report_path)
    _validate_pair(dataset, baseline, improved)

    b_sem_passed, b_sem_failed, b_sem_total = _semantic_summary(baseline)
    i_sem_passed, i_sem_failed, i_sem_total = _semantic_summary(improved)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Fixture-Backed Semantic Reporting Surface</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17212b;
      --muted: #5b6673;
      --line: #d8dee6;
      --paper: #f8fafc;
      --panel: #ffffff;
      --accent: #0f766e;
      --risk: #b45309;
      --fail: #b42318;
      --pass: #067647;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--paper);
      line-height: 1.45;
    }}
    header, main {{
      width: min(1180px, calc(100vw - 40px));
      margin: 0 auto;
    }}
    header {{
      padding: 36px 0 20px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 32px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 20px;
      letter-spacing: 0;
    }}
    p {{ max-width: 920px; }}
    code {{
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 0.92em;
    }}
    .subtitle, .note {{
      color: var(--muted);
    }}
    .posture {{
      margin-top: 18px;
      padding: 14px 16px;
      border-left: 4px solid var(--risk);
      background: #fff7ed;
      font-weight: 650;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(180px, 1fr));
      gap: 12px;
      margin: 20px 0 8px;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-height: 110px;
    }}
    .metric b {{
      display: block;
      font-size: 24px;
      margin-top: 6px;
    }}
    .metric small {{
      color: var(--muted);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: #eef4f8;
      font-weight: 680;
    }}
    tr:last-child th, tr:last-child td {{ border-bottom: 0; }}
    .calibration {{
      display: inline-block;
      color: var(--accent);
      font-weight: 650;
      margin-bottom: 4px;
    }}
    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      align-items: start;
    }}
    @media (max-width: 860px) {{
      header, main {{ width: min(100vw - 24px, 1180px); }}
      .metrics, .grid-2 {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Fixture-Backed Semantic Reporting Surface</h1>
    <p class=\"subtitle\">{escape(SYNTHETIC_DISCLAIMER)}</p>
    <div class=\"posture\">{escape(LAUNCH_POSTURE)}</div>
  </header>
  <main>
    <section>
      <h2>Scope</h2>
      <p>
        This preview reads <code>{escape(str(dataset_path))}</code> and compares
        <code>{escape(baseline.agent_system_version)}</code> with
        <code>{escape(improved.agent_system_version)}</code>. The default eval
        lane remains unchanged; supplying a semantic-decision fixture adds the
        ninth grader row <code>{SEMANTIC_GRADER_NAME}</code>.
      </p>
      <div class=\"metrics\">
        <div class=\"metric\"><small>Dataset cases</small><b>{baseline.case_count}</b><small>adversarial v1 cases</small></div>
        <div class=\"metric\"><small>{escape(baseline.agent_system_version)} overall</small><b>{baseline.passed_case_count}/{baseline.case_count}</b><small>cases passed</small></div>
        <div class=\"metric\"><small>{escape(improved.agent_system_version)} overall</small><b>{improved.passed_case_count}/{improved.case_count}</b><small>cases passed</small></div>
        <div class=\"metric\"><small>Semantic fixture</small><b>local</b><small>no model call</small></div>
      </div>
    </section>
    <section>
      <h2>Semantic Unsupported-Claim Lane</h2>
      <div class=\"grid-2\">
        <table>
          <thead><tr><th>Profile</th><th>Semantic pass</th><th>Semantic fail</th></tr></thead>
          <tbody>
            <tr><th scope=\"row\"><code>{escape(baseline.agent_system_version)}</code></th><td>{b_sem_passed}/{b_sem_total}</td><td>{b_sem_failed}</td></tr>
            <tr><th scope=\"row\"><code>{escape(improved.agent_system_version)}</code></th><td>{i_sem_passed}/{i_sem_total}</td><td>{i_sem_failed}</td></tr>
          </tbody>
        </table>
        <p class=\"note\">
          The semantic lane consumes precomputed <code>SemanticDecision</code>
          fixture records. It is an adapter contract for future NLI/model
          graders, not a live model grader and not a replacement for the
          runtime EvaluatorNode. Evidence rows are labeled
          <code>semantic_fixture</code> so reviewers can distinguish this
          lane from a future model-backed grader.
        </p>
      </div>
    </section>
    <section>
      <h2>Grader Rates</h2>
      <table>
        <thead><tr><th>Grader</th><th>{escape(baseline.agent_system_version)}</th><th>{escape(improved.agent_system_version)}</th><th>Delta</th></tr></thead>
        <tbody>
          {_grader_rate_rows(baseline, improved)}
        </tbody>
      </table>
    </section>
    <section>
      <h2>Case-Level Surface</h2>
      <p class=\"note\">
        The case table shows whether the lexical unsupported-claim grader and
        the fixture-backed semantic grader agree. This is the reviewer-facing
        surface for debugging paraphrases, safe negation, cross-sentence traps,
        and calibration cases before any credentialed model grader is wired in.
      </p>
      <table>
        <thead>
          <tr>
            <th>Case</th>
            <th>Risk</th>
            <th>Tags</th>
            <th>Baseline lexical</th>
            <th>Baseline semantic</th>
            <th>Improved semantic</th>
            <th>Readout</th>
            <th>Semantic evidence</th>
          </tr>
        </thead>
        <tbody>
          {_case_rows(dataset, baseline, improved)}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def render_reporting_surface(
    *,
    dataset_path: Path,
    baseline_report_path: Path,
    improved_report_path: Path,
    out: Path,
) -> Path:
    html = render_html(
        dataset_path=dataset_path,
        baseline_report_path=baseline_report_path,
        improved_report_path=improved_report_path,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the fixture-backed semantic reporting surface as HTML."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--baseline-report", type=Path, required=True)
    parser.add_argument("--improved-report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    out = render_reporting_surface(
        dataset_path=args.dataset,
        baseline_report_path=args.baseline_report,
        improved_report_path=args.improved_report,
        out=args.out,
    )
    print(f"OK: wrote semantic reporting surface -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
