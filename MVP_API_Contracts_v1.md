# КУРАТОР — API-контракты MVP

**Документ:** MVP_API_Contracts_v1.md
**Версия:** 1.0
**Дата:** 2026-07-06
**Статус:** Draft на приёмку (PM)
**Уровень:** Solution Architecture — источник истины для разработки Backend и генерации OpenAPI 3.1
**Задача:** T-004
**Зависит от:** MVP_Data_Model_v1.md (v1.1), Rule_Engine_MVP_v1.md (v1.0), MVP_User_Flows_v1.md (v1.0)

---

## 0. Назначение

Единый контракт взаимодействия Frontend ↔ Backend ↔ Rule Engine. Документ структурирован так,
чтобы по нему можно было практически автоматически собрать спецификацию OpenAPI 3.1 и начать
разработку. Согласованные с PM решения: авторизация в MVP — только SMS (с абстракцией
провайдера); подача заявки — самостоятельно (основной) и через координатора; роли
`руководитель`+`администратор` в MVP объединены в `admin`; уведомления — внутри системы + SMS
для критичного.

---

## 1. Общие принципы API

- **Стиль:** REST, ресурсо-ориентированный. Существительные во множественном числе
  (`/projects`, `/applications`).
- **Версионирование:** префикс пути `/api/v1`. Ломающие изменения → `/api/v2`.
- **Формат:** только JSON (`Content-Type: application/json; charset=utf-8`). Даты — ISO 8601 UTC.
- **Аутентификация:** `Authorization: Bearer <access_jwt>` во всех защищённых запросах.
- **Идентификаторы:** UUID v4 в путях и телах.
- **Пагинация (списки):** query `?page=1&page_size=20` (default 20, max 100). В ответе —
  конверт `{ "data": [...], "pagination": { "page", "page_size", "total", "total_pages" } }`.
- **Фильтрация:** query-параметры по полям (`?status=submitted&region_code=23`).
- **Сортировка:** `?sort=-created_at` (минус = убывание, несколько через запятую).
- **Идемпотентность:** для небезопасных POST, создающих ресурсы (заявка, кейс), клиент шлёт
  заголовок `Idempotency-Key: <uuid>`. Повтор с тем же ключом возвращает исходный результат.
- **HTTP-коды:** 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized,
  403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests,
  500 Internal.
- **Трассировка:** каждый ответ содержит `X-Trace-Id`; он же в теле ошибки (`trace_id`).

---

## 2. Авторизация

Провайдер аутентификации абстрагирован (`auth_provider`), в MVP реализован `sms`. Интерфейс
позволит позже добавить `esia`, `goskey`, `sso` без изменения контракта клиента.

### 2.1 Запрос SMS-кода

`POST /api/v1/auth/otp/request`

Запрос:
```json
{ "phone": "+79180000000", "consent_pd": true }
```
Ответ `200`:
```json
{ "request_id": "b1f2…", "expires_in": 120, "resend_after": 30 }
```
Ошибки: `422` неверный формат телефона; `429` слишком частые запросы (лимит).

### 2.2 Подтверждение кода → получение токена

`POST /api/v1/auth/otp/verify`

Запрос:
```json
{ "request_id": "b1f2…", "code": "1234" }
```
Ответ `200`:
```json
{
  "access_token": "eyJ…",
  "refresh_token": "def…",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": { "id": "9f1c…", "role": "citizen", "status": "active", "is_new": true }
}
```
Ошибки: `422` неверный код (`error_code: invalid_otp`); `410` код истёк (`otp_expired`).

### 2.3 Обновление токена

`POST /api/v1/auth/token/refresh` → `{ "refresh_token": "def…" }` → новый `access_token`
(и ротация refresh). Ошибка `401 invalid_refresh`.

### 2.4 Выход

`POST /api/v1/auth/logout` (Bearer) → `204`. Инвалидирует refresh-токен.

---

## 3. API по основным сущностям

Для каждого — назначение, запрос, ответ, коды, бизнес-ошибки. Ниже ключевые endpoints
(полный список полей — в MVP_Data_Model_v1.md).

### 3.1 Пользователь / профиль

| Метод | URL | Назначение |
|-------|-----|-----------|
| GET | `/api/v1/users/me` | Текущий профиль |
| PATCH | `/api/v1/users/me` | Обновить профиль (ФИО, email, регион, дата рождения) |
| GET | `/api/v1/users/me/categories` | Категории гражданина |
| PUT | `/api/v1/users/me/categories` | Задать категории (массив `citizen_category_id`) |

`GET /users/me` → `200`:
```json
{ "id":"9f1c…","role":"citizen","phone":"+79180000000","first_name":"Артур",
  "last_name":"Даштоян","region_id":"d1…","categories":["svo_participant"],"status":"active" }
```
Ошибки: `401`.

### 3.2 Кейс (Project)

