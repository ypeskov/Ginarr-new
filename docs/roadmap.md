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

- [x] В `log_event.py` для `user`-ивентов: парсить `<channel>` теги, доставать `image_path` / `attachment_file_id`, копировать файл в `$VAULT_ROOT/logs/YYYY/MM/attachments/YYYY-MM-DD_<sha8>.<ext>` (content-addressed → dedup).
- [x] Подменять `<channel>` в `content` на `[image: attachments/…]` / `[file: …]` / `[audio: …]`. Для `attachment_file_id` без локального файла — Ginarr-расширение `[kind: unresolved:<file_id>]` (агент потом скачивает через `download_attachment`); настоящий backfill пути — отдельный этап.
- [x] Доки: обновить `docs/hooks.md` и `docs/scripts/log_event.md`. Self-test в `log_event.py --self-test` (11 кейсов).

## Этап 2 — runtime-контроль записи

### 2.1 `/nolog` — Layer 4

- [x] Slash-команда `.claude/commands/nolog.md`, принимает `on | off`. Поведение: `on` → `touch .claude/channels/.nolog`, `off` → `rm -f`, без аргумента — репорт состояния.
- [x] Флаг в `.claude/channels/.nolog` + сайдкар `.nolog.state` (последнее увиденное `log_event.py` состояние — чтобы поймать переход). Оба чистятся при `bot_started`.
- [x] `log_event.py._apply_nolog`: при off→on эмитит `system:log_paused` и скипает; при on→off эмитит `system:log_resumed` и пишет текущий ивент; стабильные состояния — просто skip/write по флагу. Session-events проходят сквозь паузу.
- [x] Доки: `docs/skills/nolog.md`, апдейт `docs/scripts/log_event.md`, `docs/skills/index.md`. Self-test: 7 новых кейсов, всего 18/18.

### 2.2 `/redact` — подключение Layer 3

- [x] Slash-команда `.claude/commands/redact.md`: `/redact <value>` — Claude читает текущий `.redact-list` через Read, добавляет значение, пишет обратно через Write (без шелла → никаких проблем со спецсимволами). Без аргумента — репорт количества без раскрытия значений. Дубликаты отсеиваются, multi-line значения отклоняются.
- [x] `log_event.py`: `_load_redact_list()` читает `.claude/channels/.redact-list` на каждый user/assistant ивент и прокидывает в `redactor.redact(text, denylist)`. Missing file → пустой список (soft-fail, write-path не должен блокировать).
- [x] Файл чистится на `SessionStart` через `_reset_channels_on_start()` (рядом с `.nolog` / `.nolog.state`) — сразу после записи `bot_started`. Layer 3 по SPEC — process-lifetime only.
- [x] Доки: `docs/skills/redact.md`, апдейт `docs/skills/index.md`, `docs/scripts/log_event.md`, `docs/scripts/redactor.md`. Self-test: 5 новых кейсов, всего 23/23.

**Следующим шагом (не в 2.2):** inline-тег `<secret>value</secret>` как альтернатива «одноразовой утечки в самом `/redact <value>`-промпте». SPEC.v3 разрешает этот синтаксис; `redactor.py` его пока не реализует.

## Этап 3 — память (skill'ы capture / recall / review)

### 3.1 `capture` skill

- [x] `.claude/skills/capture/SKILL.md` — триаж по SPEC-таблице (high/medium/low + always-ask overrides + never-save). Триггер-описание: факт о себе / предпочтение / фидбек / решение / явное «запомни». Операционные вопросы и код-таски явно отсечены.
- [x] Dedup: grep по `$GINARR_VAULT_ROOT/notes/`, Read матчей, Write нового/обновлённого файла. Frontmatter по SPEC (type/name/description/created/updated + опциональные tags/source/status/supersedes).
- [x] Low-confidence → апенд в `_pending.md` по шаблону, который уже зашит в файле.
- [x] Telegram-фидбек: 💾-реакция для high (silent, без текста), 💾+короткий ответ с путём для medium, тишина для low, прямой вопрос для always-ask. Fallback 💾 → 🧠 → 👌.
- [x] **Поправка к SPEC.v3:** заведена директория `notes/reference/` — в SPEC `reference` был во frontmatter, но дира не значилась. Формализовать в SPEC v4.
- [x] Явно разделено: Ginarr-vault (owner-facing, в Obsidian) vs. Claude private auto-memory (приватный ноутбук между сессиями).
- [x] Доки: `docs/skills/capture.md`, апдейт `docs/skills/index.md`.

