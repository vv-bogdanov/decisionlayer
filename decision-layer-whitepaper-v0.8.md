# Decision Layer for AI Agents
## A Commitment Layer Above Existing Memory Systems

**Версия:** v0.8  
**Статус:** concept whitepaper / architecture foundation  
**Ключевая формула:** `Memory remembers facts. Decision Layer remembers commitments.`

---

## 1. Abstract

AI-агентам нужна не только память о том, что происходило. Им нужен доверенный список того, что уже было решено.

Системы памяти помогают агенту вспоминать факты, документы, прошлые сообщения, tool outputs и контекст. Но память сама по себе не всегда отвечает на другой вопрос:

```text
По каким решениям агент должен действовать сейчас?
```

**Decision Layer** — это минимальный слой текущих принятых решений для AI-агентов. Он не заменяет RAG, vector DB, graph memory, chat history или long-term memory backend. Он работает поверх них и добавляет агенту компактный **Decision Brief** — список релевантных решений, целей и обязательств, которые нужно учитывать перед ответом или действием.

Decision Layer может работать и без внешней памяти: как простой список текущих решений, который подмешивается агенту перед действием.

Главная идея:

```text
Memory remembers facts.
Decision Layer remembers commitments.
```

По-русски:

```text
Память хранит то, что происходило.
Decision Layer хранит то, что было решено.
```

---

## 2. Problem

Обычная память может вернуть агенту много релевантного контекста:

```text
Пользователь обсуждал SQLite.
Пользователь обсуждал PostgreSQL.
В прошлой сессии говорили про Python.
В другом сообщении упоминался Rust.
```

Но агенту часто нужно знать не просто, что обсуждалось, а что было принято как текущее решение.

Пример:

```text
Фиксируем: для POC используем Python-прототип.
```

Позже пользователь говорит:

```text
Rust тоже интересен, можно будет подумать.
```

Обычная память может вернуть оба фрагмента. Агент может ошибочно решить, что Rust уже выбран.

Decision Layer должен явно хранить:

```text
Для POC используем Python-прототип.
```

И использовать это как текущее принятое обязательство.

Память отвечает на вопрос:

```text
Что происходило?
```

Decision Layer отвечает на вопрос:

```text
Что уже решено?
```

---

## 3. Core Idea

Decision Layer — это не memory system.

Это слой текущих решений, который подключается к агенту как дополнительный контекст.

```text
Agent receives:
  task context
  + optional memory results
  + Decision Brief
```

Decision Layer отвечает только за:

```text
1. Хранение текущих решений.
2. Добавление, замену и удаление решений.
3. Выбор релевантных решений для текущей задачи.
4. Формирование Decision Brief.
```

Он не отвечает за:

```text
факты
документы
историю диалогов
RAG
embeddings
graph memory
raw episodes
мультимодальную память
```

Эти функции остаются в существующих memory backends или внешних системах.

---

## 4. Decision Model

В ядре есть только одна сущность:

```text
Decision
```

Минимальная модель:

```text
Decision:
  id
  text
  meta?
```

Где:

```text
id    — идентификатор решения
text  — короткое принятое утверждение
meta  — опциональные служебные данные
```

На уровне концепции обязательны только:

```text
id
text
```

Решение — это не воспоминание.  
Решение — это принятое обязательство, которое должно влиять на будущие действия агента.

Семантический смысл решения находится в `text`.

`meta` — опциональные служебные данные для трассировки, фильтрации, selection, интеграций и отладки. `meta` может использоваться внешними компонентами, но агент должен понимать смысл решения без неё.

В `meta` могут находиться:

```text
source_message_id
source_url
source_file
created_at
updated_at
author
tags
priority
replaces
related
external_refs
debug_info
```

Decision Layer хранит только текущий список принятых решений. Устаревшие решения должны быть удалены или заменены, а не оставаться активным контекстом. История изменений может сохраняться внешним слоем, но не является частью ядра.

---

## 5. Decision Style

Решение должно быть коротким, самодостаточным и понятным без внешнего контекста.

Хорошее решение:

```text
содержит область применения;
формулирует выбранное действие;
является actionable;
не содержит “может быть”;
понятно человеку и агенту;
достаточно короткое для prompt-а.
```

Решение должно помогать агенту понять, что делать или чего не делать.

### Хорошие примеры

