# Дорожная карта реализации

Последовательный план по доведению Ginarr до SPEC.v3. Этапы упорядочены по зависимостям: ранние разблокируют поздние.

Этот файл — долгоживущий план, переживает компакты сессии. Когда пункт сделан — отмечай `[x]` **в том же коммите**, в котором лэндится работа. Пустой чекбокс `[ ]` = ещё не начат / в работе.

См. также:
- [`TODO.md`](../TODO.md) — фичи, отложенные без расписания.
- [`architecture.md`](architecture.md) §"What is NOT here yet" — кратко текущие пробелы.

## Baseline (уже сделано)

- [x] Write-path через хуки: `log_event.py` на `UserPromptSubmit` / `Stop` / `SessionStart` / `SessionEnd`, пишет `logs/YYYY/MM/YYYY-MM-DD.jsonl`.
- [x] `redactor.py` — Layer 2 (regex) подключён к хуку через `log_event.py`. Layer 3 (denylist-файл) — реализован как инструмент, но **не подключён** к runtime-пути (см. 2.2).
- [x] `create-skill` — скаффолд скилов, скопирован из OpenClaw.
- [x] `docs/` + `.env.example` + `TODO.md`.

## Этап 1 — безопасность и верность лога

### 1.1 Layer 1 — PreToolUse denylist

- [x] Новый хук `pre_tool_denylist.py`, регистрация в `settings.json` на `PreToolUse` (matcher: `Read|Edit|Write|Bash|NotebookEdit`).
- [x] Denylist из SPEC §"Secrets and PII": `.env*` (кроме `.env.example`), `*.pem`, `*.key`, `id_rsa*`, `credentials*`, `~/.ssh/**`, `~/.aws/**`, `~/.config/gcloud/**`, `~/.kube/config`.
- [x] При матче: deny с `[REDACTED: path in denylist]` в `permissionDecisionReason`. Bash-команды сканируются token-by-token (best-effort).
- [x] Доки: обновить `docs/hooks.md`, создать `docs/scripts/pre_tool_denylist.md`.

### 1.2 Attachment markers

- [ ] В `log_event.py` для `user`-ивентов: парсить `<channel>` теги, доставать `image_path` / `attachment_file_id`, копировать файл в `$VAULT_ROOT/logs/YYYY/MM/attachments/YYYY-MM-DD_<sha8>.<ext>`.
- [ ] Подменять `<channel>` в `content` на `[image: attachments/…]` / `[file: …]` / `[audio: …]`.
- [ ] Доки: обновить `docs/hooks.md` и `docs/scripts/log_event.md`.

## Этап 2 — runtime-контроль записи

### 2.1 `/nolog` — Layer 4

- [ ] Slash-команда `.claude/commands/nolog.md`, принимает `on | off`.
- [ ] Флаг в `.claude/channels/.nolog` (чистится при `bot_started`).
- [ ] `log_event.py`: проверяет флаг на входе; при активной паузе — пропускает `user`/`assistant`; на переходах эмитит `system:log_paused` / `log_resumed`.
- [ ] Доки: `docs/skills/nolog.md`.

### 2.2 `/redact` — подключение Layer 3

- [ ] Slash-команда `.claude/commands/redact.md`: `/redact <value>` апендит `value` в `.claude/channels/.redact-list`.
- [ ] `log_event.py`: передаёт путь этого файла в `redactor.py` при вызове `redact()`.
- [ ] Файл чистится при `bot_started` (внутри `log_event.py --event session-start`).
- [ ] Доки: `docs/skills/redact.md`.

## Этап 3 — память (skill'ы capture / recall / review)

### 3.1 `capture` skill

- [ ] `.claude/skills/capture/SKILL.md` по SPEC §"Capture rules": high/medium/low confidence, always-ask-immediately, never-save.
- [ ] Агент делает dedup через grep по `$VAULT_ROOT/notes/`, пишет/обновляет `notes/<type>/<snake_case>.md` с YAML frontmatter.
- [ ] Low-confidence → апенд в `notes/_pending.md`.
- [ ] Доки: `docs/skills/capture.md`.

### 3.2 `recall` skill

- [ ] `.claude/skills/recall/SKILL.md`: перед ответом на ретроспективные вопросы — grep по `notes/`, затем по `logs/YYYY/` с явным date scope.
- [ ] Хелпер конвертации local→UTC для вопросов типа "вчера около 2 часов".
- [ ] Доки: `docs/skills/recall.md`.

### 3.3 `/review` skill

- [ ] Slash-команда + skill: проходит `notes/_pending.md` по одному кандидату — confirm / drop / edit.
- [ ] Telegram MVP: простой текстовый prompt "да / нет / редактировать". Inline keyboard — потом.
- [ ] Threshold-нотификация (≥5 кандидатов) — следующим подэтапом.
- [ ] Доки: `docs/skills/review.md`.

## Этап 4 — обслуживание (`_tools/`)

Живут в `$VAULT_ROOT/_tools/` (портируемо, не в `.claude/`), без LLM-SDK зависимостей.

### 4.1 `consolidate.py`

- [ ] `--dry-run` / `--apply`, ищет дубли по topic / tags, предлагает merge.
- [ ] Первый прогон только dry-run. Планирование через системный cron.

### 4.2 `search.py`

- [ ] Обёртка над grep с пониманием frontmatter: `--scope notes|logs --since <date>`.

### 4.3 `archive.py`

- [ ] `--older-than <duration>` — переносит retired проекты в `notes/archive/`.

## Отложено

- Multi-vault — см. [`TODO.md`](../TODO.md).
- Threshold-нотификация для `/review` (после базового review).
- Проверка миграции на Junie / OpenCode+oh-my-opencode.

## Инварианты на каждом этапе

- В одном коммите: код + соответствующий `docs/<тема>.md` + апдейт `docs/*/index.md`.
- Всё, что коммитится в репо — по-английски (CLAUDE.md). Исключение — этот `roadmap.md` (личный трекер).
- Имена skills/commands — `snake_case`. Роли в логе — `user | assistant | system`. UTC везде. Append-only.
