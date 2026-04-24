---
name: obsidian-structure
description: >
  Vault folder taxonomy and routing rules for Obsidian notes. Determines which
  folder a note belongs in based on topic. Use before creating or searching notes
  to pick the correct location. Loaded automatically by the obsidian skill.
metadata:
  author: krokobot
  version: "1.0"
---

# Obsidian Vault Structure — Routing Rules

Vault path: `/home/krokobot/obsidian-vaul`

## Folder Taxonomy

| Folder | What goes here | Examples |
|---|---|---|
| `_Dashboard` | Главная страница, TODO-лист, ключевые данные | Home, ТУДУ, Claude Code Keys |
| `RingCentral` | Всё про работу в RingCentral: 1-1 заметки, проекты, инструменты, коллеги | Michael 1:1, Dima S 1:1, RingSearch, Workspace One |
| `BG` | Жизнь в Болгарии: контакты, сервисы, документы, быт | Ветеринар, Ремонт техники, Vivacom, бухгалтер |
| `BG/Авто` | Автомобиль: СТО, штрафы, таможня, электрик | AUTOEXPERT, штрафы, Варна Таможна |
| `BG/Здоровье` | Здоровье: врачи, лекарства, анализы, операции | Лекарства мои, Анализы на контроль, дерматолог |
| `Dev Notes` | Технические заметки: команды, конфиги, шпаргалки (не привязаны к конкретному проекту) | Docker cli, Kubernetes tips, Nginx, AWS, PostgreSQL |
| `General` | Личное общее: аккаунты, пароли, контакты, разное | Payoneer, WISE, Raspberry PI, размеры одежды |
| `Investments` | Инвестиции: портфель, тикеры, планы, облигации | Tickers, План покупки авто, Облигации |
| `Krokobot` | Заметки про бота Krokobot / Claude Code | Модели, настройки |
| `Orgfin.run` | Бизнес-проект Orgfin: платежи, техдетали | Credit Cards (Stripe) |
| `Poems` | Стихи и творчество | |
| `Resume` | Резюме: опыт, навыки, сертификаты, LinkedIn | experience, skills, certifications |
| `Slava` | Всё про Славу (сын): лекарства, документы | Лекарства Слава |
| `US Green Card` | Иммиграция в США: анкета, документы | DV-2026 анкета |
| `Еда` | Рецепты, хранение продуктов, кулинария | Хранение продуктов |
| `Analysis` | Аналитические отчёты (с подпапками по дате) | 2026-04-01/report_psychological.pdf |

## Routing Rules

При создании или поиске заметки определяй папку по теме:

1. **Работа, коллеги, 1-1, проекты RC** → `RingCentral`
2. **Здоровье, врачи, лекарства, анализы** → `BG/Здоровье`
3. **Машина, СТО, штрафы, дороги** → `BG/Авто`
4. **Болгария, сервисы, контакты в БГ** → `BG`
5. **Технические шпаргалки, CLI, DevOps** → `Dev Notes`
6. **Инвестиции, портфель, ETF, накопления** → `Investments`
7. **Резюме, карьера, LinkedIn** → `Resume`
8. **Orgfin проект** → `Orgfin.run`
9. **Бот, Claude Code, Krokobot** → `Krokobot`
10. **Слава (сын)** → `Slava`
11. **Грин-карта, иммиграция США** → `US Green Card`
12. **Еда, рецепты** → `Еда`
13. **Стихи** → `Poems`
14. **TODO, главная** → `_Dashboard`
15. **Всё остальное (аккаунты, пароли, личное)** → `General`

## Naming Conventions

- Имя файла = краткое описание содержимого
- Язык имени файла — русский или английский, как удобнее по контексту
- Вложения (фото, PDF) → подпапка `_attachments` внутри соответствующей папки
- Аналитические отчёты → `Analysis/YYYY-MM-DD/`

## Search Strategy

1. Сначала ищи в целевой папке по теме (Routing Rules выше)
2. Если не нашёл — Grep по всему vault
3. Для поиска по имени — Glob `~/obsidian-vaul/**/*keyword*.md`
4. Для поиска по содержимому — Grep pattern в `~/obsidian-vaul/`