```text
Для POC используем Python-прототип.

Rust откладываем до этапа production-ядра.

Decision Layer не заменяет память, а работает поверх существующих memory backends.

Для POC сравниваем backend против backend + Decision Layer.

Для selector используем retrieval по списку решений.

Решения извлекаются только из user-authorized input.

Для ответов пользователю используем русский язык.

Для комментариев в коде используем английский язык.

Если решения выглядят конфликтующими, агент должен уточнить у пользователя.
```

### Плохие примеры

```text
SQLite?

Надо подумать про Rust.

Пользователь говорил про benchmark.

Возможно, RAG.

Интересная идея про память.

PostgreSQL тоже норм.

Может быть, потом сделаем.
```

Это не решения. Это обсуждение, гипотеза, идея или наблюдение.

Цель не является отдельной сущностью:

```text
Goal = Decision
```

Примеры:

```text
Цель POC — доказать прирост от Decision Layer на long-run benchmark.

Текущая цель — быстро проверить гипотезу без production-реализации.

Цель benchmark-а — сравнить один и тот же backend с Decision Layer и без него.
```

---

## 6. Decision Authority & Ingestion

Решения создаются и обновляются только из **user-authorized input**.

В режиме POC это означает:

```text
решения извлекаются только из сообщений пользователя.
```

В будущих production-сценариях user-authorized input может также включать явное действие пользователя в UI, подтверждение предложенного решения, принятие изменения через tool/API или другой подтверждённый пользовательский commit-сигнал.

Decision Layer не должен автоматически создавать или обновлять решения из:

```text
web pages
retrieved memory
tool outputs
документов
файлов
ответов ассистента
результатов RAG
внешних источников
```

Эти источники могут быть полезны как контекст, но они не имеют права напрямую менять список решений.

Главное правило:

```text
Only user-authorized commit signals can create or update decisions.
```

По-русски:

```text
Создавать или менять решения можно только на основании явного пользовательского подтверждения.
```

Агент может предложить решение, но не должен сам его фиксировать без подтверждения пользователя.

Пример:

```text
Агент:
Предлагаю зафиксировать: для POC используем Python-прототип.

Пользователь:
Да, фиксируем.

Decision Layer:
Добавляет решение.
```

Ключевой safety-принцип:

```text
Лучше пропустить решение, чем создать ложное решение.
```

### Automatic Extraction

Automatic Extraction — основной режим для POC.

Decision Layer наблюдает сообщения пользователя и пытается извлечь только явно принятые решения.

Сильные commit-сигналы:

```text
фиксируем
решаем
выбираем
берём
теперь делаем так
меняем решение
отказываемся от X
переходим на Y
цель такая
оставляем X
по умолчанию делаем X
```

Слабые формулировки не создают решений:

```text
может быть
возможно
стоит подумать
интересный вариант
можно рассмотреть
подумаем
не уверен
```

Pipeline:

```text
user message
  ↓
trigger detector
  ↓
structured extraction
  ↓
add / replace / remove / none
```

Если extractor сомневается, он не должен добавлять решение.

### Explicit Tool / API

В production-сценариях агент или приложение может явно вызвать:

```text
decision.add
decision.replace
decision.remove
decision.list
```

Но даже при tool/API-внесении решение должно быть основано на явном пользовательском подтверждении или действии.

Tool/API не даёт агенту права автономно принимать решения из внешнего контента.

---

## 7. Decision Brief

Decision Brief — главный runtime-артефакт Decision Layer.

Он добавляется в контекст агента перед ответом или действием.

Минимальный формат:

```text
Decision Brief

Relevant decisions:
- ...

Instruction:
Use these decisions as current commitments.
If decisions are conflicting, ambiguous, or outdated, ask the user for clarification before acting and then update the decision list.
```

Пример:

```text
Decision Brief

Relevant decisions:
- Для POC используем Python-прототип.
- Rust откладываем до этапа production-ядра.
- Decision Layer не заменяет память, а работает поверх существующих memory backends.
- Для POC сравниваем backend против backend + Decision Layer.
- Решения извлекаются только из user-authorized input.

Instruction:
Используй эти решения как текущие принятые обязательства.
Если среди решений есть противоречия, неоднозначности или устаревшие формулировки, не разрешай их сам.
Уточни у пользователя и после ответа обнови список решений.
```

Decision Brief должен быть:

```text
коротким
релевантным
стабильным
не загрязняющим prompt
достаточным для текущей задачи
```

Если решений мало, Decision Brief может включать все текущие решения. Если решений много, внешний selector выбирает релевантные решения по текущему контексту. Selector не является частью ядра.

