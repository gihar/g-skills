# Crocotime Web API: контроллеры отчёта

Источник: приложенная пользователем документация **Crocotime Api**.

## Общий запрос

Все запросы выполняются методом `POST` на корневой URL Crocotime.

```http
Content-Type: application/json; charset=utf-8
```

```json
{
  "server_token": "...",
  "app_version": "...",
  "controller": "...",
  "query": {}
}
```

- `server_token` обязателен и не должен попадать в отчёт/логи.
- `controller` обязателен.
- `app_version` опционален, но может потребоваться для совместимости с версией сервера.
- Временные метки Unix передаются в секундах.

## `api_employees`

Получение списка сотрудников.

```json
{
  "server_token": "...",
  "controller": "api_employees"
}
```

Значимые поля ответа `result.items[]`:

- `employee_id`;
- `display_name`, `first_name`, `second_name`;
- `parent_group_id` — ID родительского отдела;
- `is_deleted`, `is_enabled`;
- `time_zone`.

## `api_departments`

Дерево отделов и сотрудников.

```json
{
  "server_token": "...",
  "controller": "api_departments"
}
```

Узлы могут содержать:

- `department_id`, `display_name`;
- `employee_id`;
- вложенный массив `items`.

При фильтре по департаменту нужно рекурсивно включать сотрудников дочерних узлов.

## `api_employee_activity`

Агрегированная статистика сотрудников за интервал.

```json
{
  "server_token": "...",
  "controller": "api_employee_activity",
  "query": {
    "interval": [1583934705, 1584021105],
    "employees": [1, 2]
  }
}
```

Поля `result.items[]`:

- `employee_id`;
- `permitted_time` — продуктивное время, сек;
- `forbidden_time` — непродуктивное/отвлечения, сек;
- `unknown_time` — неизвестное время/без компьютера, сек;
- `summary_time` — отработано, сек;
- `norm` — рабочая норма, сек;
- `late_count`, `late_time`;
- `early_end_count`, `early_end_time`;
- `absenteeism`;
- `work_day_count`, `schedule_day_count`.

Для сводки вызывается один раз за месяц. Для детализации — отдельно по каждому календарному дню.

## `api_employee_work_periods`

Приход и уход за один день.

```json
{
  "server_token": "...",
  "controller": "api_employee_work_periods",
  "query": {
    "day": 1593809940,
    "employees": [1, 2]
  }
}
```

Поля `result.items[]`:

- `employee_id`;
- `day` — Unix timestamp начала дня;
- `begin` — секунды от начала дня, `-1` если не определено;
- `end` — секунды от начала дня, `-1` если не определено.

## `api_employee_working_day_schedule`

Рабочий период и статусы сотрудника за день.

```json
{
  "server_token": "...",
  "controller": "api_employee_working_day_schedule",
  "query": {
    "day": 1593770904,
    "employees": [1, 2]
  }
}
```

Поля `result.items[]`:

- `employee_id`, `day`;
- `norm`;
- `begin`, `end`, `intervals`;
- `day_off_time` — отгул;
- `vacation_time` — отпуск;
- `sick_time` — больничный;
- `holiday_time` — праздник.

## `api_window_switch_train`

Последовательность компьютерной активности сотрудника.

```json
{
  "server_token": "...",
  "controller": "api_window_switch_train",
  "query": {
    "interval": [1591135200, 1593770904],
    "employee_id": 1
  }
}
```

Поля `result.activities[]`:

- `interval: [start, end]` — Unix timestamps;
- `computer_id`;
- `program_id`;
- `window_id`;
- `url` — если есть.

Для отчёта интервалы агрегируются по 30-минутным ячейкам: ≥50% покрытия — зелёный, 0–50% — светло-зелёный, промежуток внутри прихода/ухода без активности — серый.

## Дополнительные контроллеры из документации

- `api_employee_program_activity` — активность по программам за период.
- `api_employee_schedules` — регламенты сотрудников за период.
- `api_tracking` — проектные/задачные треки.
- `api_table_controller` — чтение отдельных полей таблиц по ID.
- `BatchProcessing` — объединение нескольких запросов в один сеанс.

Текущий генератор намеренно использует только контроллеры, формат ответа которых нужен для отчёта и однозначно описан в документации.

## Контроль целостности

Для большинства дней должно выполняться:

```text
summary_time ≈ permitted_time + forbidden_time + unknown_time
```

Небольшие расхождения возможны из-за округления/особенностей версии Crocotime. Нельзя автоматически «исправлять» поля, если `unknown_time` явно присутствует; fallback вычислять только при отсутствии поля.
