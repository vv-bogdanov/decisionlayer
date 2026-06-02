# ТЗ для coding-агента

## Research prototype: Decision-First Agent Memory + Benchmark Harness

**Версия:** v0.1  
**Статус:** development task / research prototype  
**Язык:** RU  
**Цель этапа:** быстро проверить архитектуру на существующих memory benchmarks.

---

## 1. Цель

Разработать исследовательский прототип системы памяти агента на базе архитектуры:

```text
Agent Memory = Decisions + Facts
```

Главная задача прототипа — не production SDK и не интеграции, а **проверка гипотезы на существующих memory benchmarks**.

Нужно получить воспроизводимый pipeline, который позволяет:

```text
1. Запускать разные варианты памяти.
2. Подключать существующие benchmark-и.
3. Сравнивать качество с baselines.
4. Подбирать гиперпараметры recall/extraction/forgetting.
5. Собирать отчёты с метриками.
```

---

## 2. Что разрабатываем

Нужно сделать **Python research prototype**.

Rust, Node.js SDK, Python SDK как продукт, REST API, LangChain/LlamaIndex/Mem0-compatible adapters и production storage пока не нужны.

Фокус:

```text
Core memory prototype
Benchmark runners
Experiment configs
Hyperparameter sweeps
Reports
```

---

## 3. Архитектурная идея

Память состоит из двух типов записей.

### 3.1. Decision

`Decision` — текущее принятое решение, по которому агент действует.

Минимально:

```text
kind = decision
key
value
scope
refs
meta
```

Пример:

```text
key: project.mvp.database
value: SQLite
scope: project:localhelper
```

Решение создаётся или обновляется только при явном commit-сигнале.

Если новое решение имеет тот же `key + scope`, оно заменяет старое. Старое значение сохраняется как факт истории.

### 3.2. Fact

`Fact` — всё, что было сказано, извлечено, замечено, предположено, получено из источника или сохранено как история.

Минимально:

```text
kind = fact
text
scope
recallCount
tags
refs
meta
```

Фактом может быть:

```text
observation
hypothesis
error
history
decision_change
evidence
reason
source
test_result
tool_result
```

Гипотеза — это fact с тегом `hypothesis`.

Ошибка — это fact с тегом `error`.

История изменения решения — это fact с тегом `decision_change`.

### 3.3. Refs

`refs` — ссылки внутри facts/decisions на источники и связанные объекты.

Минимально:

```text
target
rel
weight
```

Возможные `rel`:

```text
source
based_on
supports
contradicts
explains
replaces
related
caused_by
evidence
derived_from
```

`refs` должны позволять потом строить graph index, source tracing, evidence tracking и multimodal references без изменения ядра.

### 3.4. recallCount

У факта нет “силы”, “важности” или “истинности” в ядре.

Есть только:

```text
recallCount — сколько раз факт вспоминался / попадал в Memory Brief
```

Принцип:

```text
чем чаще факт вспоминается, тем лучше он помнится
```

При recall:

```text
1. Находим релевантные facts.
2. Среди релевантных учитываем recallCount.
3. В Memory Brief попадает top-N.
4. Facts из Memory Brief получают recallCount++.
```

---

## 4. Core API прототипа

Нужен минимальный API:

```text
add_raw_input(...)
add_fact(...)
set_decision(...)
recall(...)
forget_facts(...)
export_trace(...)
```

### 4.1. add_raw_input

Сохраняет сырые данные:

```text
chat message
assistant message
tool output
file text
test output
benchmark episode
```

В MVP достаточно текстовых raw inputs. Мультимодальные refs предусмотреть в модели, но не реализовывать глубоко.

### 4.2. add_fact

Добавляет fact/hypothesis/error/history/evidence.

### 4.3. set_decision

Создаёт или обновляет decision.

Если `key + scope` уже есть, старое значение должно быть сохранено как fact с тегами:

```text
history
decision_change
```

### 4.4. recall

Возвращает Memory Brief:

```text
relevant decisions
top facts
related facts via refs if enabled
trace
```

### 4.5. forget_facts

Удаляет или архивирует facts по стратегии forgetting.

В MVP можно сделать простую стратегию:

```text
удалять/скрывать редко вспоминаемые facts,
если они не связаны с decisions
```

### 4.6. export_trace

Возвращает диагностическую информацию:

```text
какие decisions попали в brief
какие facts попали в brief
почему они выбраны
какие refs раскрыты
как изменился recallCount
```