| Метод | URL | Назначение |
|-------|-----|-----------|
| GET | `/api/v1/projects` | Список кейсов (пагинация, фильтр по status/life_event) |
| POST | `/api/v1/projects` | Создать кейс |
| GET | `/api/v1/projects/{id}` | Кейс с агрегатами |
| PATCH | `/api/v1/projects/{id}` | Обновить (life_event, статус) |

`POST /projects` (`Idempotency-Key`):
```json
{ "life_event": "svo_return", "title": "Возвращение со службы" }
```
Ответ `201`: объект `project` со `status: "draft"`.
Ошибки: `409` активный кейс по этой `life_event` уже есть (`duplicate_active_project`).

### 3.3 Анкета

| Метод | URL | Назначение |
|-------|-----|-----------|
| GET | `/api/v1/projects/{id}/questionnaire` | Схема вопросов (базовые + динамические по life_event) |
| PUT | `/api/v1/projects/{id}/questionnaire` | Сохранить ответы (частично/целиком) |

`GET …/questionnaire` → `200` возвращает схему:
```json
{ "sections": [
    { "code":"base", "title":"Базовые данные", "questions":[
        {"code":"income_month","type":"number","required":true,"label":"Доход в месяц, ₽"},
        {"code":"children_count","type":"number","required":false,"label":"Детей"} ]},
    { "code":"svo_return", "title":"Уточнения", "questions":[ … ] } ] }
```
`PUT …/questionnaire`:
```json
{ "answers": { "income_month": 45000, "children_count": 3 } }
```
Ответ `200`: `{ "completed": true, "missing_required": [] }`.
Ошибки: `422` невалидный тип ответа (`invalid_answer`).

### 3.4 Меры поддержки (каталог/справочно)

| Метод | URL | Назначение |
|-------|-----|-----------|
| GET | `/api/v1/measures` | Список действующих мер (фильтр region/type) |
| GET | `/api/v1/measures/{id}` | Карточка меры (в т.ч. required_documents) |
| POST | `/api/v1/measures` | (admin) создать меру |
| POST | `/api/v1/measures/{id}/versions` | (admin) опубликовать новую версию |
| POST | `/api/v1/measures/import` | (admin) импорт (напр. таблица Краснодарского края) |

Ошибки создания: `403` без роли admin; `422` невалидный `eligibility`.

### 3.5 Рекомендации Rule Engine — см. §4.

### 3.6 Документы

| Метод | URL | Назначение |
|-------|-----|-----------|
| POST | `/api/v1/documents` | Загрузить (multipart) |
| GET | `/api/v1/documents/{id}` | Метаданные |
| GET | `/api/v1/documents/{id}/content` | Скачать (подписанный URL) |
| DELETE | `/api/v1/documents/{id}` | Мягкое удаление |

`POST /documents` (multipart: file + `doc_type` + `project_id`) → `201` метаданные
(`status: uploaded`). Ошибки: `413` слишком большой файл; `415` неподдерживаемый тип.

### 3.7 Заявки

| Метод | URL | Назначение |
|-------|-----|-----------|
| GET | `/api/v1/applications` | Список (фильтр по project/status) |
| POST | `/api/v1/applications` | Создать заявку (само- или координатором) |
| GET | `/api/v1/applications/{id}` | Заявка |
| POST | `/api/v1/applications/{id}/documents` | Привязать документы (N:M) |
| POST | `/api/v1/applications/{id}/transitions` | Сменить статус (по правам) |

`POST /applications` (`Idempotency-Key`):
```json
{ "project_id":"7c…", "support_measure_id":"b3…", "channel":"mfc" }
```
Ответ `201`: заявка со `status: submitted`, зафиксирован `measure_version`.
Бизнес-ошибки: `409` версия меры изменилась (`measure_version_conflict`); `422` нет
обязательных документов (`missing_required_documents`, в `details` — список кодов); `403`
мера недоступна (`measure_unavailable`).

### 3.8 Уведомления

| Метод | URL | Назначение |
|-------|-----|-----------|
| GET | `/api/v1/notifications` | Список (внутрисистемные) |
| POST | `/api/v1/notifications/{id}/read` | Отметить прочитанным |

### 3.9 Справочники

`GET /api/v1/dictionaries/{name}` — `name` ∈ `regions`, `citizen_categories`,
`application_statuses`, `authorities`, `life_events`. Кэшируемый ответ. Управление —
`POST/PATCH` под ролью admin.

---

## 4. API Rule Engine

Отдельная группа `/api/v1/projects/{id}/matching`.

### 4.1 Запуск оценки кейса

`POST /api/v1/projects/{id}/matching/run`

Тело (опц.): `{ "subject_type": "citizen" }` (по умолчанию из профиля).
Действие: собирает Evaluation Context, прогоняет Rule Engine, пишет `RuleEvaluationLog`.
Ответ `202` (или `200` синхронно для MVP):
```json
{ "matching_id": "m1…", "evaluated_at": "2026-07-06T10:00:00Z", "engine_version": "1.0", "count": 7 }
```
Ошибки: `422` анкета не завершена (`questionnaire_incomplete`, `details.missing`).

### 4.2 Список рекомендаций

