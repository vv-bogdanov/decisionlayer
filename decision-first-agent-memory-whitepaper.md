# Decision-First Agent Memory

## Минимальная архитектура памяти для LLM/VLM-агентов

**Версия:** v0.2  
**Статус:** concept whitepaper / architecture proposal  
**Язык:** draft RU  
**Ключевая формула:** `Agent Memory = Decisions + Facts`

---

## Abstract

Современные LLM-агенты всё чаще получают внешнюю память: long-term memory, retrieval, knowledge graphs, memory blocks, multimodal stores и learned memory policies. Большинство таких подходов фокусируется на вопросе: **«что агент должен вспомнить?»**

Мы предлагаем другой базовый фокус: **«по каким принятым решениям агент должен действовать?»**

В этой архитектуре память агента состоит из двух минимальных ролей:

```text
Decisions — текущие принятые решения, управляющие поведением агента.
Facts     — сохранённые факты, наблюдения, гипотезы, ошибки, evidence и история.
```

Решения задают текущее поведение агента. Факты дают опыт, основания, источники и материал для пересмотра решений. Всё остальное — retrieval, graph reasoning, multimodal memory, safety checks, forgetting, learned policies — подключается поверх ядра как плагины.

Цель архитектуры — получить компактное, объяснимое и расширяемое ядро памяти, которое подходит для dev-агентов, персональных ассистентов, multi-agent workflows и долгоживущих LLM/VLM-систем.

---

## 1. Проблема

LLM-агенты сталкиваются с несколькими устойчивыми проблемами памяти.

### 1.1. Ограниченный контекст

Агент не может держать всю историю общения, файлов, tool outputs, решений и ошибок в prompt.

### 1.2. Нестабильность поведения

Агент может сегодня выбрать один подход, завтра предложить другой, а через неделю забыть, почему было принято исходное решение.

### 1.3. Смешение фактов и решений

Многие системы памяти хранят «важные воспоминания», но не различают:

- что было сказано;
- что является гипотезой;
- что уже принято как решение;
- по чему агент теперь должен действовать.

### 1.4. Потеря оснований

Если агент извлёк краткий факт из длинного контекста, но потерял ссылку на исходное сообщение, файл, скриншот или tool output, дальнейшие решения могут опираться на искажённую память.

### 1.5. Overengineering

Разделение на episodic, semantic, procedural, reflective, multimodal, short-term, long-term и другие типы памяти часто полезно на уровне реализации, но может перегрузить архитектурное ядро.

### 1.6. Prompt pollution

Если в контекст автоматически подмешивается слишком много памяти, модель начинает хуже рассуждать, путаться или цепляться за нерелевантные детали.

### 1.7. Memory hallucinations

Ошибки могут возникать не только при генерации ответа, но и при извлечении, обновлении, связывании и использовании памяти.

Нужна архитектура, которая сохраняет полезные свойства современных SOTA-подходов, но не превращает ядро памяти в сложную онтологию.

---

## 2. Design Goals

### 2.1. KIS-core

Ядро должно быть минимальным:

```text
Agent Memory = Decisions + Facts
```

Никакие retrieval-алгоритмы, graph databases, vector stores, multimodal indexes или learned policies не должны быть обязательной частью ядра.

### 2.2. Decision-first behavior

Агент должен действовать не по всей истории, а по текущим принятым решениям.

Пример:

```text
architecture.style = KIS
assistant.language = russian
code.comments.language = english
memory.fact_retention = recall_count_based_forgetting
```

Такие записи являются не «воспоминаниями», а текущими установками поведения.

### 2.3. Facts as experience

Факты хранят всё остальное:

```text
наблюдения
утверждения пользователя
ошибки
гипотезы
историю изменений решений
аргументы
evidence
source references
tool outputs
выводы агента
```

Факт в этой архитектуре не обязан быть «объективной истиной». Это сохранённая запись о том, что было сказано, получено, извлечено, замечено или предположено.

Примеры:

