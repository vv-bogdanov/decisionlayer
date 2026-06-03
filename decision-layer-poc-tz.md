# Верхнеуровневое ТЗ для coding-агента
## POC: Decision Layer on LongMemEval-V2

## 1. Цель

Собрать минимальный Proof of Concept для проверки гипотезы:

```text
LongMemEval-V2 baseline + Automatic Decision Layer
работает лучше,
чем тот же baseline без Decision Layer.
```

Decision Layer — это не система памяти.  
Это слой текущих принятых решений, который добавляется к контексту агента как `Decision Brief`.

Главная задача POC — быстро понять, есть ли измеримый signal от этой идеи.

---

## 2. Основные решения

В рамках POC зафиксированы следующие решения:

```text
Используем один benchmark: LongMemEval-V2.

Сравниваем только два режима:
1. baseline
2. baseline + Automatic Decision Layer

Decision Layer хранит только список текущих решений.

Решение — это короткое принятое утверждение.

Решения извлекаются только из пользовательских / user-authorized сообщений.

Лучше пропустить решение, чем создать ложное решение.

Decision Brief добавляется в prompt перед ответом.

Нужна обязательная traceability: должно быть видно, какие решения извлечены и как они попали в Decision Brief.
```

---

## 3. Технологический подход

Использовать максимально быстрый и простой research-стек:

```text
Python
uv
pytest
готовые benchmark/data utilities, если доступны
минимум собственного кода
```

Не делать в этом этапе:

```text
Rust
REST API
SDK
UI
production storage
custom benchmark
SOTA backend integrations
graph/re-ranker/hyperparameter search
automatic conflict detector
```

Цель — не построить продукт, а проверить гипотезу.

---

## 4. Benchmark

Использовать только:

```text
LongMemEval-V2
```

Задачи:

```text
Найти официальный репозиторий / dataset / runner.

Разобраться с форматом benchmark-а.

Запустить baseline на небольшом subset-е.

Добавить режим baseline + Automatic Decision Layer.

Сравнить оба режима на одном и том же subset-е.
```

Если полный benchmark тяжёлый, использовать разумный subset.  
Не переключаться на другие benchmark-и в рамках этого задания.

---

## 5. Decision Layer

Минимальное ядро:

```text
Decision = id + text + optional meta
```

Где `text` — короткое принятое решение.

Примеры решений:

```text
Для POC используем Python-прототип.

Decision Layer не заменяет память, а работает поверх существующего baseline.

Для POC сравниваем baseline против baseline + Decision Layer.

Если решения выглядят конфликтующими, агент должен уточнить у пользователя.
```

Ядро должно поддерживать базовые операции:

```text
добавить решение
заменить решение
удалить решение
получить список решений
```

Хранение для POC может быть простым in-memory с возможностью сохранить состояние/trace в файлы.

---

## 6. Automatic Decision Extraction

Решения извлекаются только из пользовательских / user-authorized сообщений внутри trajectory.

Не извлекать решения из:

```text
ответов ассистента
tool outputs
retrieved memory
документов
внешних источников
benchmark answers
```

Extractor должен быть консервативным.

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

Слабые формулировки не создают решения:

```text
может быть
возможно
стоит подумать
можно рассмотреть
подумаем
интересный вариант
```

Рекомендуемый подход:

```text
сначала простой rule trigger;
LLM structured extraction — только для сообщений-кандидатов.
```

При сомнении extractor не должен добавлять решение.

---

## 7. Decision Brief

Во втором режиме запуска перед ответом модели добавлять `Decision Brief`.

Смысл Decision Brief:

```text
дать агенту релевантный список текущих принятых решений;
сказать агенту использовать их как текущие обязательства;
если решения конфликтуют или устарели — не разрешать это самому, а уточнять у пользователя, если это возможно.
```

Для POC не нужен сложный selector.

Достаточно:

```text
если решений мало — добавлять все;
если решений много — применить простой лимит / простой keyword filter.
```

---

## 8. Traceability и logging

Traceability обязательна.

Нужно, чтобы в консоли и в сохранённых логах было видно:

```text
какие сообщения обработаны;
какие сообщения стали decision candidates;
какие решения добавлены / заменены / удалены;
какой итоговый список решений был перед ответом;
какой Decision Brief был добавлен в prompt;
какой score получился.
```

Цель traceability — дать возможность быстро понять, почему Decision Layer помог или навредил.

---

## 9. Тесты

Покрыть только критичное:

```text
добавление решения;
замена решения;
удаление решения;
получение списка решений;
Decision Brief содержит решения и инструкцию;
extractor не создаёт решения из слабых формулировок;
extractor создаёт решения из явных commit-сигналов;
benchmark smoke-run работает в двух режимах.
```

Минимальные golden cases:

```text
“Может быть SQLite” -> no decision

“SQLite выглядит интересно” -> no decision

“Фиксируем: для MVP используем SQLite” -> add decision

“Меняем решение: для MVP используем PostgreSQL” -> replace decision

“Цель: проверить Decision Layer на benchmark-е” -> add decision
```

---

## 10. Артефакты результата

После запуска должны быть сохранены:

```text
метрики baseline;
метрики baseline + Decision Layer;
предсказания обоих режимов;
логи извлечения решений;
логи Decision Brief;
итоговый report.md.
```

`report.md` должен коротко ответить:

```text
какой subset LongMemEval-V2 использован;
какая модель использовалась;
какой score у baseline;
какой score у baseline + Decision Layer;
какая разница;
сколько решений было извлечено;
на скольких samples Decision Brief был непустой;
есть ли заметный signal;
если signal нет — что видно по trace-логам.
```

---

## 11. Definition of Done

POC считается выполненным, когда одной командой можно:

```text
создать окружение;
запустить тесты;
запустить LongMemEval-V2 subset;
получить baseline score;
получить baseline + Decision Layer score;
получить trace/logs;
получить report.md.
```

Главный вопрос отчёта:

```text
Помог ли Automatic Decision Layer поверх baseline на LongMemEval-V2 subset?
```

Если signal есть — следующим этапом расширяем benchmark size, улучшаем extractor/selector и подключаем более сильные backends.

Если signal нет — анализируем traces и решаем, проблема в extractor-е, Decision Brief, benchmark-е или самой гипотезе.