`GET /api/v1/projects/{id}/matching/results?category=eligible`

Ответ `200`:
```json
{ "data": [
  { "measure_id":"b3…","measure_code":"KK-SVO-PAY-001","title":"Единовременная выплата",
    "score":100,"category":"eligible","amount":100000.00 },
  { "measure_id":"c4…","score":80,"category":"conditional","title":"…" }
], "pagination": { … } }
```
`category` ∈ `eligible|conditional|need_info` (hidden не возвращается гражданину).

### 4.3 Explainability по мере

`GET /api/v1/projects/{id}/matching/results/{measure_id}/explain` → структура из
Rule_Engine §6 (`matched`, `unmet`, `missing`, `next_step`, `required_documents`).

### 4.4 Повторная оценка

Идемпотентно: повторный `POST …/matching/run` после изменения анкеты создаёт новый прогон
(новый `matching_id`), предыдущий сохраняется в журнале.

### 4.5 Журнал оценки (admin/coordinator)

`GET /api/v1/projects/{id}/matching/log` — включая `hidden`-меры с `unmet_rules`. Доступ:
`coordinator` (свои подопечные), `admin`. Гражданину `403`.

---

## 5. Формат ошибок

Единый конверт для всех ошибок:
```json
{
  "error": {
    "error_code": "missing_required_documents",
    "message": "Для подачи заявки не хватает обязательных документов",
    "details": { "missing": ["mil_id", "passport"] },
    "trace_id": "a1b2c3…"
  }
}
```

| Ситуация | HTTP | error_code |
|----------|------|-----------|
| Неверный SMS-код | 422 | `invalid_otp` |
| Код истёк | 410 | `otp_expired` |
| Не хватает обязательных данных | 422 | `validation_failed` |
| Мера недоступна | 403 | `measure_unavailable` |
| Конфликт версий меры | 409 | `measure_version_conflict` |
| Дубль активного кейса | 409 | `duplicate_active_project` |
| Нет прав доступа | 403 | `forbidden` |
| Не аутентифицирован | 401 | `unauthorized` |
| Ресурс не найден | 404 | `not_found` |
| Превышен лимит запросов | 429 | `rate_limited` |

---

## 6. Webhook / Event-модель (задел на будущее)

Контракт событий определяется сейчас, реализация — позже (Kafka/RabbitMQ из архитектуры).
Общий конверт:
```json
{ "event_id":"e1…","event_type":"application.status_changed","occurred_at":"…",
  "trace_id":"…","data": { … } }
```

| Событие | event_type | Полезная нагрузка |
|---------|-----------|-------------------|
| Создан кейс | `project.created` | project_id, citizen_id, life_event |
| Обновлена анкета | `questionnaire.updated` | project_id, completed |
| Завершён подбор | `matching.completed` | project_id, matching_id, count |
| Создана заявка | `application.created` | application_id, measure_id |
| Изменён статус заявки | `application.status_changed` | application_id, from, to |

Доставка — HTTP POST на зарегистрированный `webhook_url` (создание подписок — вне MVP,
только контракт). Подпись `X-Signature` (HMAC) — зарезервировано.

---

## 7. OpenAPI Readiness

Документ структурирован под автогенерацию OpenAPI 3.1:

- Все ресурсы, методы и коды перечислены явно (§2–§5).
- Схемы объектов — из MVP_Data_Model_v1.md (переиспользуются как `components.schemas`).
- Единый конверт ошибок (§5) → `components.responses.Error`.
- Пагинация, `Idempotency-Key`, `Authorization` → `components.parameters` / `securitySchemes`
  (`bearerAuth`).
- Перечислимые значения (`role`, `category`, `application_status.code`, `error_code`) →
  `enum` в схемах.
- Рекомендованный следующий шаг: сгенерировать `openapi.yaml` и валидировать линтером (Spectral).

---

## 8. Проверка критерия готовности (T-004)

| Требование PM | Где выполнено |
|---------------|---------------|
| Описаны ключевые REST-endpoint'ы MVP | §2, §3, §4 |
| Форматы запросов и ответов | Примеры в каждом разделе |
| Единые ошибки и версионирование | §1 (версии), §5 (ошибки) |
| Отдельные API для Rule Engine | §4 (run / results / explain / log) |
| Пригодность для генерации OpenAPI и старта Backend | §7 |

---

## 9. Вопросы к PM

1. Синхронный подбор (`200` сразу) или асинхронный (`202` + опрос/событие) в MVP? Предложил
   синхронный для простоты — подтвердить.
2. Загрузка документов — прямым multipart на Backend или через presigned-URL в хранилище
   (S3-совместимое)? Влияет на §3.6.
3. Нужен ли уже в MVP endpoint выгрузки статистики для дашборда руководителя, или дашборд
   читает те же ресурсы с агрегирующими query-параметрами?
4. Ролевую модель фиксируем как `citizen / coordinator / admin` (manager свёрнут в admin),
   но enum в БД оставляем расширяемым — подтверждаешь?