```text
«Пользователь предложил хранить refs внутри facts/decisions.»
```

Это факт о содержании обсуждения.

```text
«Возможно, SQLite лучше для MVP.»
```

Это факт-гипотеза.

```text
«Сборка упала из-за команды build.»
```

Это факт-ошибка.

### 2.4. Evidence-aware memory

Важные факты и решения должны ссылаться на источник:

```text
raw chat message
file
screenshot
image
audio
video
tool output
test result
web source
commit
external object
```

Память не должна заменять исходные данные. Она должна уметь на них ссылаться.

### 2.5. Plugin-based SOTA expansion

Сложные возможности должны подключаться поверх ядра:

```text
retrieval
graph reasoning
temporal reasoning
multimodal memory
reflection
hallucination checks
learned memory policies
storage adapters
```

Ядро остаётся тем же.

---

## 3. Core Model

Физически вся память может быть представлена одной универсальной сущностью:

```text
MemoryItem(kind = "decision" | "fact")
```

Концептуально остаются две роли:

```text
Decision — текущее принятое решение.
Fact     — всё остальное знание, опыт, гипотезы, ошибки, evidence и история.
```

---

## 4. Decisions

`Decision` — это текущий принятый выбор, по которому агент должен действовать.

Решение отвечает на вопрос:

```text
Как мы теперь решили действовать?
```

Решение не является утверждением об истине. Оно является принятой установкой поведения.

### 4.1. Decision structure

Минимально решение содержит:

```text
key
value
scope
refs
meta
```

Пример:

```text
kind: decision
key: memory.core
value: decisions + facts
scope: project:agent-memory
refs:
  - rel: based_on
    target: fact_user_wants_kis_core
```

### 4.2. Decision as key/value/scope

Решение должно быть выразимо как:

```text
key + value + scope
```

Если утверждение невозможно выразить в таком виде, оно не должно становиться решением. Оно сохраняется как факт или гипотеза.

Пример гипотезы:

```text
«Возможно, стоит использовать SQLite.»
```

Это факт:

```text
kind: fact
tags: ["hypothesis"]
text: "Возможно, стоит использовать SQLite."
```

Пример решения:

```text
«Фиксируем: для MVP используем SQLite.»
```

Это decision:

```text
kind: decision
key: project.mvp.database
value: SQLite
scope: project:mvp
```

### 4.3. Decision update

Решения хранятся как текущее состояние.

Если новое решение имеет тот же `key` и тот же `scope`, оно заменяет старое значение.

Старое значение не остаётся текущим решением. История изменения записывается как факт.

Пример:

```text
Было:
project.mvp.database = SQLite

Стало:
project.mvp.database = PostgreSQL
```

В текущих Decisions остаётся:

```text
project.mvp.database = PostgreSQL
```

В Facts добавляется:

```text
kind: fact
tags: ["history", "decision_change"]
text: "Решение project.mvp.database изменено: SQLite → PostgreSQL."
refs:
  - rel: source
    target: raw_message_id
  - rel: replaces
    target: previous_decision_value
```

Такое правило убирает необходимость в сложной state machine для решений.

---

## 5. Facts

`Fact` — это всё, что агент знает, наблюдал, извлёк, предположил, получил из источника или сохранил как историю.

Факт отвечает на вопрос:

```text
Что известно, сказано, произошло, наблюдалось или предполагается?
```

В Facts попадают:

```text
наблюдения
утверждения пользователя
извлечённые факты
результаты действий
ошибки
гипотезы
аргументы
история изменений решений
evidence
source summaries
raw input references
выводы агента
```

### 5.1. Fact structure

Минимально факт содержит:

```text
text
scope
recallCount
tags
refs
meta
```

Пример:

```text
kind: fact
scope: project:agent-memory
text: "Пользователь хочет максимально компактное ядро памяти."
tags: ["observation", "reason"]
recallCount: 3
refs:
  - rel: source
    target: raw_chat_message_id
```

