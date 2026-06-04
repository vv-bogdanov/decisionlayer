# Operational Decision Brief v0

## Purpose

Operational Decision Brief v0 is the coding-task variant of a Decision Brief.
It preserves compact accepted implementation decisions from a base task so an
agent can reuse them on a related task without receiving raw history, full
patches, hidden tests, or answer-specific information.

This is still Decision Layer content, not a memory system. Each item must be an
accepted decision, requirement, constraint, or implementation commitment.

## Authority

Allowed sources:

- base-task accepted patch, issue, hints, or accepted maintainer/user
  instruction;
- explicit user instruction;
- trusted manual API/tool call.

Disallowed sources:

- related-task hidden patch;
- related-task hidden tests;
- related-task final answer;
- post-hoc related-task grading result;
- assistant speculation;
- retrieved documents without user/manual authority.

Post-hoc related-task failures may be used for analysis and reports, but not as
proof-run Decision Brief content.

## Item Shape

Each bullet should be one short operational commitment, usually under 240
characters. Keep enough implementation detail that an agent cannot replace it
with a plausible but wrong abstraction.

Preferred item types:

- requirement: externally visible behavior that must hold;
- constraint: behavior that must not change;
- implementation decision: accepted local mechanism, extension point, argument
  mapping, operator choice, or invariant;
- failure-derived constraint: a stable lesson from an authorized base-task
  failed attempt.

Avoid:

- raw patches;
- line-by-line edit instructions;
- full test logs;
- vague summaries such as "preserve attrs correctly";
- arbitrary facts about files or APIs without an accepted action.

## Good Examples

```text
- Add a keep_attrs argument to global xr.where; if omitted, resolve it with xarray's global keep_attrs option.
- When keep_attrs is True for xr.where(cond, x, y), pass a callable to apply_ufunc that selects attrs[1], the attrs from x, not cond.
- For parser-created unevaluated calls, EvaluateFalseTransformer is the extension point; parser-only changes may still need function doit/eval path checks.
- When deconstructing an expression alias, use the shortest import path accepted by Django migrations, not the module where the class happens to live.
```

## Bad Examples

```text
- xarray has attrs.
- Look at computation.py around where().
- The hidden test is test_where_attrs.
- Apply the exact following diff: ...
- Maybe use a callable if needed.
```

## D2 Extraction Schema

D2 extractors should produce strict JSON:

```json
{
  "decisions": [
    {
      "text": "When keep_attrs is True for xr.where(cond, x, y), pass a callable to apply_ufunc that selects attrs[1], the attrs from x, not cond.",
      "type": "implementation_decision",
      "authority": "base_accepted_patch",
      "source_evidence": "Base patch converts keep_attrs=True to a callable before apply_ufunc.",
      "risk": "low"
    }
  ],
  "rejected": [
    {
      "text": "The related hidden test checks test_where_attrs.",
      "reason": "related-task hidden-test leakage"
    }
  ]
}
```

Allowed `type` values:

```text
requirement
constraint
implementation_decision
failure_derived_constraint
procedure
```

Allowed `authority` values:

```text
base_issue
base_hint
base_accepted_patch
user_instruction
manual_api
```

Risk values:

```text
low
medium
high
```

Use `risk=high` when the item might be overfit, speculative, or not clearly
authorized. High-risk decisions should be manually reviewed before D1/D2 runs.

## D2 Extraction Prompt Template

```text
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

Return strict JSON with keys decisions and rejected. Do not include markdown.

Rules:
- Extract only accepted decisions, requirements, constraints, procedures, and
  implementation commitments.
- Preserve implementation-critical details: argument mapping, operator choice,
  extension point, callable/index choice, invariant, fallback/default policy.
- Do not copy raw patch hunks. Do not include file locations unless the file is
  the accepted extension point.
- Better reject an uncertain item than create a false decision.
- Each decision text should be short enough to fit as a prompt bullet.

Schema:
{
  "decisions": [
    {
      "text": "...",
      "type": "requirement|constraint|implementation_decision|failure_derived_constraint|procedure",
      "authority": "base_issue|base_hint|base_accepted_patch|user_instruction|manual_api",
      "source_evidence": "short source explanation",
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

## Audit Checklist

- Does every item trace to an allowed base-task source?
- Would the item still be valid if the related task asked a different question
  in the same code area?
- Is it more actionable than a generic requirement?
- Is it shorter than a patch but specific enough to prevent the known wrong
  abstraction?
- Does it avoid hidden related-task information?

## Proof-Run Hygiene

Coding benchmark workspaces must not expose future repository history to the
agent. Prefer a sanitized single-commit checkout built from the target base
commit, and forbid `git log`, `git show`, and `git blame` in the agent prompt.

Every proof run should save enough artifacts to explain failures without
rerunning completed cases:

- prompt and Decision Brief used by the agent;
- structured agent event log, preferably JSONL;
- stderr and wall-clock timing;
- pre-run and post-run diff;
- blocked-command audit or guard-bin logs;
- official grading report and grading timing.

Before official grading, run a lightweight patch/brief verifier when the brief
contains critical implementation commitments. The verifier should fail fast if
required terms or files are absent from the generated patch, or if the patch
touches files outside a narrow allowlist.

Example:

```text
decision-layer verify-patch \
  --patch patch.diff \
  --require-term visit_Subscript \
  --require-term is_simple_tuple \
  --require-file sphinx/pycode/ast.py \
  --allow-file sphinx/pycode/ast.py
```

Alternative local agents or subagents are useful for diagnosis, but they should
not replace the predeclared D0/D1/D2 runner in the proof table unless the whole
slice is rerun with that same runner and model.

When delegating log audits to a local helper, start the helper from the artifact
directory or pass repo-local summaries. Absolute paths outside the helper's
working directory may be blocked even for read-only commands.
