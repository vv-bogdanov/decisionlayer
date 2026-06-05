# ADR Standards Research Notes

This folder contains local copies of the ADR references used to shape the
Codex ADR Decision Plugin POC. The plugin should preserve the ADR style already
used in a repository and only fall back to its own template when no local ADR
convention exists.

## Downloaded Sources

- `sources/nygard-documenting-architecture-decisions.html`
  - Michael Nygard, "Documenting Architecture Decisions"
  - https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- `sources/adr-tools-readme.md`
  - Nat Pryce adr-tools README
  - https://github.com/npryce/adr-tools
- `sources/adr-tools-template.md`
  - Nat Pryce adr-tools default ADR template
  - https://github.com/npryce/adr-tools/blob/master/src/template.md
- `sources/adr-tools-0001-record-architecture-decisions.md`
  - adr-tools own first ADR example
  - https://github.com/npryce/adr-tools/blob/master/doc/adr/0001-record-architecture-decisions.md
- `sources/madr-4.0.0-adr-template.md`
  - MADR 4.0.0 full template
  - https://github.com/adr/madr/tree/4.0.0/template
- `sources/madr-4.0.0-adr-template-minimal.md`
  - MADR 4.0.0 minimal template
  - https://github.com/adr/madr/tree/4.0.0/template
- `sources/madr-4.0.0-adr-template-bare-minimal.md`
  - MADR 4.0.0 bare minimal template
  - https://github.com/adr/madr/tree/4.0.0/template
- `sources/adr-github-templates-overview.html`
  - ADR GitHub organization template overview
  - https://adr.github.io/adr-templates/
- `sources/architecture-decision-record-readme.md`
  - Architecture Decision Record template collection
  - https://github.com/architecture-decision-record/architecture-decision-record
- `sources/jph-template-michael-nygard.md`
  - Michael Nygard template from the template collection
- `sources/jph-template-madr.md`
  - MADR template from the template collection
- `sources/jph-template-tyree-akerman.md`
  - Tyree/Akerman template from the template collection
- `sources/arc42-section-9-architecture-decisions.html`
  - arc42 Architecture Decisions guidance
  - https://docs.arc42.org/section-9/
- `sources/aws-adr-process.html`
  - AWS Prescriptive Guidance ADR process
  - https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
- `sources/aws-adr-best-practices.html`
  - AWS Prescriptive Guidance ADR best practices
  - https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/best-practices.html
- `sources/ozimmer-architecture-decisions-making-of.html`
  - Olaf Zimmermann, Y-Statements and ADR practice notes
  - https://ozimmer.ch/practices/2020/04/27/ArchitectureDecisionMaking.html
- `sources/arxiv-2604.27333-adr-template-comparison.html`
  - 2026 empirical comparison of ADR templates
  - https://arxiv.org/abs/2604.27333

## What To Take

- Prefer repository convention over plugin convention.
  If a repo already has ADRs, create new ADRs with the same directory,
  numbering, heading names, date/status placement, and section order.
- Keep one ADR per significant decision.
  ADRs should capture decisions that are important, expensive, large-scale,
  risky, architecturally significant, or hard to reverse.
- Keep accepted ADRs immutable.
  After acceptance, do not content-edit an ADR through the tool. Use a new ADR
  to supersede the old one. The only tool mutation to an accepted ADR is marking
  it as superseded and linking to the replacement.
- Keep a status lifecycle.
  The parser should recognize common statuses such as proposed, accepted,
  rejected, deprecated, and superseded. The prompt brief includes only active
  accepted decisions.
- Keep the mandatory data small.
  The minimum useful structure is title, status, context, decision, and
  consequences. Date is valuable enough to include in the fallback template.
- Add considered options when creating new ADRs from scratch.
  MADR and arc42 both emphasize alternatives and tradeoffs; this is useful for
  future agents and humans. It should be optional when matching an existing repo
  format.
- Keep rationale explicit.
  A good ADR answers why this option was chosen, not just what implementation
  happened.
- Keep consequences honest.
  Include positive, negative, and neutral consequences. Do not hide tradeoffs.
- Keep docs short.
  Nygard's guidance is one or two pages. For this plugin, that maps to compact
  markdown files and a much smaller prompt brief.
- Use Y-Statements as a compact brief shape, not as the source-of-truth format.
  The brief can compress ADRs into lines shaped like:
  "In context X, facing Y, we decided Z, to achieve A, accepting B."

## Simplifications For The POC

- Do not implement `edit` for accepted ADRs.
- Do not implement a custom ADR schema.
- Do not implement a vector index, graph, database, or reranker.
- Do not generate a persistent brief cache until hook performance proves it is
  needed.
- Do not force MADR on existing repositories.
- Do not include proposed, rejected, deprecated, or superseded ADRs in the
  automatic prompt requirements block.

## Fallback Template Recommendation

Use this only when no ADR convention exists in the repository:

```md
# NNNN. Short Decision Title

Date: YYYY-MM-DD

## Status

Accepted

## Context and Problem Statement

What problem, force, constraint, or requirement motivates this decision?

## Considered Options

- Option A
- Option B

## Decision

We will ...

## Consequences

- Good, because ...
- Bad, because ...
```

This fallback is intentionally Nygard-compatible and borrows the most useful
MADR practice: considered options.

## Tool Behavior Recommendation

- `locate`: find ADR directory, template, format profile, and active count.
- `list`: show ADRs and statuses.
- `brief`: return the exact compact block the hook injects.
- `add`: create a new accepted ADR from explicit user-authorized input.
- `supersede`: create a replacement ADR and mark the old one superseded.
- `config`: read or write local/global default directories and limits.

No `edit` tool in the first POC. Manual git edits remain possible for humans,
but the plugin should not make accepted-decision mutation easy for agents.