### 5.2. Fact is a record, not an authority

Факт не означает, что агент обязан считать утверждение истинным или действовать по нему.

Факт означает:

```text
это было сказано / извлечено / замечено / получено / предположено / сохранено
```

Для сомнительных, гипотетических или внешних утверждений используются `tags`, `refs` и `meta`.

Примеры:

```text
tags: ["hypothesis"]
tags: ["external_claim"]
tags: ["error"]
tags: ["user_statement"]
tags: ["tool_result"]
```

Источник должен быть доступен через `refs`.

### 5.3. Tags

`tags` — это свободные роли факта.

Примеры:

```text
observation
hypothesis
error
history
decision_change
evidence
reason
source
raw
summary
test_result
external_claim
user_statement
tool_result
```

Гипотеза — это факт с тегом:

```text
hypothesis
```

Ошибка — это факт с тегом:

```text
error
```

История изменения решения — это факт с тегом:

```text
decision_change
```

---

## 6. Refs

`refs` — универсальный механизм ссылок внутри Decisions и Facts.

Ссылка может указывать на:

```text
другой факт
другое решение
сырое сообщение чата
эпизод диалога
файл
изображение
скриншот
аудио
видео
tool output
результат теста
web-источник
коммит
внешний объект
```

Минимальный формат:

```text
target
rel
weight
```

Примеры отношений:

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

`refs` позволяют строить поверх ядра:

```text
graph index
evidence tracking
source tracing
causal links
multimodal memory
temporal graph
multi-hop recall
```

Важно: `refs` не являются отдельной сущностью ядра. Это обычное поле внутри Decisions и Facts.

---

## 7. Raw Inputs / Episodes

Система должна предусматривать сохранение сырых входных данных.

К сырым данным относятся:

```text
сообщения пользователя
ответы ассистента
tool outputs
файлы
изображения
скриншоты
аудио
видео
логи
результаты тестов
внешние документы
```

Facts и Decisions должны уметь ссылаться на эти данные через `refs`.

Пример:

```text
kind: fact
text: "Пользователь предложил хранить refs внутри facts/decisions."
refs:
  - rel: source
    target: raw_message_2026_06_02_15_42
```

Это защищает память от потери смысла при extraction: всегда можно вернуться к исходному источнику.

---

## 8. RecallCount

Факты имеют `recallCount` — счётчик вспоминаний.

Факт усиливается не потому, что он «важнее» или «истиннее», а потому что он чаще попадал в Memory Brief и использовался в работе агента.

Базовое правило:

```text
чем чаще факт вспоминается, тем лучше он помнится
```

При recall:

```text
1. Сначала находятся релевантные facts.
2. Среди релевантных выше поднимаются facts с большим recallCount.
3. В Memory Brief попадает top-N facts.
4. Facts, попавшие в Memory Brief, получают recallCount++.
```

Концептуальная формула:

```text
factScore = relevance(context, fact) + recallBoost(recallCount)
```

Точная формула не является частью ядра и может задаваться Recall Plugin.

Краткосрочная и долгосрочная память не являются отдельными сущностями.

```text
short-term / long-term = разные уровни recallCount и частоты попадания в контекст
```

---

## 9. Forgetting

Решения не забываются автоматически. Они только обновляются новыми решениями.

Факты могут забываться автоматически по принципу использования.

Кандидаты на забывание:

```text
факты с низким recallCount
факты, которые давно не попадали в Memory Brief
факты без связей с текущими решениями
дублирующиеся факты
факты без useful refs/source
```

Факт защищён от быстрого забывания, если он:

```text
является основанием текущего решения
связан с ошибкой или исправлением
имеет важный source/evidence
часто вспоминается
явно закреплён
```

Такой подход позволяет сохранять широкую фактологическую память без бесконечного роста активного контекста.

---

## 10. Memory Brief

Перед ответом агент получает не всю память, а компактный `Memory Brief`.

Он формируется автоматически из:

