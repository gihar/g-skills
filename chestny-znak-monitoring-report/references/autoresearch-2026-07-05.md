# Autoresearch note: `chestny-znak-monitoring-report` (2026-07-05)

## Trigger

The user asked to improve the skill for regulatory monitoring reports and then run `autoresearch` for `chestny-znak-monitoring-report`.

Key user requirements:

- Check official sources, draft NPAs, published NPAs, regulators, legal systems, EDI/OFD operators, and industry media.
- Deduplicate sources and highlight critical changes, business actions, deadlines, product groups, IT/EDI/cash register/API changes, and sources.
- Separately perform adopted-act normative control so documents like “О внесении изменений в постановление ... № ...” are not missed even when they do not mention “Честный ЗНАК”.
- For the period, explicitly check publication.pravo.gov.ru, Garant hotlaw, Consultant/legal republications, Minpromtorg, and ChZ/CRPT.
- Use the full watchlist of base resolutions equally; do not over-focus on one number.
- If a watchlist resolution is amended, include it at least as “Важно”.
- If a new related marking resolution/system act/experiment/API/EDI/OFD/cash-register act is found, add it to the watchlist for future runs.
- PDF tables must be readable: sections 2 and 3 use 4 columns, maximum 5.
- Add “Ожидающиеся события на ближайшие полгода” for the 6-month horizon from report preparation date.
- Remove the report header line `Подготовлено для: Алексей`.

## Eval suite used

1. Header privacy: report header has no `Подготовлено для: Алексей` or personal recipient line.
2. Normative anti-miss: publication.pravo.gov.ru, Garant hotlaw, Consultant/legal republications, Minpromtorg, ChZ/CRPT, and full watchlist are explicitly required.
3. Watchlist inclusion rule: amendments to any watchlist resolution are at least “Важно”; new related acts are added to the watchlist.
4. PDF table readability: main tables use 4 columns, maximum 5, avoiding 7–8 narrow columns.
5. Six-month events: mandatory block covers effective dates, experiments, registration/stock/deadline events, permit mode, EDI/UPD, KKT/OFD, API/LK GIS MT, discussion endings, official webinars/events.
6. Business action extraction: actions, deadlines, product groups, IT/EDI/cash/API impacts, sources, confidence, and deduplication are explicit.

## Result

Baseline after initial manual edits: 5/6 (83.3%).

Kept mutations:

1. Removed `**Подготовлено для:** Алексей` from the recommended PDF header and added an explicit prohibition against personal recipient lines.
2. Converted section 11 “Ожидающиеся события...” from a 7-column table to a preferred 4-column format with an optional 5-column fallback.
3. Added a final preflight checklist before PDF generation/sending covering header privacy, normative control, watchlist handling, readable tables, business actions, deduplication, and the 6-month events block.

Final: 6/6 (100%).

## Operational note

For future edits, preserve the skill as a class-level monitoring/reporting skill. Put narrow run details and research notes in `references/`; keep SKILL.md focused on durable workflow, report structure, source strategy, and quality gates.
