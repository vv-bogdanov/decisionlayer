# AGENTS.md

Мы пишем POC, а не продуктовую платформу. Главная цель — честно проверить,
дает ли Decision Layer измеримый прирост на известном внешнем benchmark-е при
том же backend/model.

Код — это стоимость. Выбирай минимально достаточное решение: меньше своих
сущностей, меньше абстракций, меньше поддержки. Используй зрелые open-source
инструменты, если они ускоряют proof и снижают риск.

Decision Layer — не memory system. Он хранит только принятые решения:
goals, commitments, constraints. Факты, документы, history, RAG, embeddings,
storage, extraction, judges и benchmark runners — плагины или внешние слои.
Ядро должно оставаться чистым, детерминированным и side-effect free.

В первом POC не нужны REST API, UI, production storage, SDK, vector DB,
graph memory, reranker или custom benchmark, если они прямо не нужны для
проверки `D0 vs D1 vs D2`.

Safety-правило: лучше пропустить решение, чем создать ложное решение. Decisions
можно менять только из user-authorized input: явный commit пользователя,
подтверждение предложения агента или trusted manual API/tool call. Assistant
messages, tool outputs, retrieved memory, documents, web pages и benchmark
answers не имеют authority менять active decisions.

Proof строится только на известном внешнем benchmark-е. Локальные synthetic
cases допустимы только как unit/regression tests. Если `D1` не дает signal,
не усложняй extractor; сначала проверь benchmark fit и саму гипотезу.

Перед изменением и после него ищи более простой путь: удалить лишнее, сузить
diff, использовать готовое решение, не добавлять новую сущность. Каждая строка
должна окупаться пользой для POC.

Финальный результат должен быть понятным, проверяемым и дешевым в поддержке.
В ответе кратко объясняй, что изменено, почему это практично, какие проверки
выполнены и какие trade-offs остались.