```text
релевантных текущих решений
релевантных часто вспоминаемых фактов
связанных фактов через refs
актуальных гипотез, если задача связана с выбором
ошибок и противоречий, если они касаются текущего действия
evidence/source refs при необходимости
```

Приоритет:

```text
1. Текущие решения
2. Факты, связанные с этими решениями
3. Релевантные факты с высоким recallCount
4. Гипотезы по текущему вопросу
5. Evidence/source refs при необходимости
```

Пример:

```text
Decisions:
- memory.core = decisions + facts
- memory.fact_retention = recall_count_based_forgetting
- architecture.style = KIS

Facts:
- Пользователь хочет максимально компактное ядро.
- Решения хранятся как текущий key/value/scope.
- Старые решения сохраняются как facts/history.
- Гипотезы являются facts с тегом hypothesis.
```

---

## 11. Errors and Decision Revision

Ошибка сохраняется как факт.

Пример:

```text
kind: fact
tags: ["error"]
text: "Сборка упала из-за выбранной команды build."
refs:
  - rel: contradicts
    target: decision_build_command
  - rel: source
    target: test_output_id
```

После ошибки агент может создать гипотезу:

```text
kind: fact
tags: ["hypothesis"]
text: "Возможно, build.command нужно изменить."
refs:
  - rel: based_on
    target: error_fact_id
```

Если гипотеза принимается, она становится новым решением:

```text
kind: decision
key: build.command
value: new_command
scope: project
```

Старое значение сохраняется как факт истории.

Ошибка не должна автоматически менять решение. Она должна запускать создание гипотезы о пересмотре решения.

---

## 12. Core Operations

Минимальный набор операций:

```text
addFact(text, scope, tags?, refs?, meta?)
setDecision(key, value, scope, refs?, meta?)
recall(context)
forgetFacts()
```

### 12.1. addFact

Добавляет новый факт:

```text
наблюдение
гипотезу
ошибку
историю
evidence
source summary
test result
```

### 12.2. setDecision

Создаёт или обновляет текущее решение.

Если решение с таким `key + scope` уже было, старое значение записывается как факт истории.

### 12.3. recall

Формирует Memory Brief:

```text
relevant decisions
top facts
related facts via refs
source/evidence refs if needed
```

Конкретный алгоритм recall не является частью ядра.

### 12.4. forgetFacts

Удаляет или архивирует редко вспоминаемые факты.

Конкретная стратегия забывания не является частью ядра.

---

## 13. Plugin Architecture

Ядро должно быть независимым от конкретных алгоритмов.

Поверх ядра подключаются внешние органы — плагины.

### 13.1. Extractor Plugin

Извлекает из входящих данных:

```text
facts
hypotheses
decision updates
refs
tags
meta
```

Может быть:

```text
rule-based
LLM-based
hybrid
learned
```

### 13.2. Recall Plugin

Формирует Memory Brief.

Возможные стратегии:

```text
semantic search
keyword search
hybrid retrieval
scope matching
refs expansion
graph traversal
reranking
time-aware retrieval
decision-first retrieval
recallCount-aware retrieval
```

Recall plugin должен быть заменяемым, чтобы можно было тестировать разные подходы.

### 13.3. Graph Index Plugin

Строит граф поверх `refs`.

Не является частью ядра.

Может использоваться для:

```text
multi-hop retrieval
temporal graph reasoning
causal tracing
dependency analysis
decision reasoning
entity graph
```

### 13.4. Raw Episode Storage Plugin

Сохраняет сырые эпизоды и входные данные:

```text
chat messages
files
screenshots
images
audio
video
tool outputs
logs
test outputs
documents
```

Facts и Decisions ссылаются на эти данные через `refs`.

### 13.5. Multimodal Memory Plugin

Работает с изображениями, видео, аудио и экраном.

Может добавлять:

```text
OCR facts
ASR facts
image embeddings
frame embeddings
object references
screenshot refs
visual evidence refs
```

