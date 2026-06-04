# SWE-ContextBench Operational Extractor Prompt

Extract Operational Decision Brief v0 items from the base task only.

Allowed inputs:

- base problem statement
- base hints
- base accepted patch
- base public issue/PR metadata

Forbidden inputs:

- related task hidden patch
- related task hidden tests
- related task final answer
- related task grading result

Return strict JSON with keys `decisions` and `rejected`. Do not include
markdown.

Rules:

- Extract only accepted decisions, requirements, constraints, procedures, and
  implementation commitments.
- Preserve implementation-critical details: argument mapping, operator choice,
  extension point, callable/index choice, invariant, fallback/default policy,
  and negative prefixes/suffixes.
- Preserve conditions exactly. If the source says "when X is false, use Y",
  the decision must keep "when X is false"; do not rewrite it as "if Z is not
  available" or a generic requirement.
- Preserve branch behavior. If accepted code has different behavior for two
  branches, emit separate short decisions for each branch when both matter.
- Preserve key/value mappings and identity mappings: graph key, URL, argument
  index, source object, target object, and branch-specific object identity.
- Preserve exact code identifiers only when they carry the decision, such as
  `internal`, `refuri`, `current_filename`, `attrs[1]`, or an accepted extension
  point file/function.
- Include `critical_details` for each decision: 1-5 short phrases that a patch
  verifier or manual audit can use to check whether the agent preserved the
  decision.
- Do not copy raw patch hunks. Do not include file locations unless the file is
  the accepted extension point.
- Better reject an uncertain item than create a false decision.
- Each decision text should be short enough to fit as a prompt bullet.

Schema:

```json
{
  "decisions": [
    {
      "text": "...",
      "type": "requirement|constraint|implementation_decision|failure_derived_constraint|procedure",
      "authority": "base_issue|base_hint|base_accepted_patch|user_instruction|manual_api",
      "source_evidence": "short source explanation",
      "critical_details": ["short condition/mapping/operator detail"],
      "risk": "low|medium|high"
    }
  ],
  "rejected": [
    {
      "text": "...",
      "reason": "..."
    }
  ]
}
```

Good decision examples:

```text
- For external inheritance-diagram refs where `internal` is false, derive the graph key from the `refuri` fragment after `#`, not from `reftitle`.
- For local inheritance-diagram `refid` anchors in SVG output, use `current_filename + '#' + refid`; do not prefix `../`.
- When keep_attrs is True for xr.where(cond, x, y), pass a callable to apply_ufunc that selects attrs[1], the attrs from x, not cond.
```

Bad decision examples:

```text
- For external references, extract the URI fragment if `reftitle` is not available.
- Preserve links correctly.
- Apply the exact accepted diff.
```

Input follows:

```text
{{BASE_TASK_ARTIFACTS}}
```