### 3.2 `recall` skill

- [x] `.claude/skills/recall/SKILL.md`: read-only скилл. На ретроспективные вопросы — grep по `notes/` (авторитет, логи не трогаем, если заметка отвечает), иначе `logs/YYYY/MM/*.jsonl` с явным UTC-окном, плюс опционально `_pending.md` c пометкой «не подтверждено». Цитата источника в каждом ответе; если ничего нет — говорит одной строкой, не выдумывает.
- [x] Local→UTC — **LLM-native**: скилл инструктирует Claude конвертировать фразы типа «вчера около 2» в UTC-окно по TZ владельца (Europe/Sofia, DST-aware), с кросс-чеком `TZ=Europe/Sofia date -u …` на границах. Helper-скрипт не пишется — SPEC прямо говорит, что локальное время это query-time concern. TZ владельца сохранена в private auto-memory (`user_default_timezone.md`).
- [x] Доки: `docs/skills/recall.md`, апдейт `docs/skills/index.md` (recall переехал из Not yet built в Installed).

### 3.3 `/review` skill

- [x] Slash-команда `.claude/commands/review.md` + скилл `.claude/skills/review-pending/SKILL.md` (имя `review-pending` вместо `review` чтобы не конфликтовать со встроенным CC-скилом для PR-ревью; `/review` как slash-команда всё равно работает). Действия: `save | drop | skip | edit` — в RU/EN; skip = ротация в хвост очереди (без потери). Save запускает dedup по `notes/`, при совпадении — merge или conflict protocol из `capture`. Template-заголовок `_pending.md` никогда не перезаписывается.
- [x] Telegram MVP: реакция 💾 на save (fallback 🧠→👌), 👌 на drop/skip, текстовая подсказка по действиям в презентации кандидата. Inline keyboard — отложено.
- [ ] Threshold-нотификация (≥5 кандидатов) — следующим подэтапом.
- [x] Доки: `docs/skills/review.md`, апдейт `docs/skills/index.md` (review переехал из Not yet built в Installed).

## Этап 4 — обслуживание (`tools/`)

Живут в `tools/` в корне репы (под git), pure Python stdlib, без LLM-SDK зависимостей. SPEC.v3 изначально говорил `$VAULT_ROOT/_tools/` — решено перенести в репу для version control без потери портативности (скрипты рантайм-нейтральны, ничего из `.claude/` их не импортирует). Оператор может симлинкнуть в вольт, если хочет их там видеть. Будет формализовано в SPEC v4 вместе с аналогичным переездом skills/agents.

### 4.1 `consolidate.py`

- [x] Dry-run репорт дублей по Jaccard-сходству токенов имён файлов (`--threshold`, default 0.6) и/или тегов. Группирует по общему `type`; скипает `_*.md` и `archive/`. Пропускает мусор в frontmatter без падения.
- [x] `--apply` пока — заглушка с понятным stderr и exit 2; мёрдж отдан на явный owner-флоу (`/review` или руками в Obsidian), чтобы не терять инфу автоматически. Планирование через системный cron.

### 4.2 `search.py`

- [x] CLI: `search.py <query> [--scope notes|logs|both] [--since <date>] [--type …] [--tag …] [--json]`. Notes фильтруются по frontmatter (`type`/`tag`), logs — по дате в имени файла (`YYYY-MM-DD.jsonl`). Подстроковый поиск (case-insensitive), escape перед regex. JSON-выход для пайплайнов.

### 4.3 `archive.py`

- [x] CLI: `archive.py --older-than <Nd|Nw|Nmo|Ny> [--type project] [--apply]`. Кандидат = `status: retired|archived` **и** `updated` ≤ cutoff. Целевой путь — `notes/archive/<оригинальный-rel-path>`, субдиректории сохраняются. По умолчанию dry-run; `--apply` делает реальный `shutil.move`.

## Отложено

- Multi-vault — см. [`TODO.md`](../TODO.md).
- Threshold-нотификация для `/review` (после базового review).
- Проверка миграции на Junie / OpenCode+oh-my-opencode.

## Инварианты на каждом этапе

- В одном коммите: код + соответствующий `docs/<тема>.md` + апдейт `docs/*/index.md`.
- Всё, что коммитится в репо — по-английски (CLAUDE.md). Исключение — этот `roadmap.md` (личный трекер).
- Имена skills — kebab-case (agentskills.io spec). Имена заметок в vault'е — `snake_case.md` (SPEC.v3). Роли в логе — `user | assistant | system`. UTC везде. Append-only.