Ядро при этом не меняется.

### 13.6. Linker Plugin

Создаёт и обновляет `refs`.

Может находить:

```text
какие факты поддерживают решение
какие факты противоречат решению
какие ошибки связаны с каким решением
какие факты являются source/evidence
какие элементы памяти связаны тематически
```

### 13.7. Forgetting Plugin

Управляет удалением или архивированием фактов.

Может учитывать:

```text
recallCount
свежесть
связь с решениями
наличие source refs
ошибочность
дублирование
явное закрепление
```

### 13.8. Reflection Plugin

Анализирует ошибки и результаты действий.

Задачи:

```text
сохранять ошибки как facts
искать связанные decisions
создавать hypothesis facts
предлагать обновление решений
не менять решения без принятия гипотезы
```

### 13.9. Hallucination / Safety Plugin

Проверяет качество операций памяти.

Особенно важно проверять:

```text
не принял ли агент рассуждение за решение
не выдумал ли fact
есть ли source refs у важных facts
есть ли source refs у изменений decisions
не созданы ли ложные refs
```

### 13.10. Learned Memory Policy Plugin

Опциональный слой, который может обучаться на результатах использования памяти.

Может оптимизировать:

```text
что сохранять
что вспоминать
что забывать
какие refs усиливать
какие facts считать полезными
как формировать Memory Brief
```

Ядро при этом не меняется.

### 13.11. Storage Adapter

Хранит MemoryItems и raw inputs.

Возможные backend'ы:

```text
in-memory
file-based
SQLite
Postgres
Vector DB
Graph DB
object storage
hybrid storage
```

Storage adapter не должен менять модель ядра.

---

## 14. Quality Discipline

Для сильной памяти нужны обязательные правила.

### 14.1. Source refs

Важные facts и decisions должны иметь ссылку на источник.

Особенно:

```text
decision
decision_change
error
accepted hypothesis
important evidence
```

### 14.2. Decision safety

Decision создаётся или обновляется только при явном commit-сигнале.

Если commit-сигнала нет, информация сохраняется как fact или hypothesis.

### 14.3. Reason refs

Важные decisions должны иметь ссылки на основания:

```text
refs:
  - rel: based_on
    target: fact_id
```

Это позволяет отвечать на вопрос:

```text
Почему мы так решили?
```

### 14.4. Raw preservation

Сырые входные данные должны быть доступны через `refs`.

Facts не должны быть единственным источником того, что было сказано, показано или получено.

### 14.5. Evaluation

Нужно тестировать не только ответы агента, но и операции памяти:

```text
fact extraction
decision extraction
decision update
source refs
recall quality
forgetting
hypothesis -> decision
error -> hypothesis
false decision prevention
```

---

## 15. Comparison with Existing Directions

Современные agent memory системы можно условно разделить на несколько направлений:

1. **Selective long-term memory.**  
   Системы, которые извлекают и достают наиболее важные memories из долгих диалогов.

2. **Stateful agent memory.**  
   Подходы, где агент имеет устойчивое состояние и может управлять своим контекстом.

3. **Temporal knowledge graph memory.**  
   Подходы, где память строится как граф сущностей, отношений, источников и времени.

4. **Multimodal memory.**  
   Системы, которые сохраняют и вспоминают визуальные, аудио и экранные данные.

5. **Learned memory management.**  
   Подходы, где правила записи, обновления, удаления и recall обучаются на опыте.

Предлагаемая архитектура не конкурирует с каждым из этих направлений на уровне конкретного retrieval-алгоритма. Она предлагает минимальное ядро, к которому эти направления могут подключаться как внешние органы.

Главное отличие:

```text
Большинство подходов фокусируется на том, что вспомнить.
Decision-First Memory дополнительно фиксирует, по каким текущим решениям агент должен действовать.
```

---

## 16. Evaluation Plan

Для проверки архитектуры нужны benchmark-и и собственные сценарии.

Минимальные метрики:

