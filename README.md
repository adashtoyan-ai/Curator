# КУРАТОР

Платформа цифрового сопровождения граждан. Не каталог льгот и не портал госуслуг, а система,
которая сама определяет, что человеку положено, и ведёт его по персональному маршруту. Первый
сценарий — сопровождение участников СВО и членов их семей (пилот — Краснодарский край).

## Что в репозитории

### Спецификация (Product + Solution Architecture)
- **MVP_Overview_v1.2.md** — сводный обзор проекта (начните отсюда).
- **MVP_Data_Model_v1.md** — модель данных ядра.
- **Rule_Engine_MVP_v1.md** — движок подбора мер (eligibility, Score, Explainability).
- **MVP_User_Flows_v1.md** — пользовательские сценарии.
- **MVP_API_Contracts_v1.md** — REST-контракты.
- **MVP_UI_Specification_v1.md** — экранная модель.
- **MVP_Product_Backlog_v1.md** — бэклог и роадмап.
- **MVP_Solution_Architecture_v1.md** — техническая архитектура (модульный монолит).

### Рабочий демо-прототип
- **curator-demo/** — запускаемый сквозной сценарий (FastAPI + SQLite):
  вход → анкета → подбор мер (Rule Engine) → объяснение → заявка → координатор → история → дашборд.
  White Label, история сопровождения (Case Timeline), панель руководителя.
  См. `curator-demo/README.md` и `curator-demo/DEMO_SCRIPT.md` (сценарий показа заказчику).

## Быстрый старт демо

```bash
cd curator-demo
python3 -m pip install -r requirements.txt --break-system-packages
python3 -m uvicorn app.main:app --port 8000
# открыть http://localhost:8000, демо-код SMS: 1234
```

## Статус
MVP v1.2 — спецификация готова, демо-прототип работает end-to-end. Команда: 2 человека + ИИ.
Данные мер поддержки в демо — примерные; перед пилотом заменяются актуальными данными региона.