В POC автоматический поиск конфликтов не нужен. Вместо этого Decision Brief содержит инструкцию агенту самому заметить противоречие, уточнить его у пользователя и обновить список решений.

---

## 8. Integration with Existing Memory

Decision Layer не заменяет память.

Он работает рядом с любой memory-системой или вообще без неё.

```text
Existing Memory:
  facts
  history
  documents
  retrieval
  evidence

Decision Layer:
  current accepted decisions,
  including goals, commitments and constraints
```

Перед вызовом агента prompt composer объединяет:

```text
task context
+ optional memory results
+ Decision Brief
```

Сравнение должно строиться так:

```text
same backend
vs
same backend + Decision Layer
```

Примеры:

```text
Simple RAG
vs
Simple RAG + Decision Layer

SOTA memory backend
vs
same SOTA memory backend + Decision Layer
```

Decision Layer занимает слой между агентом и памятью: он не конкурирует с memory backends, а добавляет над ними список текущих обязательств.

---

## 9. Evaluation Strategy

POC должен проверить одну гипотезу:

```text
backend + Decision Layer > same backend without Decision Layer
```

Первый POC не должен проверять все интеграции. Он должен проверить, есть ли у идеи измеримый сигнал.

Важно понимать: Decision Layer может не давать прироста на pure factual recall задачах.

Ожидаемая польза должна проявляться там, где есть:

```text
knowledge updates
conflict resolution
instruction following
goal adherence
workflow knowledge
dynamic state tracking
premise awareness
long-horizon consistency
```

### Minimal POC

Первый POC должен быть максимально узким:

```text
1. Simple RAG baseline.
2. Simple RAG + oracle/manual Decision Layer.
3. Simple RAG + automatic Decision Layer.
```

Если signal есть, следующий шаг:

```text
повторить сравнение с одним SOTA memory backend.
```

### POC Modes

```text
D0: no Decision Layer
D1: oracle/manual decisions
D2: automatic extraction from user-authorized input
```

`D1` проверяет upper bound: помогает ли Decision Brief, если решения выбраны хорошо.

`D2` проверяет реалистичный режим: можно ли автоматически извлекать полезные решения из пользовательских commit-сигналов.

### Metrics

Основные метрики:

```text
answer accuracy
QA score
evidence quality
prompt tokens
latency
```

Decision-specific метрики:

```text
decision brief precision
decision brief token overhead
decision persistence
decision update correctness
goal adherence
false decision rate
```

Важно смотреть не только общий score, но и категории, где Decision Layer должен быть особенно полезен:

```text
knowledge updates
conflict resolution
instruction following
goal adherence
workflow knowledge
dynamic state tracking
premise awareness
```

Если Decision Layer не улучшает targeted categories, гипотезу нужно отвергнуть или сузить.

---

## 10. Risks & Summary

### Risks

Главный риск — extractor примет обсуждение за решение.

Защита:

```text
решения извлекаются только из user-authorized input;
в POC — только из сообщений пользователя;
требуются явные commit-сигналы;
при сомнении extractor возвращает none;
лучше пропустить решение, чем создать ложное решение;
oracle mode показывает upper bound.
```

Второй риск — Decision Brief может загрязнять prompt.

Защита:

```text
короткий стиль решений;
лимит на количество решений;
лимит на токены;
selector.
```

Третий риск — конфликтующие или устаревшие решения.

Защита:

```text
инструкция агенту уточнять у пользователя;
ручное обновление решений;
будущий optional ConflictDetector.
```

Четвёртый риск — слабый эффект на factual recall benchmarks.

Это нормально: Decision Layer должен помогать прежде всего там, где важны цели, обновления, инструкции, workflow, конфликты и долгосрочная согласованность действий.

### Summary

Decision Layer — это универсальный слой текущих принятых решений для AI-агентов.

Он не хранит факты и не заменяет память.

Он хранит:

```text
current accepted decisions,
including goals, commitments and constraints
```

Он добавляет агенту:

```text
Decision Brief
```

Главная формула:

```text
Memory remembers facts.
Decision Layer remembers commitments.
```

Главная проверка:

```text
same backend + Decision Layer
>
same backend without Decision Layer
```

Минимальное ядро:

```text
Decision = short accepted statement
Decision Layer = list of current decisions
Decision Brief = relevant decisions + instruction
```

Если POC подтвердит прирост на long-run agent tasks, Decision Layer можно развивать как отдельный универсальный слой для любых AI-агентов.