```text
Decision persistence
  агент помнит текущие решения

Decision update correctness
  старые решения корректно уходят в history facts

False decision rate
  агент не превращает рассуждения в решения

Fact recall precision
  в Memory Brief попадают полезные facts

Fact recall coverage
  нужные facts не теряются

Source traceability
  важные facts/decisions имеют source refs

Forgetting quality
  редко вспоминаемые facts уходят, важные остаются

Error reflection quality
  ошибки приводят к полезным hypothesis facts

Prompt efficiency
  Memory Brief компактный и не загрязняет контекст
```

Дополнительно нужно сравнивать:

```text
Decision-First Memory vs full-context
Decision-First Memory vs simple vector memory
Decision-First Memory vs Mem0-like selective memory
Decision-First Memory + graph plugin vs temporal graph memory
Decision-First Memory + multimodal plugin vs multimodal memory baselines
```

---

## 17. Expected Contributions

Архитектура предлагает несколько вкладов:

1. **Decision-first memory model.**  
   Отдельное представление текущих принятых решений как управляющего состояния агента.

2. **Minimal core.**  
   Вся память сводится к Decisions и Facts.

3. **Facts as universal experience layer.**  
   Наблюдения, ошибки, гипотезы, evidence, история и аргументы хранятся как facts с тегами.

4. **Refs as universal connectivity.**  
   Связи, источники, evidence и graph-поведение реализуются через `refs`.

5. **RecallCount вместо short/long memory types.**  
   Разные уровни запоминаемости выражаются через частоту вспоминания, а не через отдельные типы памяти.

6. **Plugin-based SOTA expansion.**  
   Retrieval, graph reasoning, multimodal memory, safety и learned policies развиваются независимо от ядра.

---

## 18. Roadmap

### Stage 1 — Core MVP

```text
MemoryItem
Decisions
Facts
refs
tags
meta
recallCount

addFact
setDecision
recall
forgetFacts
```

### Stage 2 — Raw Preservation

```text
raw message storage
tool output storage
file/image/screenshot refs
source refs for important facts/decisions
```

### Stage 3 — Recall Experiments

```text
simple recall
semantic recall
hybrid recall
decision-first recall
recallCount-aware recall
refs expansion
reranking
```

### Stage 4 — Reflection

```text
error facts
related decisions
hypothesis creation
decision revision workflow
```

### Stage 5 — Graph / Multimodal / Learned Plugins

```text
graph index
temporal retrieval
multimodal evidence memory
learned memory policies
hallucination/safety checks
```

### Stage 6 — Benchmarks

```text
custom decision-memory benchmark
LoCoMo-style long-dialogue tests
LongMemEval-style multi-session tests
HaluMem-style memory-operation tests
coding-agent workflow tests
```

---

## 19. Summary

Decision-First Agent Memory предлагает минимальную архитектуру памяти для долгоживущих LLM/VLM-агентов.

Ядро:

```text
Agent Memory = Decisions + Facts
```

Где:

```text
Decisions — текущие принятые выборы, управляющие поведением.
Facts     — опыт, наблюдения, ошибки, гипотезы, evidence и история.
```

`refs`, `tags`, `meta` и `recallCount` дают достаточно гибкости, чтобы поверх ядра строить graph memory, multimodal memory, source tracing, reflection, learned policies и SOTA retrieval.

Главная идея:

```text
Решения управляют поведением.
Факты дают опыт и основания.
Чем чаще факт вспоминается, тем лучше он помнится.
Плагины дают SOTA-возможности без усложнения ядра.
```

---

## 20. Reference Directions

Этот whitepaper позиционируется относительно следующих направлений и benchmark-семейств:

- Mem0-like selective long-term memory;
- Zep/Graphiti-like temporal knowledge graph memory;
- Letta/MemGPT-like stateful agent memory;
- MIRIX/M3-Agent-like multimodal memory;
- LongMemEval, LoCoMo, HaluMem, MemoryAgentBench-like evaluation protocols.
