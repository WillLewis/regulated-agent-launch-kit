# Risk Register

| Risk | Impact | Mitigation | Owner | Status |
|---|---|---|---|---|
| Consent-sensitive case misrouted | Unsafe recommendation or missing approval | Route grader, consent grader, evaluator check, regression case | Deployment lead | Open |
| Evaluator misses unsupported customer claim | Public-facing overclaim | Unsupported-claim grader and reviewer sampling | Compliance reviewer | Open |
| Partner schema changes break tool calls | Tool misuse or failed handoff | Schema versioning and required-tool grader | Deployment engineer | Open |
| Latency hurts workflow adoption | Low user trust and poor pilot uptake | Cost/latency grader and routine-case routing policy | Product owner | Open |
| Redacted evidence loses diagnostic value | Weak public proof | Redaction reviewer and evidence-pack checklist | Risk reviewer | Open |
| Dataset realism is insufficient | False confidence from synthetic scores | Dataset card and human review | Human owner | Open |
| Over-escalation increases support burden | Operational load | Escalation precision metric and KPI tree | Partner support lead | Open |
| Synthetic-only scores create false confidence | Inflated launch recommendation | Exec update must state synthetic limitations | Executive sponsor | Open |