Это критично для benchmark debugging.

---

## 5. Плагины / политики

Система должна позволять подменять политики через конфиг.

### 5.1. Extraction policies

Варианты:

```text
manual_oracle
rule_based
llm_extractor
llm_extractor_with_safety
```

Для первых прогонов допустимо начать с простых эвристик и/или LLM extraction.

Важно: extraction должна отдельно извлекать:

```text
facts
hypotheses
decision updates
refs
tags
```

### 5.2. Recall policies

Варианты:

```text
recent_only
keyword
vector
hybrid
decision_first
decision_first_with_recall_count
decision_first_with_refs_expansion
```

### 5.3. Forgetting policies

Варианты:

```text
none
low_recall_count
low_recall_count_except_decision_refs
age_plus_low_recall_count
```

### 5.4. Safety policies

Минимально проверить:

```text
не сохранять decision без явного commit-сигнала
не обновлять decision без key/value/scope
для важных updates создавать history fact
для важных facts/decisions сохранять source refs
```

---

## 6. Benchmark Harness

Нужен единый слой запуска benchmark-ов.

Общий pipeline:

```text
1. Load benchmark dataset.
2. Feed conversation/history/events into memory runtime.
3. Run memory recall for each benchmark question/task.
4. Generate answer using configured LLM or benchmark reader.
5. Score answer.
6. Save traces and metrics.
```

Benchmark harness должен быть независим от конкретной memory policy.

---

## 7. Подключаемые benchmark-и

### 7.1. LongMemEval

Подключить как один из первых benchmark-ов.

Цель проверки:

```text
information extraction
multi-session reasoning
temporal reasoning
knowledge updates
abstention
```

Особенно важны:

```text
knowledge updates
temporal reasoning
abstention
```

Они хорошо проверяют нашу модель decisions/facts/history.

### 7.2. LoCoMo

Подключить после LongMemEval или параллельно.

Цель проверки:

```text
long-term conversational memory
QA over long conversations
event summarization
temporal facts
multi-session memory
```

LoCoMo важен, потому что по нему часто сравнивают memory systems.

### 7.3. HaluMem

Подключить для проверки memory hallucinations.

Цель проверки:

```text
memory extraction hallucinations
memory updating hallucinations
memory QA hallucinations
```

Особенно важно для нашей архитектуры:

```text
false fact creation
false decision creation
wrong decision update
unsupported memory answer
```

### 7.4. MemoryAgentBench

Подключить для проверки agentic memory.

Цель проверки:

```text
accurate retrieval
test-time learning
long-range understanding
conflict resolution
```

Этот benchmark особенно интересен для проверки обновлений, противоречий и накопления опыта.

---

## 8. Baselines

Нужно реализовать минимум следующие baselines:

```text
B0: no_memory
B1: recent_context_only
B2: full_context_where_possible
B3: simple_rag
B4: fact_only_memory
B5: decisions_only_memory
B6: decisions_plus_facts
B7: decisions_plus_facts_plus_refs
B8: decisions_plus_facts_plus_refs_plus_recall_count
```

Цель — понять, что именно даёт прирост:

```text
facts
decisions
refs
recallCount
decision-first recall
forgetting
```

---

## 9. Конфиги и гиперпараметры

Вся система должна запускаться из конфигов.

Нужно предусмотреть конфигурацию:

```text
benchmark
model
embedding_model
extractor_policy
recall_policy
forgetting_policy
safety_policy
top_k_decisions
top_k_facts
refs_expansion_depth
refs_expansion_limit
recall_count_weight
keyword_weight
vector_weight
recency_weight
scope_weight
max_memory_brief_tokens
forgetting_threshold
```

Не все параметры должны быть задействованы сразу. Но архитектура должна позволять их добавлять.

---

## 10. Hyperparameter optimization

Нужно подготовить систему так, чтобы можно было запускать sweeps.

Рекомендуемый подход:

```text
Hydra для конфигов и multirun.
Optuna для автоматического подбора гиперпараметров.
```

Опционально позже:

```text
Ray Tune для масштабных параллельных запусков.
W&B для experiment tracking.
```

Задача coding-агента:

```text
1. Сделать конфиговую систему.
2. Сделать запуск одиночного эксперимента.
3. Сделать batch/multirun запуск.
4. Сделать Optuna objective, который оптимизирует выбранную метрику.
5. Сохранять результаты всех trial-ов.
```

