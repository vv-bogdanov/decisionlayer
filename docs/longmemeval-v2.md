# LongMemEval-V2 Notes

## Official Sources

- Project page: https://xiaowu0162.github.io/longmemeval-v2/
- GitHub: https://github.com/xiaowu0162/LongMemEval-V2
- Hugging Face dataset: https://huggingface.co/datasets/xiaowu0162/longmemeval-v2
- Paper: https://arxiv.org/abs/2605.12493

The GitHub repository describes itself as the official LongMemEval-V2
repository and includes the evaluation harness, data preparation tools,
leaderboard packaging utilities, and memory baselines.

The default dataset repository is `xiaowu0162/longmemeval-v2`.

## License And Access

- Code repository license: Apache-2.0.
- Dataset license: Apache-2.0.
- Dataset files are public on Hugging Face.
- Full dataset size is large. The Hugging Face repository lists roughly 7.12 GB
  total, with `trajectories.jsonl` around 1.2 GB plus screenshot archives.

## Dataset Contents

Official dataset card:

- 451 manually curated questions.
- 1,870 task trajectories.
- Two domains: `web` and `enterprise`.
- Two haystack tiers:
  - `haystacks/lme_v2_small.json`
  - `haystacks/lme_v2_medium.json`
- Five memory abilities:
  - static state recall;
  - dynamic state tracking;
  - workflow / procedure knowledge;
  - environment gotchas;
  - premise awareness.

## Core Files

Expected local data root:

```text
questions.jsonl
trajectories.jsonl
haystacks/lme_v2_small.json
haystacks/lme_v2_medium.json
question_screenshots/
trajectory_screenshots/
```

For the first text-only POC path, screenshots are not required unless a selected
question has a non-null `image` field or the chosen backend uses trajectory
screenshots.

## Schema Summary

`questions.jsonl` fields:

- `id`
- `domain`
- `environment`
- `question_type`
- `question`
- `image`
- `answer`
- `eval_function`

`trajectories.jsonl` fields:

- `id`
- `domain`
- `environment`
- `goal`
- `outcome`
- `start_url`
- `states`

Each trajectory state includes:

- `state_index`
- `step`
- `url`
- `action`
- `thought`
- `accessibility_tree`
- `screenshot`

Haystack files map each `question_id` to an ordered list of trajectory ids.

## Official Memory Backend Interface

The official harness uses a memory backend API:

```text
insert(trajectory)
query(question, query_image=None) -> list[{"type": "text" | "image", "value": str}]
```

This maps cleanly to the Decision Layer proof design:

```text
D0: same backend returns normal memory context.
D1: same backend + oracle/manual Decision Brief.
D2: same backend + automatically extracted Decision Brief.
```

For the first POC, keep our adapter independent from the official harness. Read
the local data root directly, run small deterministic fixtures in tests, and use
the official harness only when we are ready to compare against released
baselines.

## First Adapter Scope

The first adapter should:

- read `questions.jsonl`;
- read one haystack file by tier;
- select a small deterministic subset;
- stream `trajectories.jsonl` and keep only trajectory ids required by the
  selected questions;
- expose examples with question metadata, answer, and trajectory objects;
- avoid downloading data inside the runner.

The adapter should not:

- download the dataset;
- extract screenshot archives;
- depend on PyTorch;
- implement the official reader model;
- implement SOTA memory backends.

## Local Scoring Scope

The POC scorer implements the deterministic LongMemEval-V2 answer checks used
by the downloaded questions:

- `norm_phrase_set_match`
- `norm_phrase_set_match_ordered`
- `mc_choice_match`
- `mc_choice_set_match`

The scorer marks `llm_abstention_checker` and `llm_gotchas_checker` as
unsupported unless an evaluator backend is added. Runs report
`scorable_examples` and `unsupported_examples`, so judge-only questions do not
silently become exact-match scores.
