"""Agent-system profiles for deterministic baseline-vs-improved comparison.

The deployment-readiness narrative needs an honest "before" and "after"
to be measurable. ``BASELINE_V0`` is a *deliberately weak* synthetic
configuration: it skips partner-config lookups when the aggregator
route looks healthy, never cites the synthetic partner-fallback policy,
and injects a real-time-data overpromise on granted-consent healthy
cases. None of that behavior is acceptable for a real deployment — it
exists in this lab so the offline graders have visible failures to
classify and so an "improved" delta is real, not narrative.

``IMPROVED_V0`` preserves the policy-compliant deterministic behavior
shipped earlier in Phase 3.

``LLM_CANDIDATE_V0`` is an *optional* profile that reuses every
deterministic decision ``IMPROVED_V0`` makes (tool calls, policy
citations, approval boundary, prohibited-action avoidance) but
generates the customer-facing ``draft_text`` via the
``app.agents.llm_adapter``. It requires credentials, is **not** part
of the public proof loop, and is not the default. Approval boundaries
remain deterministic; the LLM never decides who must approve a case.

``LLM_CANDIDATE_V1`` is a *prompt-improvement* sibling of
``LLM_CANDIDATE_V0``. Same adapter, same model, same cost-capture
path, same deterministic decisions — only the prompt changes. v1
exists so the four ``UNSAFE_CUSTOMER_COMMS`` failures the real-LLM
adversarial run surfaced on v0 can be measured as a true before/after
delta. Like v0, it is opt-in and credential-gated; no Make target in
the public proof loop invokes it.

Profile strings are stable so they can be written into
``TraceRecord.agent_system_version``, surfaced in eval reports, and
filtered on without parsing. Add new profiles by extending the enum
and branching in ``app.agents.financial_links_reliability_agent``.
"""

from __future__ import annotations

from enum import Enum


class AgentSystemProfile(str, Enum):
    """Stable identifiers for synthetic agent-system configurations."""

    BASELINE_V0 = "baseline_v0"
    IMPROVED_V0 = "improved_v0"
    LLM_CANDIDATE_V0 = "llm_candidate_v0"
    LLM_CANDIDATE_V1 = "llm_candidate_v1"


KNOWN_PROFILES: frozenset[str] = frozenset(profile.value for profile in AgentSystemProfile)

DEFAULT_PROFILE: AgentSystemProfile = AgentSystemProfile.IMPROVED_V0


def normalize_profile(value: str | None) -> str:
    """Validate a profile string. Returns the default when ``value`` is ``None``."""

    if value is None:
        return DEFAULT_PROFILE.value
    if value not in KNOWN_PROFILES:
        raise ValueError(
            f"Unknown agent-system profile {value!r}; "
            f"known profiles: {sorted(KNOWN_PROFILES)}"
        )
    return value