Примеры оптимизируемых параметров:

```text
top_k_facts
top_k_decisions
recall_count_weight
keyword_weight
vector_weight
refs_expansion_depth
max_memory_brief_tokens
forgetting_threshold
```

Примеры целевых метрик:

```text
accuracy
F1
judge_score
source_traceability
false_decision_rate
prompt_tokens
latency
```

Нужна поддержка multi-objective scoring, хотя MVP может начать с одной главной метрики.

---

## 11. Метрики

### 11.1. Общие метрики

```text
accuracy
F1 / EM where applicable
LLM judge score where needed
latency
prompt tokens
memory brief tokens
cost estimate
```

### 11.2. Memory-specific метрики

```text
Fact Recall Precision
Fact Recall Coverage
Decision Persistence
Decision Update Correctness
False Decision Rate
Source Traceability
History Preservation
Forgetting Safety
Unsupported Claim Rate
```

### 11.3. Trace/debug метрики

```text
number of facts stored
number of decisions stored
number of raw inputs stored
average recallCount
facts selected per recall
decisions selected per recall
refs expanded per recall
```

---

## 12. Отчёты

После запуска экспериментов система должна генерировать:

```text
summary table
per-benchmark table
per-policy comparison
best hyperparameters
failure cases
sample traces
memory brief examples
```

Форматы:

```text
JSON
CSV
Markdown report
```

Желательно, чтобы по каждому прогону сохранялось:

```text
config
metrics
predictions
expected answers
memory trace
selected decisions/facts
```

---

## 13. Минимальная структура проекта

На верхнем уровне достаточно:

```text
core/
  memory model and operations

policies/
  extraction, recall, forgetting, safety variants

benchmarks/
  LongMemEval, LoCoMo, HaluMem, MemoryAgentBench adapters

baselines/
  no-memory, recent-only, full-context, RAG, fact-only

experiments/
  configs, runners, sweeps

reports/
  generated metrics and markdown reports
```

Точная структура на усмотрение coding-агента.

---

## 14. Non-goals для текущего этапа

Не делать сейчас:

```text
Rust rewrite
Node.js SDK
Python SDK как продукт
REST API
LangChain adapter
LlamaIndex adapter
Mem0-compatible adapter
production database
auth/multitenancy
UI/dashboard
custom benchmark
```

Разрешается делать минимальные CLI/скрипты только для запуска экспериментов.

---

## 15. Ожидаемые артефакты

К концу этапа должны быть:

```text
1. Python prototype ядра Decisions + Facts.
2. Подключён минимум один внешний benchmark.
3. Подготовлена структура для подключения остальных benchmark-ов.
4. Реализованы baselines:
   - recent-only
   - simple RAG
   - fact-only
   - decisions+facts
5. Реализован конфиговый запуск экспериментов.
6. Реализован Optuna/Hydra sweep pipeline.
7. Генерируется отчёт с метриками.
8. Сохраняются traces для debugging.
```

---

## 16. Приоритет выполнения

### P0

```text
Core memory model
addFact
setDecision
recall
exportTrace
baseline runners
one benchmark adapter
config system
```

### P1

```text
LongMemEval + LoCoMo
simple RAG baseline
fact-only baseline
decisions+facts baseline
report generator
```

### P2

```text
HaluMem
MemoryAgentBench
Optuna sweeps
refs expansion
forgetting variants
```

### P3

```text
advanced recall
LLM extraction safety
multi-objective optimization
failure analysis reports
```

---

## 17. Definition of Done

Этап считается завершённым, когда можно выполнить команду вида:

```text
run_experiment benchmark=LongMemEval memory=decisions_facts recall=decision_first
```

и получить:

```text
metrics.json
predictions.jsonl
trace.jsonl
report.md
```

Также должна быть возможность запустить sweep:

```text
run_sweep benchmark=LongMemEval memory=decisions_facts search=optuna
```

и получить:

```text
best_config.yaml
trials.csv
sweep_report.md
```

---

## 18. Главная цель этапа

Доказать или опровергнуть гипотезу:

```text
Decision-First Memory даёт измеримый выигрыш
по качеству, стабильности, обновлению знаний и объяснимости
по сравнению с fact-only, simple RAG и recent-context baselines.
```

После получения первых результатов принимать решение:

```text
какой recall работает лучше
нужны ли refs expansion / graph plugin
насколько полезен recallCount
как настраивать forgetting
когда имеет смысл переписывать ядро на Rust
```
